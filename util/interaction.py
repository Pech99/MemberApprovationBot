
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

from classi.DAO import *
from classi.setup import *
from util.config import load_config



config = load_config(section='telegram')
BOT = Bot(token=config['token'])


# =====================================================================
# MOTORE DI COMPILAZIONE: INVIO DELLE RICHIESTE SUCCESSIVE
# =====================================================================
async def send_next_step(user_id: int, state: FSMContext):
    data = await state.get_data()
    
    steps = data.get("setup")
    if not isinstance(steps, GroupSteps):
        raise ValueError("key must be a str")

    # Verifica se l'utente ha completato tutti i moduli richiesti
    if steps.hasNext():
        await process_form_completion(user_id, state)
        return

    step = steps.getNext()
    if step.type == "button":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Accetto ✅", callback_data="form_accept_rules")]
        ])
        await BOT.send_message(chat_id=user_id, text=step.question, reply_markup=keyboard)
    else:
        # Blocchi standard di testo, date o contenuti multimediali
        await BOT.send_message(chat_id=user_id, text=step.question)

# =====================================================================
# FINE COMPILAZIONE & INVIO RICHIESTA AGLI ADMIN
# =====================================================================
async def process_form_completion(user_id: int, state: FSMContext):
    data = await state.get_data()
    chat_id = data.get("chat_id")
    user_id = data.get("user_id")
    answers = data.get("answers", {})

    # 1. Recupera la richiesta dal database per sincronizzare i dati dell'utente
    request_db = await JoinRequestDAO.get_by_chat_ids(chat_id, user_id)
    if not request_db:
        await BOT.send_message(chat_id=user_id, text="Si è verificato un errore nel salvataggio. Riprova.")
        await state.clear()
        return

    # Aggiorna il record inserendo il JSON delle risposte
    request_db.answers = answers
    await JoinRequestDAO.update_request(request_db)

    # 2. Notifica l'utente finale del successo dell'invio
    await BOT.send_message(
        chat_id=user_id, 
        text="Grazie! Le tue risposte sono state inoltrate agli amministratori. Riceverai una notifica a breve."
    )
    await state.clear() # Resetta la FSM per questo utente

    # 3. Composizione del report testuale per gli amministratori
    report_text = (
        f"📥 <b>Nuova richiesta di accesso!</b>\n\n"
        f"👤 <b>Utente:</b> {html.quote(request_db.full_name)} (@{html.quote(request_db.username)})\n"
        f"🆔 <b>ID Utente:</b> <code>{user_id}</code>\n"
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
            InlineKeyboardButton(text="Accetta ✅", callback_data=f"approve:{chat_id}:{user_id}"),
            InlineKeyboardButton(text="Rifiuta ❌", callback_data=f"decline:{chat_id}:{user_id}")
        ]
    ])

    # 4. Spedizione delle informazioni agli admin del gruppo
    # Ottieni la lista degli amministratori reali della chat di destinazione
    try:
        admins = await BOT.get_chat_administrators(chat_id=chat_id)
        for admin in admins:
            if admin.user.is_bot:
                continue
            
            try:
                # Invia il resoconto testuale principale completo di tastiera decisionale
                await BOT.send_message(chat_id=admin.user.id, text=report_text, reply_markup=admin_keyboard, parse_mode="HTML")
                
                # Se l'utente ha allegato dei file, li gira in sequenza all'admin
                for media in media_to_send:
                    if media["type"] == "photo":
                        await BOT.send_photo(chat_id=admin.user.id, photo=media["file_id"], caption=f"Allegato per la richiesta di {request_db.full_name}")
                    elif media["type"] == "video":
                        await BOT.send_video(chat_id=admin.user.id, video=media["file_id"], caption=f"Allegato per la richiesta di {request_db.full_name}")
                    elif media["type"] == "voice":
                        await BOT.send_voice(chat_id=admin.user.id, voice=media["file_id"])
            except Exception as e:
                a = 0
                #logger.warning(f"Impossibile notificare l'admin {admin.user.id}: {e}")
    except Exception as e:
        a = 0
        #logger.error(f"Errore durante il recupero degli amministratori per la chat {chat_id}: {e}")
