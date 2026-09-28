import time
import html

from aiogram import Router, F
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from ai import analyze, next_step, specialist_summary
from states import Support
from keyboards import step_kb
from escalation import send_to_specialists

router = Router()
MAX_QUESTIONS = 3  # больше 3 уточнений не задаём, иначе юзер взбесится


# ============ КОМАНДЫ ============

HELP_TEXT = """📖 КАК ПРАВИЛЬНО ОПИСАТЬ ПРОБЛЕМУ

Я понимаю свободный текст, но чем больше деталей —
тем быстрее помогу. Вот что стоит указать.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ЧТО РАБОТАЕТ ХОРОШО

1. Что не работает
   «Не открывается корпоративная почта»

2. Где именно
   «На ноутбуке. С телефона почта открывается»

3. Что видите на экране
   «Пишет "ошибка авторизации"»

4. Когда началось
   «Сегодня утром, вчера всё работало»

5. Срочность
   «Через 20 минут встреча, нужно срочно»

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ ЧТО МЕШАЕТ ПОМОЧЬ

1. Слишком общее
   «Всё сломалось» → непонятно, что именно

2. Без деталей
   «Не работает» → не знаю, что и где

3. Эмоции без фактов
   «Это кошмар, всё бесит» → помогу,
   но сначала опишите, что произошло

4. Вопрос не по теме
   «Расскажи анекдот» → я помогаю только
   с техническими проблемами

5. Провокации
   «Давай сам решай» → мне нужны детали
   от вас, иначе не смогу помочь

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 ПРИМЕРЫ

❌ Плохо:
   «Всё сломалось»

✅ Хорошо:
   «Не могу зайти в рабочую систему с ноутбука.
    Пишет "ошибка подключения". С телефона
    система открывается. Срочно, через 20 минут
    встреча»

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Плохо:
   «Почта не работает»

✅ Хорошо:
   «Корпоративная почта не отправляет письма.
    Приходят нормально, а отправить не могу.
    Ошибка "не удалось отправить сообщение".
    Началось сегодня утром»

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 ЧТО Я УМЕЮ

• Разобрать проблему и определить сервис
• Задать 1–2 уточняющих вопроса
• Предложить шаги решения
• Проверить, помогло ли
• Передать специалисту с полным контекстом

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 КОРОТКОЕ ПРАВИЛО

Чем конкретнее — тем быстрее помогу.
Если не знаете терминов — пишите как есть.
Я разберусь.
"""

WELCOME_TEXT = """👋 Здравствуйте! Я — виртуальный помощник поддержки.

Я разберу вашу проблему, задам пару уточняющих вопросов
и постараюсь помочь сразу. Если не получится — передам
специалисту вместе с полной историей.

Чтобы я помог быстрее, опишите проблему своими словами:
— что не работает,
— на каком устройстве,
— когда началось,
— есть ли срочность.

Не нужно знать термины. Пишите как есть.

/help — подробная инструкция
"""

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(WELCOME_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)



@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ок, обращение сброшено. Опиши новую проблему, когда надо.")


# ============ B: ПРИЁМ ОБРАЩЕНИЯ ============

@router.message(StateFilter(None), F.text)
async def new_ticket(message: Message, state: FSMContext):
    await state.set_data({
        "original": message.text,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "qa": [],
        "steps_tried": [],
        "step_number": 0,
        "last_question": None,
        "current_step": None,
        "problem": None,
        "service": None,
        "urgency": "medium",
        "created_at": time.time(),
    })
    await run_analysis(message, state)


@router.message(Support.clarifying, F.text)
async def got_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    qa = data["qa"] + [{"q": data["last_question"], "a": message.text}]
    await state.update_data(qa=qa)
    await run_analysis(message, state)


