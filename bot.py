
import logging
import json
from aiogram import Bot, Dispatcher, F, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    ChatJoinRequest, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)

# Importa i tuoi moduli DAO e DB Manager reali dal pacchetto DB
from classi.DAO import *
from classi.models import *
from util.config import load_config

# 1. Configurazione Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Inizializzazione Bot e Dispatcher
# In produzione inserisci il token in un file .env o config.ini
config = load_config(section='telegram')
bot = Bot(token=config['token'])
dp = Dispatcher()

# 3. Definizione degli Stati FSM
class DynamicForm(StatesGroup):
    filling_form = State()  # Stato generico per la compilazione dei blocchi dinamici

# =====================================================================
# INTERCETTAZIONE DELLA RICHIESTA DI JOIN & INVIO PRIMO MESSAGGIO
# =====================================================================
@dp.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, state: FSMContext):
    chat_id = event.chat.id
    user_id = event.from_user.id
    username = event.from_user.username
    full_name = event.from_user.full_name

    logger.info(f"Nuova richiesta di join rilevata. Chat: {chat_id}, Utente: {user_id}")

    # Recupera il setup specifico configurato dagli admin per questo gruppo
    setup = await GroupSetupDAO.get_by_chat_id(chat_id)
    
    if not setup or not setup.steps:
        # Se non c'è nessun setup dinamico impostato, approva direttamente
        logger.info(f"Nessun setup trovato per la chat {chat_id}. Approvo l'utente.")
        await event.approve()
        return

    # Crea preventivamente il record della richiesta sul database in stato PENDING
    new_request = JoinRequest(
        chat_id=chat_id,
        user_id=user_id,
        username=username,
        full_name=full_name,
        answers={},
        status=JoinRequeStstaus.pending
    )
    RqID = await JoinRequestDAO.create(new_request)

    # Inizializza il contesto FSM memorizzando i dettagli della richiesta e degli step
    await state.set_state(DynamicForm.filling_form)
    await state.update_data(
        id = RqID,
        chat_id=chat_id,
        user_id=user_id,
        steps=setup.steps,  # Lista di dizionari con i blocchi base (es. tipo, domanda, chiave)
        current_step_index=0,
        answers={}
    )

    # Avvia la somministrazione del primo blocco di domande in chat privata
    await send_next_step(user_id, state)


# =====================================================================
# MOTORE DI COMPILAZIONE: INVIO DELLE RICHIESTE SUCCESSIVE
# =====================================================================
async def send_next_step(user_id: int, state: FSMContext):
    data = await state.get_data()
    steps = data.get("steps", [])
    current_index = data.get("current_step_index", 0)

    # Verifica se l'utente ha completato tutti i moduli richiesti
    if current_index >= len(steps):
        await process_form_completion(user_id, state)
        return

    # Estrai le informazioni sul blocco/step corrente
    current_step = steps[current_index]
    step_type = current_step.get("type", "text")
    question = current_step.get("question", "Inserisci il dato richiesto:")

    # Gestione condizionale in base al tipo di blocco base
    if step_type == "button":
        # Esempio: Accettazione del regolamento o risposte chiuse
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Accetto ✅", callback_data="form_accept_rules")]
        ])
        await bot.send_message(chat_id=user_id, text=question, reply_markup=keyboard)
    else:
        # Blocchi standard di testo, date o contenuti multimediali
        await bot.send_message(chat_id=user_id, text=question)


