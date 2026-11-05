import os
import xml.etree.ElementTree as ET
import re
import requests
from google import genai

client = genai.Client(api_key="AQ.Ab8RN6Ln36HdUcjCZ-iRjrq3KkkWEoNoxdf_KJurXGqEqrIJ7w")

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

def ask_gemini_with_embedded_xml(user_prompt):
    xml_context = extract_knowledge_from_xml(user_prompt)
    
    print("🤖 Gemini анализирует вырезки из TFlexAPI.xml и пишет макрос...")
    
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

    # Формируем полный промпт, включая динамически вырезанный контекст из XML
    full_user_content = (
        f"СПРАВКА ИЗ XML-БИБЛИОТЕКИ:\n{xml_context}\n\n"
        f"ЗАДАЧА ПОЛЬЗОВАТЕЛЯ: {user_prompt}\n\n"
        "Используя XML-справку выше, напиши чистый построчный код C#."
    )

    try:
        # Запрос к Gemini через официальный современный SDK
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=full_user_content,
            config={
                'system_instruction': system_instruction,
                'temperature': 0.0 # Жестко детерминированный ответ для написания кода
            }
        )
        
        csharp_code = response.text.strip()
        
        # 1. Стираем маркдаун (если модель обернула код в ```csharp ... ```)
        if "```" in csharp_code:
            lines = csharp_code.split("\n")
            cleaned_lines = [line for line in lines if not line.strip().startswith("```")]
            csharp_code = "\n".join(cleaned_lines)
        csharp_code = csharp_code.replace("`", "").strip()

        # 2. ЖЕСТКАЯ ХАКЕРСКАЯ КОРРЕКЦИЯ СИНТАКСИСА ПОД СТАРУЮ ВЕРСИЮ API 18 (net48)
        csharp_code = csharp_code.replace("TFlex.Application.Window.PostCommand", "TFlex.Application.PostCommand")
        csharp_code = csharp_code.replace("TFlex.Application.ActiveMainWindow.PostCommand", "TFlex.Application.PostCommand")
        csharp_code = csharp_code.replace("TFlex.Application.ActiveWindow.PostCommand", "TFlex.Application.PostCommand")
        
        csharp_code = csharp_code.replace("doc.ViewRedraw();", "doc.Redraw();")
        csharp_code = csharp_code.replace("doc.Refresh();", "doc.Redraw();")

        # ХАК ДЛЯ СТАРОГО API: Срезаем несуществующие прослойки Model2D и Object2D
        csharp_code = csharp_code.replace("doc.Model2D.Constraint", "TFlex.Model.Model2D.Constraint")
        csharp_code = csharp_code.replace("doc.Model2D.Object2D", "doc")
        csharp_code = csharp_code.replace("doc.Model2D", "doc")

        # 3. Фильтр структуры
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
    except Exception as e:
        print("❌ Ошибка связи с Gemini API:", e)
        return None

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