import os
import xml.etree.ElementTree as ET
import re
import requests
import time
# Импортируем наш новый отдельный модуль памяти
from tflex_memory import save_working_example, get_relevant_examples_context


def extract_knowledge_from_xml(user_query):
    """Глубокий парсер XML-библиотеки T-FLEX"""
    xml_path = r"C:\tflexmacros\knowledge\TFlexAPI.xml"
    extracted_hints = ""
    
    if not os.path.exists(xml_path):
        return "⚠️ Внимание: Файл TFlexAPI.xml не найден в папке knowledge!\n"
        
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        search_terms = ["Cylinder", "Cone", "Sphere", "Variable", "Document", "View", "Redraw", "Line", "Circle", "Constraint"]
        matched_terms = [term for term in search_terms if term.lower() in user_query.lower()]
        if not matched_terms:
            matched_terms = ["Document", "Model2D"]

        count = 0
        for member in root.findall(".//member"):
            name = member.get("name", "")
            summary_node = member.find("summary")
            
            if any(term in name for term in matched_terms) and summary_node is not None:
                summary_text = summary_node.text.strip() if summary_node.text else ""
                if summary_text and count < 15:
                    summary_clean = re.sub(r'\s+', ' ', summary_text)
                    extracted_hints += f"Элемент API: {name}\nОписание: {summary_clean}\n\n"
                    count += 1
    except Exception as e:
        print("⚠️ Ошибка при чтении XML:", e)
        
    return extracted_hints


def fix_missing_semicolons(csharp_code):
    """Автоматически подставляет пропущенные точки с запятой"""
    fixed_lines = []
    for line in csharp_code.split("\n"):
        stripped = line.strip()
        if stripped and not stripped.endswith(";") and not stripped.endswith("{") and not stripped.startswith("//"):
            fixed_lines.append(line + ";")
        else:
            fixed_lines.append(line)
    return "\n".join(fixed_lines)


def send_to_tflex(csharp_code):
    """Отправляет код на локальный сервер моста T-FLEX CAD"""
    if not csharp_code: return "Ошибка: пустой код"
    print("🚀 Отправка сгенерированного макроса в T-FLEX CAD...")
    try:
        response = requests.post("http://localhost:8090/", data=csharp_code.encode('utf-8'), timeout=60)
        return response.text.strip()
    except Exception as e:
        return f"❌ Ошибка сети моста: {e}"


def ask_gemini_with_embedded_xml(user_prompt, previous_code="", error_feedback=""):
    xml_context = extract_knowledge_from_xml(user_prompt)
    # Достаем релевантные примеры из нашего нового модуля памяти
    memory_context = get_relevant_examples_context(user_prompt)
    
    current_temperature = 0.0
    
    if error_feedback:
        current_temperature = 0.4
        print(f"🔄 Gemma исправляет ошибку (Температура: {current_temperature})...")
        full_user_content = (
            f"ЗАДАЧА ПОЛЬЗОВАТЕЛЯ: {user_prompt}\n\n"
            f"ОШИБКА ОТ T-FLEX CAD:\n{error_feedback}\n\n"
            f"ПРЕДЫДУЩИЙ ОШИБОЧНЫЙ КОД:\n{previous_code}\n\n"
            "Напиши ИСПРАВЛЕННЫЙ вариант кода. Избегай ошибки выше! Каждая строка должна заканчиваться ';'."
        )
    else:
        print("🤖 Локальная Gemma анализирует эталоны памяти и XML-справку...")
        full_user_content = (
            f"{memory_context}\n\n"
            f"СПРАВКА ИЗ XML-БИБЛИОТЕКИ:\n{xml_context}\n\n"
            f"НОВАЯ ЗАДАЧА ПОЛЬЗОВАТЕЛЯ: {user_prompt}\n\n"
            "Используя эталоны из памяти и XML-справку, напиши чистый построчный код C#."
        )
    
    system_instruction = (
        "Ты — узкоспециализированный генератор C# макросов для САПР T-FLEX CAD 18 (net48).\n"
        "Выдавай ТОЛЬКО исполняемые строки C# кода внутрь метода Execute(Document doc).\n"
        "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать: using, class, namespace, public void, public static, или фигурные скобки.\n"
        "Каждая строка/инструкция кода ОБЯЗАТЕЛЬНО должна заканчиваться точкой с запятой (;)."
    )

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "gemma2",
        "prompt": f"Системные инструкции:\n{system_instruction}\n\n{full_user_content}",
        "stream": False,
        "options": {"temperature": current_temperature}
    }

    try:
        response = requests.post(url, json=payload, timeout=180)
        if response.status_code == 200:
            csharp_code = response.json().get("response", "").strip()
        else:
            return None
    except Exception as e:
        print("❌ Ошибка связи с Ollama:", e)
        return None

    # Очистка
    if "```" in csharp_code:
        lines = csharp_code.split("\n")
        cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
        csharp_code = "\n".join(cleaned_lines)
    csharp_code = csharp_code.replace("`", "").strip()

    filtered_lines = []
    for line in csharp_code.split("\n"):
        trimmed = line.strip()
        if not trimmed: continue
        if any(trimmed.startswith(w) for w in ["using ", "public ", "private ", "class ", "namespace ", "{", "}"]):
            continue
        filtered_lines.append(line)
        
    final_code = "\n".join(filtered_lines).strip()
    return fix_missing_semicolons(final_code)


