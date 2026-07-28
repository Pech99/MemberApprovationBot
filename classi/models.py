from aiogram.fsm.state import State, StatesGroup

class DynamicForm(StatesGroup):
    filling_form = State()
