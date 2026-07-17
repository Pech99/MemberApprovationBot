from aiogram.types import ChatJoinRequest, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.fsm.storage.memory import MemoryStorage     # Sostituisci in prod con PostgresStorage
from aiogram.fsm.state import State, StatesGroup
from DB.db_manager import init_db, close_db
from aiogram.fsm.context import FSMContext
import logging
import asyncpg
import asyncio
import json


# Configura i Log
logging.basicConfig(level=logging.INFO)

# Token e credenziali (In produzione usa le variabili d'ambiente!)
BOT_TOKEN = "IL_TUO_TELEGRAM_BOT_TOKEN"
DATABASE_URL = "postgresql://utente:password@localhost:5432/nome_db"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage()) # In produzione usa PostgresStorage per non pesare sulla RAM
router = Router()

# Pool di connessione al Database (globale)
db_pool = None




# --- STATI FSM ---
class DynamicFormStates(StatesGroup):
    compilazione = State() # Stato unico per tutta la compilazione dinamica

# --- HELPER DATABASE ---
async def get_group_steps(chat_id: int):
    """Recupera il setup dei blocchi per un determinato gruppo"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT steps FROM group_setups WHERE chat_id = $1", chat_id)
        if row:
            return json.loads(row['steps'])
        return None

async def save_pending_request(user_id: int, chat_id: int, username: str, answers: dict):
    """Salva la richiesta pronta nel DB prima del verdetto dell'admin"""
    async with db_pool.acquire() as conn:
        return await conn.fetchval(
            """
            INSERT INTO join_requests (user_id, chat_id, username, answers) 
            VALUES ($1, $2, $3, $4) RETURNING id
            """,
            user_id, chat_id, username, json.dumps(answers)
        )

# --- AVVIO FLUSSO (CHAT JOIN REQUEST) ---
@router.chat_join_request()
async def handle_join_request(request: ChatJoinRequest, state: FSMContext):
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    # 1. Recupera i passaggi dal DB per questo specifico gruppo
    steps = await get_group_steps(chat_id)
    
    if not steps:
        # Se il gruppo non ha un setup personalizzato, accettiamo l'utente direttamente
        await request.approve()
        logging.info(f"Approvato automaticamente {user_id} in {chat_id} (nessun setup configurato).")
        return

    # 2. Inizializza i dati nella FSM
    await state.set_state(DynamicFormStates.compilazione)
    await state.update_data(
        steps=steps,
        current_index=0,
        answers={},
        target_chat_id=chat_id,
        target_chat_title=request.chat.title
    )
    
    # 3. Dai il benvenuto in chat privata e fai la prima domanda
    await bot.send_message(
        chat_id=user_id,
        text=f"Ciao! Per entrare in <b>{request.chat.title}</b> devi completare una breve presentazione.\n\n"
             f"<b>Domanda 1:</b> {steps[0]['question']}",
        parse_mode="HTML"
    )

# --- MOTORE DI COMPILAZIONE DINAMICO ---
@router.message(DynamicFormStates.compilazione)
async def process_dynamic_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = data["steps"]
    current_index = data["current_index"]
    answers = data["answers"]
    target_chat_id = data["target_chat_id"]
    
    current_step = steps[current_index]
    step_type = current_step["type"]
    step_key = current_step["key"]
    question_text = current_step["question"]
    
    valido = False
    risposta_salvata = None

    # Verifica la corrispondenza del tipo di messaggio inviato rispetto allo step richiesto
    if step_type == "text" and message.text:
        valido = True
        risposta_salvata = message.text
        
    elif step_type == "photo" and message.photo:
        valido = True
        # Salviamo l'ID della foto con la risoluzione più alta (l'ultima della lista)
        risposta_salvata = f"PHOTO_ID:{message.photo[-1].file_id}"
        
    elif step_type == "video" and message.video:
        valido = True
        risposta_salvata = f"VIDEO_ID:{message.video.file_id}"
        
    elif step_type == "audio" and message.audio:
        valido = True
        risposta_salvata = f"AUDIO_ID:{message.audio.file_id}"
        
    elif step_type == "video_note" and message.video_note: # I videomessaggi rotondi
        valido = True
        risposta_salvata = f"VIDEONOTE_ID:{message.video_note.file_id}"

    # Se l'utente invia un formato sbagliato (es. manda un testo quando serviva una foto)
    if not valido:
        await message.reply(f"Formato non valido. Per questo passaggio è richiesto un file di tipo: <b>{step_type}</b>.")
        return

    # Salva la risposta corrente nel dizionario temporaneo della FSM
    answers[step_key] = {
        "question": question_text,
        "type": step_type,
        "answer": risposta_salvata
    }
    await state.update_data(answers=answers)

    # Avanza all'indice successivo
    next_index = current_index + 1
    if next_index < len(steps):
        # Ci sono altre domande!
        await state.update_data(current_index=next_index)
        next_step = steps[next_index]
        await message.answer(f"<b>Domanda {next_index + 1}:</b> {next_step['question']}", parse_mode="HTML")
    else:
        # Modulo terminato! Salva la richiesta su DB
        request_id = await save_pending_request(
            user_id=message.from_user.id,
            chat_id=target_chat_id,
            username=message.from_user.username,
            answers=answers
        )
        
        await message.answer("Grazie! Le tue risposte sono state inviate agli amministratori. Riceverai una notifica non appena decideranno.")
        
        # Notifica gli admin inviando il resoconto
        await invia_richiesta_ad_admin(message.from_user, target_chat_id, answers, request_id)
        
        # Pulisce la FSM per questo utente
        await state.clear()

