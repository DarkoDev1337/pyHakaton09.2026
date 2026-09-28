from aiogram.fsm.state import State, StatesGroup


class Support(StatesGroup):
    clarifying = State()  # ждём ответ на уточняющий вопрос
    solving = State()     # ждём результат шага (кнопки)