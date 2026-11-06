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

def ask_gemini_with_embedded_xml(user_prompt):
    xml_context = extract_knowledge_from_xml(user_prompt)
    
    print("🤖 Локальная Gemma анализирует вырезки из TFlexAPI.xml и пишет макрос...")
    
    system_instruction = (
        "Ты — узкоспециализированный генератор C# макросов для САПР T-FLEX CAD 18 (net48).\n"
        "Выдавай ТОЛЬКО исполняемые строки C# кода, которые вставятся внутрь метода Execute(Document doc).\n"
        "КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО писать ключевые слова: using, class, namespace, public void, public static, или фигурные скобки.\n"
        "ЗАПРЕЩЕНО использовать любые методы типа doc.Circle(), doc.TransformationGroup, Fragment.Circle — их НЕ СУЩЕСТВУЕТ!\n\n"
        "ПРАВИЛА АВТОМАТИЗАЦИИ:\n"
        "Если пользователь просит нарисовать круг, окружность, квадрат, цилиндр или деталь, ты должен сделать строго две вещи:\n"
        "1. Создать управляющие переменные размеров чертежа (например, AI_Radius, AI_Height, AI_Width) через doc.CreateVariable.\n"
        "2. Вывести красивое виндовое окно-уведомление через MessageBox.Show, сообщающее, что параметры геометрии успешно сгенерированы.\n\n"
        "Пример идеального ответа:\n"
        "doc.BeginChanges(\"ИИ_Геометрия\");\n"
        "Variable v1 = doc.CreateVariable(\"AI_Size\");\n"
        "if (v1 != null) v1.Expression = \"100\";\n"
        "doc.EndChanges();\n"
        "MessageBox.Show(\"Параметры успешно переданы в T-FLEX!\", \"ИИ Ассистент\");\n"
        "doc.Redraw();"
    )

    full_user_content = (
        f"СИСТЕМНЫЕ ИНСТРУКЦИИ:\n{system_instruction}\n\n"
        f"СПРАВКА ИЗ XML-БИБЛИОТЕКИ:\n{xml_context}\n\n"
        f"ЗАДАЧА ПОЛЬЗОВАТЕЛЯ: {user_prompt}\n\n"
        "Используя XML-справку выше, напиши чистый построчный код C#."
    )

    # Параметры запроса к локальной Ollama
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "gemma2",  # Укажите имя вашей локальной модели
        "prompt": full_user_content,
        "stream": False,
        "options": {
            "temperature": 0.0
        }
    }

    max_retries = 3
    csharp_code = ""
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=180)
            if response.status_code == 200:
                res_json = response.json()
                csharp_code = res_json.get("response", "").strip()
                break
            else:
                print(f"⚠️ Ошибка сервера Ollama: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Попытка {attempt + 1} не удалась. Повтор через 3 секунды...")
            time.sleep(3)
            if attempt == max_retries - 1:
                print("❌ Ошибка связи с локальной моделью Ollama:", e)
                return None

    # Очистка кода (остается без изменений)
    if "```" in csharp_code:
        lines = csharp_code.split("\n")
        cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
        csharp_code = "\n".join(cleaned_lines)
    csharp_code = csharp_code.replace("`", "").strip()

    csharp_code = csharp_code.replace("TFlex.Application.Window.PostCommand", "TFlex.Application.PostCommand")
    csharp_code = csharp_code.replace("TFlex.Application.ActiveMainWindow.PostCommand", "TFlex.Application.PostCommand")
    csharp_code = csharp_code.replace("TFlex.Application.ActiveWindow.PostCommand", "TFlex.Application.PostCommand")
    csharp_code = csharp_code.replace("doc.ViewRedraw();", "doc.Redraw();")
    csharp_code = csharp_code.replace("doc.Refresh();", "doc.Redraw();")
    csharp_code = csharp_code.replace("doc.Model2D.Constraint", "TFlex.Model.Model2D.Constraint")
    csharp_code = csharp_code.replace("doc.Model2D.Object2D", "doc")
    csharp_code = csharp_code.replace("doc.Model2D", "doc")

    filtered_lines = []
    for line in csharp_code.split("\n"):
        trimmed = line.strip()
        if not trimmed:
            continue
        if (trimmed.startswith("using ") or 
            trimmed.startswith("public ") or 
            trimmed.startswith("private ") or 
            trimmed.startswith("class ") or 
            trimmed.startswith("namespace ") or 
            trimmed == "{" or 
            trimmed == "}"):
            continue
        if any(char.lower() in 'абвгдежзийклмнопрстуфхцчшщъыьэюя' for char in trimmed[:3]):
            continue
        filtered_lines.append(line)
        
    return "\n".join(filtered_lines).strip()


def send_to_tflex(csharp_code):
    if not csharp_code: return
    print("🚀 Отправка сгенерированного по XML макроса в T-FLEX CAD...")
    try:
        response = requests.post("http://localhost:8090/", data=csharp_code.encode('utf-8'), timeout=15)
        status = response.text
        if status == "ОК":
            print("📥 Ответ от T-FLEX: Макрос успешно выполнен!")
        else:
            print(f"📥 Ответ от T-FLEX:\n{status}")
    except Exception as e:
        print("❌ Ошибка сети моста:", e)

if __name__ == "__main__":
    print("=== ОБЛАЧНЫЙ ИИ-ИНЖЕНЕР (GEMINI) С ИНТЕГРАЦИЕЙ XML-БИБЛИОТЕК ===")
    print("Программа на лету вырезает справочные данные из TFlexAPI.xml под каждый ваш запрос.\n")
    
    while True:
        prompt = input("👤 Запрос: ")
        if prompt.lower() == 'exit': break
        code = ask_gemini_with_embedded_xml(prompt)
        if code:
            print("\n💻 Сгенерированный по XML код C#:")
            print(code)
            print("-" * 40)
            send_to_tflex(code)
            print("=" * 40 + "\n")