# =====================================================================
# RICEZIONE DELLE RISPOSTE (Gestore Messaggi di Testo / Media)
# =====================================================================
@dp.message(DynamicForm.filling_form)
async def handle_user_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    steps = data.get("steps", [])
    current_index = data.get("current_step_index", 0)
    answers = data.get("answers", {})

    current_step = steps[current_index]
    step_key = current_step.get("key")
    step_type = current_step.get("type", "text")

    # Validazione base e cattura dell'input a seconda del tipo atteso
    if step_type == "text":
        if not message.text:
            await message.reply("Per favore, rispondi inserendo del testo valido.")
            return
        answers[step_key] = message.text

    elif step_type == "media":
        # Cattura foto, video o messaggi vocali salvando il file_id unico di Telegram
        if message.photo:
            answers[step_key] = {"type": "photo", "file_id": message.photo[-1].file_id}
        elif message.video:
            answers[step_key] = {"type": "video", "file_id": message.video.file_id}
        elif message.voice:
            answers[step_key] = {"type": "voice", "file_id": message.voice.file_id}
        else:
            await message.reply("Per favore, allega un contenuto multimediale (Foto, Video o Audio).")
            return
    else:
        # Se lo step richiedeva un bottone ma l'utente scrive a testo, lo invitiamo a cliccare
        await message.reply("Usa i pulsanti a schermo per completare questo passaggio.")
        return

    # Aggiorna il dizionario delle risposte e avanza all'indice successivo
    new_index = current_index + 1
    await state.update_data(answers=answers, current_step_index=new_index)
    
    # Prosegui con lo step successivo
    await send_next_step(message.from_user.id, state)


# Gestore specifico per la pressione dei bottoni inline durante la compilazione
@dp.callback_query(DynamicForm.filling_form, F.data == "form_accept_rules")
async def handle_button_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    steps = data.get("steps", [])
    current_index = data.get("current_step_index", 0)
    answers = data.get("answers", {})

    current_step = steps[current_index]
    step_key = current_step.get("key")

    # Salva la conferma dell'utente
    answers[step_key] = "Accettato"
    
    await callback.answer("Passaggio completato!")
    await callback.message.edit_reply_markup(reply_markup=None) # Rimuove il bottone per pulizia

    # Avanza all'indice successivo
    new_index = current_index + 1
    await state.update_data(answers=answers, current_step_index=new_index)
    
    await send_next_step(callback.from_user.id, state)


# =====================================================================
# FINE COMPILAZIONE & INVIO RICHIESTA AGLI ADMIN
# =====================================================================
async def process_form_completion(user_id: int, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")
    target_user_id = data.get("user_id")
    answers = data.get("answers", {})

    # 1. Recupera la richiesta dal database per sincronizzare i dati dell'utente
    request_db = await JoinRequestDAO.get_request(chat_id, target_user_id)
    if not request_db:
        await bot.send_message(chat_id=user_id, text="Si è verificato un errore nel salvataggio. Riprova.")
        await state.clear()
        return

    # Aggiorna il record inserendo il JSON delle risposte
    request_db.answers = answers
    await JoinRequestDAO.update_request(request_db)

    # 2. Notifica l'utente finale del successo dell'invio
    await bot.send_message(
        chat_id=user_id, 
        text="Grazie! Le tue risposte sono state inoltrate agli amministratori. Riceverai una notifica a breve."
    )
    await state.clear() # Resetta la FSM per questo utente

    # 3. Composizione del report testuale per gli amministratori
    report_text = (
        f"📥 <b>Nuova richiesta di accesso!</b>\n\n"
        f"👤 <b>Utente:</b> {html.quote(request_db.full_name)} (@{html.quote(request_db.username)})\n"
        f"🆔 <b>ID Utente:</b> <code>{target_user_id}</code>\n"
        f"🌐 <b>Chat di destinazione:</b> <code>{chat_id}</code>\n\n"
        f"📝 <b>Risposte fornite:</b>\n"
    )

    media_to_send = []
    for key, value in answers.items():
        if isinstance(value, dict) and "file_id" in value:
            # Identifica la presenza di risposte di tipo file multimediale
            media_to_send.append(value)
            report_text += f"- <i>{key}</i>: [Inviato allegato multimediale sotto]\n"
        else:
            report_text += f"- <i>{key}</i>: {html.quote(str(value))}\n"

    # Generazione dei bottoni di approvazione/rifiuto caricando ID chat e ID utente nel callback_data
    # NOTA: Telegram ha un limite di 64 byte per il callback_data. 
    # La stringa "approve:{chat_id}:{user_id}" vi rientra perfettamente.
    admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Accetta ✅", callback_data=f"approve:{chat_id}:{target_user_id}"),
            InlineKeyboardButton(text="Rifiuta ❌", callback_data=f"decline:{chat_id}:{target_user_id}")
        ]
    ])

    # 4. Spedizione delle informazioni agli admin del gruppo
    # Ottieni la lista degli amministratori reali della chat di destinazione
    try:
        admins = await bot.get_chat_administrators(chat_id=chat_id)
        for admin in admins:
            if admin.user.is_bot:
                continue
            
            try:
                # Invia il resoconto testuale principale completo di tastiera decisionale
                await bot.send_message(chat_id=admin.user.id, text=report_text, reply_markup=admin_keyboard, parse_mode="HTML")
                
                # Se l'utente ha allegato dei file, li gira in sequenza all'admin
                for media in media_to_send:
                    if media["type"] == "photo":
                        await bot.send_photo(chat_id=admin.user.id, photo=media["file_id"], caption=f"Allegato per la richiesta di {request_db.full_name}")
                    elif media["type"] == "video":
                        await bot.send_video(chat_id=admin.user.id, video=media["file_id"], caption=f"Allegato per la richiesta di {request_db.full_name}")
                    elif media["type"] == "voice":
                        await bot.send_voice(chat_id=admin.user.id, voice=media["file_id"])
            except Exception as e:
                logger.warning(f"Impossibile notificare l'admin {admin.user.id}: {e}")
    except Exception as e:
        logger.error(f"Errore durante il recupero degli amministratori per la chat {chat_id}: {e}")


