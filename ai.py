import os
import json
from dotenv import load_dotenv
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from prompts import ANALYZE_PROMPT, NEXT_STEP_PROMPT, SPECIALIST_SUMMARY_PROMPT

load_dotenv()

# Клиент создаётся ОДИН раз, а не на каждый вызов
_giga = GigaChat(
    credentials=os.getenv("GIGACHAT_CREDENTIALS"),
    scope="GIGACHAT_API_PERS",
    model="GigaChat-2",
    verify_ssl_certs=False,
)

DEFAULTS = {
    "problem_summary": "",
    "service": "не определено",
    "urgency": "medium",
    "known_facts": [],
    "missing_info": [],
    "next_question": None,
    "next_step": None,
    "step_number": 0,
    "total_steps_estimate": 0,
    "status": "escalate",
    "specialist_summary": None,
}


async def _ask(system: str, user: str, temperature: float = 0.2) -> str:
    resp = await _giga.achat(Chat(
        messages=[
            Messages(role=MessagesRole.SYSTEM, content=system),
            Messages(role=MessagesRole.USER, content=user),
        ],
        temperature=temperature,
    ))
    return resp.choices[0].message.content


def _extract_json(raw: str) -> str:
    start, end = raw.find("{"), raw.rfind("}")
    return raw[start:end + 1] if start != -1 and end != -1 else raw


def _safe_fallback(user_text: str, reason: str) -> dict:
    return {
        **DEFAULTS,
        "problem_summary": user_text[:200],
        "status": "escalate",
        "specialist_summary": f"{reason}. Исходный текст: {user_text[:300]}",
    }


async def analyze(original: str, qa: list[dict] | None = None) -> dict:
    """
    original — первое сообщение юзера
    qa — история уточнений: [{"q": "вопрос бота", "a": "ответ юзера"}, ...]
    """
    context = f"Исходное обращение: {original}\n"
    for item in qa or []:
        context += f"Вопрос: {item['q']}\nОтвет пользователя: {item['a']}\n"

    for _ in range(2):  # один ретрай перед эскалацией
        try:
            raw = await _ask(ANALYZE_PROMPT, context)
            return {**DEFAULTS, **json.loads(_extract_json(raw))}
        except Exception as e:
            print(f"[ai.analyze] {type(e).__name__}: {e}")
    return _safe_fallback(original, "AI не вернул валидный JSON")


async def next_step(ticket: dict) -> dict:
    problem = ticket.get("problem_statement", "")
    steps_tried = ticket.get("steps_tried", [])
    current_step = ticket.get("step_number", 1)

    # Жёсткий лимит в коде, а не только в промпте
    if current_step >= 4:
        return {
            "next_step": None,
            "step_number": current_step,
            "total_steps_estimate": 4,
            "status": "escalate",
            "specialist_summary": None,
        }

    context = (
        f"problem_statement: {problem}\n"
        f"steps_tried: {json.dumps(steps_tried, ensure_ascii=False)}\n"
        f"current_step: {current_step}\n"
        "Предложи следующий шаг."
    )

    for _ in range(2):
        try:
            raw = await _ask(NEXT_STEP_PROMPT, context)
            return json.loads(_extract_json(raw))
        except Exception as e:
            print(f"[ai.next_step] {type(e).__name__}: {e}")
    return {
        "next_step": None,
        "step_number": current_step,
        "total_steps_estimate": 0,
        "status": "escalate",
        "specialist_summary": f"AI не смог предложить шаг. Проблема: {problem[:200]}",
    }


async def specialist_summary(ticket: dict) -> str:
    original = ticket.get("original_message", "")
    problem = ticket.get("problem_statement", "")
    steps_tried = ticket.get("steps_tried", [])
    urgency = ticket.get("urgency", "medium")

    steps_text = "; ".join(
        f"{s.get('step', '')} — {s.get('result', '')}" for s in steps_tried
    ) or "шагов не было"

    context = (
        f"Исходное обращение: {original}\n"
        f"Проблема: {problem}\n"
        f"Что пробовали: {steps_text}\n"
        f"Срочность: {urgency}"
    )

    try:
        return (await _ask(SPECIALIST_SUMMARY_PROMPT, context)).strip()
    except Exception as e:
        print(f"[ai.specialist_summary] {type(e).__name__}: {e}")
        return f"Срочность: {urgency}. Проблема: {problem[:200]}. Пробовали: {steps_text}"