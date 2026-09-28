from aiogram.utils.keyboard import InlineKeyboardBuilder


def step_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Помогло", callback_data="step_ok")
    kb.button(text="❌ Не помогло", callback_data="step_fail")
    kb.button(text="🆘 Позвать человека", callback_data="call_human")
    kb.adjust(2, 1)
    return kb.as_markup()