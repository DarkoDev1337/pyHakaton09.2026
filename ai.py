import os
import json
from dotenv import load_dotenv
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from prompts import ANALYZE_PROMPT, NEXT_STEP_PROMPT, SPECIALIST_SUMMARY_PROMPT

load_dotenv()


def _get_client() -> GigaChat:
    return GigaChat(
        credentials=os.getenv("GIGACHAT_CREDENTIALS"),
        scope="GIGACHAT_API_PERS",
        model="GigaChat-2",
        verify_ssl_certs=False,
    )


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    return raw.strip()


def _safe_fallback(user_text: str, reason: str) -> dict:
    return {
        "problem_summary": user_text[:200],
        "service": "не определено",
        "urgency": "medium",
        "known_facts": [],
        "missing_info": [],
        "next_question": None,
        "next_step": None,
        "step_number": 0,
        "total_steps_estimate": 0,
        "status": "escalate",
        "specialist_summary": f"{reason}. Исходный текст: {user_text[:300]}",
    }


def analyze(user_text: str) -> dict:
    messages = [
        Messages(role=MessagesRole.SYSTEM, content=ANALYZE_PROMPT),
        Messages(role=MessagesRole.USER, content=user_text),
    ]

    try:
        with _get_client() as giga:
            response = giga.chat(Chat(messages=messages))
            raw = response.choices[0].message.content
            cleaned = _clean_json(raw)
            return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"[ai.analyze] JSON decode error: {e}")
        return _safe_fallback(user_text, "AI вернул не JSON")
    except Exception as e:
        print(f"[ai.analyze] Ошибка: {e}")
        return _safe_fallback(user_text, f"Ошибка AI: {type(e).__name__}")


def next_step(ticket: dict) -> dict:
    problem = ticket.get("problem_statement", "")
    steps_tried = ticket.get("steps_tried", [])
    current_step = ticket.get("step_number", 1)

    context = f"problem_statement: {problem}\n"
    context += f"steps_tried: {json.dumps(steps_tried, ensure_ascii=False)}\n"
    context += f"current_step: {current_step}\n"
    context += "Предложи следующий шаг."

    messages = [
        Messages(role=MessagesRole.SYSTEM, content=NEXT_STEP_PROMPT),
        Messages(role=MessagesRole.USER, content=context),
    ]

    try:
        with _get_client() as giga:
            response = giga.chat(Chat(messages=messages))
            raw = response.choices[0].message.content
            cleaned = _clean_json(raw)
            return json.loads(cleaned)
    except Exception as e:
        print(f"[ai.next_step] Ошибка: {e}")
        return {
            "next_step": None,
            "step_number": current_step,
            "total_steps_estimate": 0,
            "status": "escalate",
            "specialist_summary": f"AI не смог предложить шаг. Проблема: {problem[:200]}",
        }


def specialist_summary(ticket: dict) -> str:
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

    messages = [
        Messages(role=MessagesRole.SYSTEM, content=SPECIALIST_SUMMARY_PROMPT),
        Messages(role=MessagesRole.USER, content=context),
    ]

    try:
        with _get_client() as giga:
            response = giga.chat(Chat(messages=messages))
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ai.specialist_summary] Ошибка: {e}")
        return f"Срочность: {urgency}. Проблема: {problem[:200]}. Пробовали: {steps_text}"