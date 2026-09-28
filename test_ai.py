import json
from ai import analyze, next_step, specialist_summary


def show(title: str, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2))


# --- Тесты analyze() ---

show("Простое: почта", analyze("Не открывается корпоративная почта, пишет 'ошибка авторизации'"))

show("Неоднозначное", analyze("У меня опять всё сломалось"))

show("Срочное", analyze(
    "Срочно! Не могу зайти в рабочую систему с ноутбука. С телефона открывается, с ноутбука нет. Через 20 минут встреча!"
))

show("Нерешаемое", analyze(
    "Пропал доступ к 1С. Пишет 'нет прав доступа'. Меня перевели в другой отдел."
))

# --- Тест next_step() ---

ticket = {
    "problem_statement": "Не открывается корпоративная почта, ошибка авторизации",
    "steps_tried": [{"step": "Выйти и войти заново", "result": "не помогло"}],
    "step_number": 1,
}
show("Следующий шаг", next_step(ticket))

# --- Тест specialist_summary() ---

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
print(specialist_summary(ticket_full))