async def run_analysis(message: Message, state: FSMContext):
    """Зовёт ИИ и решает, что делать дальше: спросить / дать шаг / эскалировать."""
    data = await state.get_data()
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    result = await analyze(data["original"], data["qa"])

    await state.update_data(
        problem=result["problem_summary"],
        service=result["service"],
        urgency=result["urgency"],
    )

    if result["urgency"] == "high" and not data["qa"]:
        await message.answer("⚡ Вижу, что срочно. Действуем быстро.")

    status = result.get("status")

    print("\n=== AI RESULT ===")
    print("STATUS:", repr(status))
    print("QUESTION:", repr(result.get("next_question")))
    print("STEP:", repr(result.get("next_step")))
    print("=================\n")

    if (
            status == "clarifying"
            and result.get("next_question")
            and len(data["qa"]) < MAX_QUESTIONS
    ):
        question = result["next_question"]

        await state.update_data(last_question=question)
        await state.set_state(Support.clarifying)
        await message.answer(html.escape(question))

    elif status == "solving" and result.get("next_step"):
        await state.update_data(
            current_step=result["next_step"],
            step_number=1,
        )
        await send_step(
            message,
            state,
            result["next_step"],
            1,
            result.get("total_steps_estimate", 0),
        )

    else:
        await escalate(message, state, result.get("specialist_summary"))

# ============ C: РЕШЕНИЕ И ПРОВЕРКА ============

async def send_step(message: Message, state: FSMContext, text: str, number: int, total: int):
    await state.set_state(Support.solving)
    total_txt = f" из ~{total}" if total else ""
    await message.answer(
        f"🔧 <b>Шаг {number}{total_txt}</b>\n\n{html.escape(text)}\n\n"
        "Сделай и скажи, что вышло 👇",
        reply_markup=step_kb(),
    )


@router.message(Support.solving, F.text)
async def solving_text(message: Message):
    await message.answer("Нажми кнопку под шагом: помогло или нет. Если всё плохо, жми «Позвать человека».")


@router.callback_query(Support.solving, F.data == "step_ok")
async def step_ok(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()
    await state.clear()
    await cb.message.answer("🎉 Отлично, закрываю обращение. Если что-то ещё сломается, пиши.")


@router.callback_query(Support.solving, F.data == "step_fail")
async def step_fail(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()

    data = await state.get_data()
    steps = data["steps_tried"] + [{"step": data["current_step"], "result": "не помогло"}]
    await state.update_data(steps_tried=steps)

    await cb.message.bot.send_chat_action(cb.message.chat.id, ChatAction.TYPING)
    res = await next_step({
        "problem_statement": data["problem"] or data["original"],
        "steps_tried": steps,
        "step_number": data["step_number"],
    })

    if res["status"] == "solving" and res["next_step"]:
        n = data["step_number"] + 1
        await state.update_data(current_step=res["next_step"], step_number=n)
        await send_step(cb.message, state, res["next_step"], n, res["total_steps_estimate"])
    else:
        await escalate(cb.message, state, res.get("specialist_summary"))


@router.callback_query(Support.solving, F.data == "call_human")
async def call_human(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.answer()
    await escalate(cb.message, state, None)


# ============ ЭСКАЛАЦИЯ (сборка тикета, отправку делает D) ============

async def escalate(message: Message, state: FSMContext, summary: str | None):
    data = await state.get_data()
    ticket = {
        "user_id": data["user_id"],
        "username": data["username"],
        "chat_id": message.chat.id,
        "original_message": data["original"],
        "problem_statement": data.get("problem") or data["original"][:200],
        "service": data.get("service"),
        "urgency": data.get("urgency", "medium"),
        "qa": data["qa"],
        "steps_tried": data["steps_tried"],
        "created_at": data["created_at"],
    }
    ticket["summary"] = summary or await specialist_summary(ticket)

    await state.clear()
    await message.answer(
        "🙋 Тут нужен живой специалист. Я передал ему всё: что случилось и что мы пробовали. "
        "Пересказывать ничего не надо, ответ придёт сюда."
    )
    await send_to_specialists(message.bot, ticket)


# ============ ЗАЩИТА ОТ ПРОТУХШИХ КНОПОК (должно быть в самом конце) ============

@router.callback_query()
async def stale_callback(cb: CallbackQuery):
    await cb.answer("Кнопка устарела, опиши проблему заново", show_alert=True)