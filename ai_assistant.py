import os
import xml.etree.ElementTree as ET
import re
import requests
import time


def extract_knowledge_from_xml(user_query):
    """Глубокий парсер XML-библиотеки T-FLEX, который вырезает только нужные классы"""
    xml_path = r"C:\tflexmacros\knowledge\TFlexAPI.xml"
    extracted_hints = ""
    
    if not os.path.exists(xml_path):
        return "⚠️ Внимание: Файл TFlexAPI.xml не найден в папке knowledge!\n"
        
    print(f"🔍 Сканирую XML-библиотеку знаний по запросу '{user_query}'...")
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
                    extracted_hints += f"Элемент API: {name}\nОписание из документации: {summary_clean}\n\n"
                    count += 1
                    
    except Exception as e:
        print("⚠️ Ошибка при чтении XML-документации:", e)
        
    return extracted_hints

import json

def send_to_tflex(csharp_code):
    if not csharp_code: return "Ошибка: пустой код"
    print("🚀 Отправка сгенерированного по XML макроса в T-FLEX CAD...")
    try:
        response = requests.post("http://localhost:8090/", data=csharp_code.encode('utf-8'), timeout=60)
        return response.text.strip()
    except Exception as e:
        return f"❌ Ошибка сети моста: {e}"

def ask_gemini_with_embedded_xml(user_prompt, previous_code=="", error_feedback=""):
    xml_context = extract_knowledge_from_xml(user_prompt)
    
    if error_feedback:
        print("🔄 Gemma исправляет код на основе ошибки от T-FLEX...")
        full_user_content = (
            f"ПРЕДЫДУЩИЙ ВАРИАНТ КОДА:\n{previous_code}\n\n"
            f"ОШИБКА, КОТОРУЮ ВЕРНУЛ T-FLEX CAD:\n{error_feedback}\n\n"
            f"СПРАВКА ИЗ XML-БИБЛИОТЕКИ:\n{xml_context}\n\n"
            f"ЗАДАЧА ПОЛЬЗОВАТЕЛЯ: {user_prompt}\n\n"
            "Исправь ошибку и выдай исправленный чистый построчный код C# без пояснений."
        )
    else:
        print("🤖 Локальная Gemma анализирует вырезки из TFlexAPI.xml и пишет макрос...")
        full_user_content = (
            f"СПРАВКА ИЗ XML-БИБЛИОТЕКИ:\n{xml_context}\n\n"
            f"ЗАДАЧА ПОЛЬЗОВАТЕЛЯ: {user_prompt}\n\n"
            "Используя XML-справку выше, напиши чистый построчный код C#."
        )
    
    system_instruction = (
        "Ты — узкоспециализированный генератор C# макросов для САПР T-FLEX CAD 18 (net48).\n"
        "Выдавай ТОЛЬКО исполняемые строки C# кода, которые вставятся внутрь метода Execute(Document doc).\n"
        "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать ключевые слова: using, class, namespace, public void, public static, или фигурные скобки.\n"
        "Используй методы создания переменных (doc.CreateVariable) и геометрии через API T-FLEX (например, FreeNode, CircleConstruction, Circle)."
    )

    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "gemma2",
        "prompt": f"Системные инструкции:\n{system_instruction}\n\n{full_user_content}",
        "stream": False,
        "options": {"temperature": 0.0}
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

    # Очистка кода от маркдауна и лишних символов
    if "```" in csharp_code:
        lines = csharp_code.split("\n")
        cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
        csharp_code = "\n".join(cleaned_lines)
    csharp_code = csharp_code.replace("`", "").strip()

    # Фильтрация запрещенных строк
    filtered_lines = []
    for line in csharp_code.split("\n"):
        trimmed = line.strip()
        if not trimmed: continue
        if any(trimmed.startswith(w) for w in ["using ", "public ", "private ", "class ", "namespace ", "{", "}"]):
            continue
        filtered_lines.append(line)
        
    return "\n".join(filtered_lines).strip()

if __name__ == "__main__":
    print("=== ОБЛАЧНЫЙ/ЛОКАЛЬНЫЙ ИИ-ИНЖЕНЕР С ОБРАТНОЙ СВЯЗЬЮ ===")
    
    while True:
        prompt = input("\n👤 Запрос: ")
        if prompt.lower() == 'exit': break
        
        current_code = ""
        error_feedback = ""
        max_fix_attempts = 3
        success = False
        
        for attempt in range(max_fix_attempts):
            # Генерация кода (первый раз или с учетом ошибки)
            current_code = ask_gemini_with_embedded_xml(prompt, previous_code=current_code, error_feedback=error_feedback)
            
            if not current_code:
                print("❌ Не удалось сгенерировать код.")
                break
                
            print(f"\n💻 Сгенерированный код C# (попытка {attempt + 1}):")
            print(current_code)
            print("-" * 40)
            
            # Отправка в T-FLEX
            tflex_response = send_to_tflex(current_code)
            print(f"📥 Ответ от T-FLEX: {tflex_response}")
            
            if tflex_response == "ОК":
                print("✅ Макрос успешно выполнен без ошибок!")
                success = True
                break
            else:
                print(f"⚠️ Обнаружена ошибка в T-FLEX. Передаем её обратно в Gemma для исправления...")
                error_feedback = tflex_response
                time.sleep(2)
                
        if not success:
            print("❌ Не удалось добиться успешного выполнения макроса после нескольких попыток.")
        print("=" * 40 + "\n")