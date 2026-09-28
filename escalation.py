import os
import html
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()
SPECIALIST_CHAT_ID = os.getenv("SPECIALIST_CHAT_ID")


def format_ticket(t: dict) -> str:
    e = html.escape
    urgent = "🔥 СРОЧНО " if t["urgency"] == "high" else ""
    qa = "\n".join(f"• {e(x['q'])} → {e(x['a'])}" for x in t["qa"]) or "—"
    steps = "\n".join(f"• {e(str(s['step']))} — {e(s['result'])}" for s in t["steps_tried"]) or "—"
    return (
        f"🚨 {urgent}<b>Новое обращение</b>\n"
        f"👤 @{e(t['username'] or 'без_ника')} (id {t['user_id']})\n"
        f"📌 <b>Проблема:</b> {e(t['problem_statement'])}\n"
        f"🧩 <b>Сервис:</b> {e(t['service'] or 'не определено')}\n"
        f"💬 <b>Исходное:</b> {e(t['original_message'])}\n\n"
        f"❓ <b>Уточнения:</b>\n{qa}\n\n"
        f"🔧 <b>Пробовали:</b>\n{steps}\n\n"
        f"📝 <b>Сводка:</b> {e(t['summary'])}"
    )


async def send_to_specialists(bot: Bot, ticket: dict):
    text = format_ticket(ticket)
    if SPECIALIST_CHAT_ID:
        await bot.send_message(int(SPECIALIST_CHAT_ID), text)
    else:
        print("\n[ESCALATION]\n" + text)  # пока чата нет, просто печатаем в консоль