# --- INVIO SCHEDA AD ADMIN ---
async def invia_richiesta_ad_admin(user: types.User, group_id: int, answers: dict, request_id: int):
    """Invia il resoconto delle risposte nel gruppo o chat degli admin"""
    # Costruiamo la tastiera con i callback per gli admin
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Accetta", callback_data=f"adm_approve_{request_id}"),
            InlineKeyboardButton(text="❌ Rifiuta", callback_data=f"adm_reject_{request_id}")
        ]
    ])
    
    testo_base = f"📥 <b>Nuova richiesta di join!</b>\n" \
                 f"Utente: {user.mention_html()} (@{user.username or 'Nessun Username'})\n" \
                 f"ID Utente: <code>{user.id}</code>\n\n"
    
    # Inviamo il messaggio agli admin. 
    # NOTA: Per semplicità inviamo qui lo storico direttamente al gruppo stesso (se il bot è admin lì).
    # In alternativa, puoi definire un ID di un gruppo di controllo Admin separato.
    destinatario_admin = group_id 

    await bot.send_message(chat_id=destinatario_admin, text=testo_base, parse_mode="HTML")

    # Cicliamo sulle risposte inviando i media in sequenza se presenti
    for key, item in answers.items():
        val = item["answer"]
        q = item["question"]
        
        if isinstance(val, str) and val.startswith("PHOTO_ID:"):
            await bot.send_photo(chat_id=destinatario_admin, photo=val.replace("PHOTO_ID:", ""), caption=f"❓ {q}")
        elif isinstance(val, str) and val.startswith("VIDEO_ID:"):
            await bot.send_video(chat_id=destinatario_admin, video=val.replace("VIDEO_ID:", ""), caption=f"❓ {q}")
        elif isinstance(val, str) and val.startswith("AUDIO_ID:"):
            await bot.send_audio(chat_id=destinatario_admin, audio=val.replace("AUDIO_ID:", ""), caption=f"❓ {q}")
        elif isinstance(val, str) and val.startswith("VIDEONOTE_ID:"):
            await bot.send_video_note(chat_id=destinatario_admin, video_note=val.replace("VIDEONOTE_ID:", ""))
        else:
            await bot.send_message(chat_id=destinatario_admin, text=f"❓ <b>{q}</b>\n➡️ {val}", parse_mode="HTML")

    # Messaggio finale con i pulsanti di azione agganciati all'ID della richiesta
    await bot.send_message(
        chat_id=destinatario_admin,
        text="Scegli come procedere per questa richiesta:",
        reply_markup=keyboard
    )

# --- AZIONI ADMIN (ACCETTA / RIFIUTA) ---
@router.callback_query(F.data.startswith("adm_"))
async def handle_admin_decision(callback: CallbackQuery):
    azione, request_id_str = callback.data.replace("adm_", "").split("_", 1)
    request_id = int(request_id_str)
    
    async with db_pool.acquire() as conn:
        # Recupera i dettagli della richiesta dal DB
        req = await conn.fetchrow("SELECT user_id, chat_id, status FROM join_requests WHERE id = $1", request_id)
        
        if not req:
            await callback.answer("Richiesta non trovata.", show_alert=True)
            return
            
        if req['status'] != 'pending':
            await callback.answer(f"Questa richiesta è già stata gestita (Stato: {req['status']}).", show_alert=True)
            return
        
        user_id = req['user_id']
        chat_id = req['chat_id']
        
        if azione == "approve":
            try:
                # Approva la richiesta su Telegram
                await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
                await conn.execute("UPDATE join_requests SET status = 'approved' WHERE id = $1", request_id)
                await callback.message.edit_text("✅ Richiesta approvata con successo!")
                # Notifica l'utente
                await bot.send_message(chat_id=user_id, text="Complimenti! La tua richiesta di accesso è stata approvata.")
            except Exception as e:
                await callback.answer(f"Errore durante l'approvazione: {str(e)}", show_alert=True)
                
        elif azione == "reject":
            try:
                # Rifiuta la richiesta su Telegram
                await bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
                await conn.execute("UPDATE join_requests SET status = 'rejected' WHERE id = $1", request_id)
                await callback.message.edit_text("❌ Richiesta rifiutata.")
                # Notifica l'utente
                await bot.send_message(chat_id=user_id, text="Ci dispiace, ma la tua richiesta di accesso è stata rifiutata.")
            except Exception as e:
                await callback.answer(f"Errore durante il rifiuto: {str(e)}", show_alert=True)


# --- AVVIO BOT ---
async def main():
    # Inizializza il DB manager caricando il file database.ini e impostando lo schema
    await init_db()
    
    # Configura il dispatcher (e lo storage FSM come preferisci)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    
    try:
        logging.info("Bot in avvio...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        # Assicura la chiusura del pool quando il bot si spegne
        await close_db()

if __name__ == "__main__":
    asyncio.run(main())