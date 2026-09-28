import asyncio
import json
from ai import analyze, next_step, specialist_summary


def show(title, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


async def main():
    show("Простое: почта", await analyze("Не открывается корпоративная почта, пишет 'ошибка авторизации'"))
    show("Неоднозначное", await analyze("У меня опять всё сломалось"))
    show("Срочное", await analyze(
        "Срочно! Не могу зайти в рабочую систему с ноутбука. С телефона открывается, с ноутбука нет. Через 20 минут встреча!"
    ))
    show("Нерешаемое", await analyze(
        "Пропал доступ к 1С. Пишет 'нет прав доступа'. Меня перевели в другой отдел."
    ))

    # Тест с историей уточнений
    show("С уточнением", await analyze(
        "Не могу зайти в рабочую систему с ноутбука",
        qa=[{"q": "Что видите на экране?", "a": "Белый экран и бесконечная загрузка"}],
    ))

    ticket = {
        "problem_statement": "Не открывается корпоративная почта, ошибка авторизации",
        "steps_tried": [{"step": "Выйти и войти заново", "result": "не помогло"}],
        "step_number": 1,
    }
    show("Следующий шаг", await next_step(ticket))

    ticket_full = {
        "original_message": "Срочно! Не могу зайти в рабочую систему с ноутбука. Через 20 минут встреча!",
        "problem_statement": "Не может войти в рабочую систему с ноутбука",
        "steps_tried": [
            {"step": "Проверить VPN", "result": "не помогло"},
            {"step": "Перезагрузить ноутбук", "result": "не помогло"},
        ],
        "urgency": "high",
    }
    print("\n=== Сводка для специалиста ===")
    print(await specialist_summary(ticket_full))


asyncio.run(main())