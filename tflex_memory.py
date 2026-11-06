import os
import json

MEMORY_FILE = r"C:\tflexmacros\knowledge\working_examples.json"


def load_all_examples():
    """Загружает всю базу сохраненных успешных макросов."""
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Ошибка чтения базы памяти: {e}")
            return []
    return []


def save_working_example(user_prompt: str, working_code: str):
    """Сохраняет успешную связку 'Запрос пользователя -> Рабочий C# код'."""
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    examples = load_all_examples()

    # Избегаем дубликатов точь-в-точь
    for ex in examples:
        if ex.get("code") == working_code:
            print("ℹ️ Этот код уже есть в базе знаний.")
            return

    examples.append({
        "prompt": user_prompt,
        "code": working_code
    })

    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(examples, f, ensure_ascii=False, indent=4)
        print("🎯 [Память] Успешный макрос зафиксирован в базе знаний!")
    except Exception as e:
        print(f"❌ Не удалось сохранить пример в память: {e}")


def get_relevant_examples_context(user_query: str, max_examples: int = 3) -> str:
    """
    Ищет в базе памяти наиболее подходящие эталонные примеры.
    Если совпадений по ключевым словам нет, берет последние успешные.
    """
    examples = load_all_examples()
    if not examples:
        return "Пока нет сохраненных эталонных примеров."

    query_words = set(user_query.lower().split())
    matched_examples = []

    # Простейший поиск по совпадению слов в запросе
    for ex in examples:
        prompt_words = set(ex["prompt"].lower().split())
        if query_words.intersection(prompt_words):
            matched_examples.append(ex)

    # Если по ключевым словам ничего не нашли, берем последние добавленные
    if not matched_examples:
        matched_examples = examples[-max_examples:]
    else:
        matched_examples = matched_examples[-max_examples:]

    context_str = "🧠 ПРОВЕРЕННЫЕ ЭТАЛОНЫ ИЗ ПАМЯТИ (используй их точный синтаксис как образец):\n\n"
    for idx, ex in enumerate(matched_examples, 1):
        context_str += f"Пример #{idx}\nЗапрос: {ex['prompt']}\nРабочий C# код:\n{ex['code']}\n"
        context_str += "-" * 30 + "\n"

    return context_str