if __name__ == "__main__":
    print("=== ИИ-ИНЖЕНЕР С ИСТОРИЕЙ ОШИБОК И ЗАЩИТОЙ ОТ ПОВТОРОВ ===")
    
    while True:
        prompt = input("\n👤 Запрос: ")
        if prompt.lower() == 'exit': break
        
        current_code = ""
        error_feedback = ""
        max_fix_attempts = 15
        success = False
        
        # 📜 История всех неудачных вариантов кода для текущей задачи
        history_of_failed_codes = []
        
        attempt = 0
        while attempt < max_fix_attempts:
            attempt += 1
            print(f"\n--- Попытка генерации #{attempt} ---")
            
            # Генерация с учетом истории неудачных попыток
            current_code = ask_gemini_with_embedded_xml(
                user_prompt=prompt, 
                previous_code=current_code, 
                error_feedback=error_feedback
            )
            
            if not current_code:
                print("❌ Не удалось сгенерировать код.")
                break
                
            # 🛡️ ПРОВЕРКА ПО ВСЕЙ ИСТОРИИ: если этот код уже был на ЛЮБОЙ из прошлых попыток
            if current_code in history_of_failed_codes:
                print("⚠️ ВНИМАНИЕ: Модель предложила вариант кода, который ОНА УЖЕ СЕГОДНЯ ПРОБОВАВА И ОН УПАЛ!")
                print("🔄 Прессуем модель историей ошибок, попытка не сгорает...")
                
                error_feedback = (
                    "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять код из списка неудачных попыток ниже! "
                    "Все эти варианты уже компилировались с ошибкой. Придумай совершенно другую структуру."
                )
                attempt -= 1  # Попытка не сгорает
                time.sleep(1)
                continue

            # Добавляем свежий провальный вариант в копилку истории (перед отправкой в T-FLEX)
            # Примечание: если тест пройдет успешно, мы его оттуда удалим/неважно, цикл прервется по break.
            
            print(f"💻 Сгенерированный код C#:")
            print(current_code)
            print("-" * 40)
            
            # Отправка в T-FLEX
            tflex_response = send_to_tflex(current_code)
            print(f"📥 Ответ от T-FLEX: {tflex_response}")
            
            if tflex_response == "ОК":
                print("✅ Макрос успешно выполнен без ошибок!")
                save_working_example(prompt, current_code)
                success = True
                break
            else:
                print(f"⚠️ Ошибка в T-FLEX. Запоминаем этот тупик в историю...")
                if current_code not in history_of_failed_codes:
                    history_of_failed_codes.append(current_code)
                
                # 🧠 ИНТЕЛЛЕКТУАЛЬНЫЙ ПЕРЕВОДЧИК ОШИБОК ДЛЯ ГЕММЫ:
                # Если T-FLEX ругается на пропущенный using/сборку, разжевываем модели, что делать:
                parsed_hint = ""
                if "пропущена директива using" in tflex_response or "отсутствует в текущем контексте" in tflex_response:
                    parsed_hint = (
                        "\n💡 РАСШИФРОВКА ОШИБКИ ДЛЯ ТЕБЯ:\n"
                        "Ты используете класс или метод без полного пути. Поскольку ключевое слово 'using' писать запрещено, "
                        "ты ОБЯЗАТЕЛЬНО должна указывать полное пространство имен для всех классов T-FLEX "
                        "(например: TFlex.Model.Model2D.CircleConstruction вместо просто CircleConstruction).\n"
                    )

                failed_history_text = "\n\n".join([f"Попытка #{i+1}:\n{code}" for i, code in enumerate(history_of_failed_codes)])
                
                error_feedback = (
                    f"Ответ от T-FLEX: {tflex_response}\n"
                    f"{parsed_hint}\n"
                    f"СПИСОК ТВОИХ ПРОШЛЫХ ОШИБОЧНЫХ ВАРИАНТОВ (НЕ ПОВТОРЯЙ ИХ):\n{failed_history_text}"
                )
                time.sleep(2)
                
        if not success:
            print("❌ Не удалось добиться успешного выполнения макроса за отведенные попытки.")
        print("=" * 40 + "\\n")