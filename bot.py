from aiogram.fsm.context import FSMContext
from aiogram.types import ChatJoinRequest
from aiogram import Router, F
from aiogram import types


router = Router()

@router.chat_join_request()
async def handle_join_request(request: ChatJoinRequest, state: FSMContext):
    user_id = request.from_user.id
    chat_id = request.chat.id  # Il gruppo a cui l'utente vuole accedere
    
    # 1. Recupera da Postgres la configurazione del setup per 'chat_id'
    # setup_steps = await db.get_group_setup(chat_id)
    setup_steps = [
        {"type": "text", "question": "Ciao! Presentati in un messaggio:"},
        {"type": "photo", "question": "Ora inviaci una foto profilo per conoscerti:"}
    ] # Simulazione dati da DB
    
    if not setup_steps:
        # Se l'admin non ha impostato domande, lo accettiamo subito!
        await request.approve()
        return

    # 2. Inizializziamo il contesto della FSM per questo utente
    await state.set_state(DynamicFormStates.compilazione)
    await state.set_data({
        "target_chat_id": chat_id, # Il gruppo finale
        "steps": setup_steps,      # Tutta la lista di passaggi da fare
        "current_index": 0,        # Partiamo dal primo blocco (indice 0)
        "answers": {}              # Qui accumuleremo le risposte dell'utente
    })
    
    # 3. Inviamo la prima domanda privatamente all'utente
    first_question = setup_steps[0]["question"]
    await request.bot.send_message(
        chat_id=user_id,
        text=f"Benvenuto! Per entrare nel gruppo, rispondi a questa domanda:\n\n{first_question}"
    )


@router.message(DynamicFormStates.compilazione)
async def process_dynamic_step(message: types.Message, state: FSMContext):
    data = await state.get_data()
    steps = data["steps"]
    current_index = data["current_index"]
    answers = data["answers"]
    target_chat_id = data["target_chat_id"]
    
    current_step = steps[current_index]
    step_type = current_step["type"]
    
    # --- VALIDAZIONE DELL'INPUT IN BASE AL TIPO DI BLOCCO ---
    valid = False
    answer_value = None

    if step_type == "text" and message.text:
        answer_value = message.text
        valid = True
    elif step_type == "photo" and message.photo:
        # Salviamo il file_id della foto con la risoluzione maggiore
        answer_value = message.photo[-1].file_id
        valid = True
    # Puoi espandere qui per "video", "document", ecc.

    if not valid:
        await message.answer(f"Formato non valido. Per favore, invia il tipo richiesto: {step_type}")
        return

    # --- SALVATAGGIO DELLA RISPOSTA ---
    answers[f"step_{current_index}"] = {
        "question": current_step["question"],
        "answer": answer_value,
        "type": step_type
    }
    await state.update_data(answers=answers)
    
    # --- VERIFICA SE CI SONO ALTRE DOMANDE ---
    next_index = current_index + 1
    if next_index < len(steps):
        # Passiamo al prossimo step
        await state.update_data(current_index=next_index)
        next_question = steps[next_index]["question"]
        await message.answer(next_question)
    else:
        # --- FINE DEL FORM: INVIA LA RICHIESTA AGLI ADMIN ---
        await state.clear() # Svuota la FSM dell'utente
        
        await message.answer("Grazie! Le tue risposte sono state inviate agli amministratori. Attendi la conferma. ⏳")
        
        # Qui manderai il riepilogo al gruppo admin / chat admin
        await invia_richiesta_ad_admin(message.bot, target_chat_id, message.from_user, answers)


async def invia_richiesta_ad_admin(bot, group_id, user: types.User, answers: dict):
    # Costruisci il testo riepilogativo ciclando su 'answers'
    riepilogo = f"📥 **Nuova richiesta di join** da parte di {user.mention_html()}:\n\n"
    for key, data in answers.items():
        riepilogo += f"❓ {data['question']}\n➡️ {data['answer']}\n\n"
    
    # Tastiera di approvazione
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="Accetta ✅", callback_data=f"approve_{group_id}_{user.id}"),
        types.InlineKeyboardButton(text="Rifiuta ❌", callback_data=f"reject_{group_id}_{user.id}")
    )
    
    # Manda il riepilogo (puoi impostare un ID di un gruppo di amministrazione nel DB)
    admin_chat_id = ... # Recupera da DB dove mandare le richieste per questo gruppo
    await bot.send_message(chat_id=admin_chat_id, text=riepilogo, reply_markup=builder.as_markup(), parse_mode="HTML")