# =====================================================================
# DECISIONE ADMIN: APPROVAZIONE / RIFIUTO RICHIESTA DI JOIN
# =====================================================================
@dp.callback_query(F.data.startswith("approve:") | F.data.startswith("decline:"))
async def handle_admin_decision(callback: CallbackQuery):
    action, chat_id_str, user_id_str = callback.data.split(":")
    chat_id = int(chat_id_str)
    user_id = int(user_id_str)

    # 1. Recupera la richiesta memorizzata sul database per accertarne lo stato
    request_db = await JoinRequestDAO.get_request(chat_id, user_id)
    if not request_db or request_db.status != RequestStatus.PENDING:
        await callback.answer("Questa richiesta è già stata elaborata o è inesistente.", show_alert=True)
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    if action == "approve":
        try:
            # Esegue la chiamata nativa Telegram per far entrare l'utente nel gruppo
            await bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id) [cite: 5]
            request_db.status = RequestStatus.APPROVED [cite: 5]
            await JoinRequestDAO.update_request(request_db)
            
            await callback.answer("Richiesta approvata con successo!")
            await callback.message.edit_text(callback.message.text + "\n\n🟢 <b>Stato: APPROVATA</b>", parse_mode="HTML", reply_markup=None)
            
            # Notifica l'utente dell'avvenuta accettazione
            try:
                await bot.send_message(chat_id=user_id, text="Evviva! La tua richiesta di accesso è stata approvata dagli amministratori! Ora puoi entrare nel gruppo.")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Errore durante l'approvazione di Telegram: {e}")
            await callback.answer(f"Errore durante l'approvazione: {e}", show_alert=True)

    elif action == "decline":
        try:
            # Esegue la chiamata nativa Telegram per respingere la richiesta
            await bot.decline_chat_join_request(chat_id=chat_id, user_id=user_id) [cite: 5]
            request_db.status = RequestStatus.DECLINED
            await JoinRequestDAO.update_request(request_db)
            
            await callback.answer("Richiesta respinta.")
            await callback.message.edit_text(callback.message.text + "\n\n🔴 <b>Stato: RESPINTA</b>", parse_mode="HTML", reply_markup=None)
            
            # Notifica l'utente dell'esito negativo
            try:
                await bot.send_message(chat_id=user_id, text="Ci dispiace, ma la tua richiesta di accesso è stata rifiutata dagli amministratori.")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Errore durante il rifiuto di Telegram: {e}")
            await callback.answer(f"Errore durante il rifiuto: {e}", show_alert=True)


# =====================================================================
# AVVIO DEL BOT (Polling Asincrono)
# =====================================================================
async def main():
    logger.info("Avvio del bot in corso...")
    # Rimuove eventuali webhook pendenti per ripartire in polling pulito
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())