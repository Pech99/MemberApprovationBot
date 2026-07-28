
from aiogram.types import Message, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Dispatcher, F, html
from aiogram.filters import Command
import logging
import json

from DB.db_manager import init_db
from util.config import load_config
from classi.setup import *
from classi.DAO import *
from util.interaction import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher()

# OK Tabella Utenti
# OK Tabella Gruppi e Canali
# OK Modell e DAO Utenti
# OK Modell e DAO Gruppi e Canali
#    Trigger unicit join requet

# Gestione partecpanti e amministratori (con inserimento ed aggiornamento)





# =====================================================================
# INTERCETTAZIONE DELLA RICHIESTA DI JOIN & INVIO PRIMO MESSAGGIO
# =====================================================================
@dp.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, state: FSMContext):
    chat_id = event.chat.id
    user_id = event.from_user.id
    username = event.from_user.username

    logger.info(f"Nuova richiesta di join rilevata. Chat: {chat_id}, Utente: {user_id}")

    # Recupera il setup specifico configurato dagli admin per questo gruppo
    setup = await GroupSetupDAO.get_by_chat_id(chat_id)
    
    if not setup.hasNext():
        return

    # Crea preventivamente il record della richiesta sul database in stato PENDING
    new_request = JoinRequest(
        chat_id=chat_id,
        user_id=user_id,
        username=username,
    )
    RqID = await JoinRequestDAO.create(new_request)

    # Inizializza il contesto FSM memorizzando i dettagli della richiesta e degli step
    await state.set_state(DynamicForm.filling_form)
    await state.update_data(
        id = RqID,
        chat_id=chat_id,
        user_id=user_id,
        setup=setup,  # Lista di dizionari con i blocchi base (es. tipo, domanda, chiave)
        answers={}
    )

    # Avvia la somministrazione del primo blocco di domande in chat privata
    await send_next_step(user_id, state)


# =====================================================================
# RICEZIONE DELLE RISPOSTE (Gestore Messaggi di Testo / Media)
# =====================================================================
@dp.message(DynamicForm.filling_form)
async def handle_user_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data.get("answers", {})
    setup = data.get("setup")
    if not isinstance(setup, GroupSetup):
        raise ValueError("key must be a str")

    step = setup.getCurrent()

    # Validazione base e cattura dell'input a seconda del tipo atteso
    if step.type == "text":
        if not message.text:
            await message.reply("Per favore, rispondi inserendo del testo valido.")
            return
        answers[step.key] = message.text

    elif step.type == "media":
        # Cattura foto, video o messaggi vocali salvando il file_id unico di Telegram
        if message.photo:
            answers[step.key] = {"type": "photo", "file_id": message.photo[-1].file_id}
        elif message.video:
            answers[step.key] = {"type": "video", "file_id": message.video.file_id}
        elif message.voice:
            answers[step.key] = {"type": "voice", "file_id": message.voice.file_id}
        else:
            await message.reply("Per favore, allega un contenuto multimediale (Foto, Video o Audio).")
            return
    else:
        # Se lo step richiedeva un bottone ma l'utente scrive a testo, lo invitiamo a cliccare
        await message.reply("Usa i pulsanti a schermo per completare questo passaggio.")
        return
    
    await state.update_data(answers=answers, current_step_index=setup.current+1)
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
            await BOT.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
            request_db.status = RequestStatus.APPROVED
            await JoinRequestDAO.update_request(request_db)
            
            await callback.answer("Richiesta approvata con successo!")
            await callback.message.edit_text(callback.message.text + "\n\n🟢 <b>Stato: APPROVATA</b>", parse_mode="HTML", reply_markup=None)
            
            # Notifica l'utente dell'avvenuta accettazione
            try:
                await BOT.send_message(chat_id=user_id, text="Evviva! La tua richiesta di accesso è stata approvata dagli amministratori! Ora puoi entrare nel gruppo.")
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Errore durante l'approvazione di Telegram: {e}")
            await callback.answer(f"Errore durante l'approvazione: {e}", show_alert=True)

    elif action == "decline":
        try:
            # Esegue la chiamata nativa Telegram per respingere la richiesta
            await BOT.decline_chat_join_request(chat_id=chat_id, user_id=user_id)
            request_db.status = RequestStatus.DECLINED
            await JoinRequestDAO.update_request(request_db)
            
            await callback.answer("Richiesta respinta.")
            await callback.message.edit_text(callback.message.text + "\n\n🔴 <b>Stato: RESPINTA</b>", parse_mode="HTML", reply_markup=None)
            
            # Notifica l'utente dell'esito negativo
            try:
                await BOT.send_message(chat_id=user_id, text="Ci dispiace, ma la tua richiesta di accesso è stata rifiutata dagli amministratori.")
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
    await init_db()
    # Rimuove eventuali webhook pendenti per ripartire in polling pulito
    await BOT.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(BOT)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())