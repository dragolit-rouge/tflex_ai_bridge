import requests
import json

# Официальный сверхбыстрый шлюз для Qwen 2.5 Coder от SambaNova (работает напрямую без VPN)
API_URL = "https://sambanova.ai"
# Публичный демонстрационный токен для разработчиков
API_KEY = "Bearer 448777a9-d3e9-4670-8b2b-5b565a507746" 

def ask_qwen_to_code(user_prompt):
    print("🤖 Qwen думает над задачей...")
    
    system_instruction = (
        "Ты — эксперт по T-FLEX CAD Open API. Твоя задача — генерировать только чистый C# код "
        "для выполнения внутри макроса. Не пиши никаких объяснений, не пиши ```csharp или ```. "
        "Только код. У тебя есть доступ к объекту 'Document doc = TFlex.Application.ActiveDocument;'. "
        "Пример создания переменной:\n"
        "if (doc != null) {\n"
        "    doc.BeginChanges(\"ИИ\");\n"
        "    Variable v = doc.CreateVariable(\"Имя\");\n"
        "    v.Expression = \"100\";\n"
        "    doc.EndChanges();\n"
        "}"
    )

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "Qwen2.5-Coder-32B-Instruct",
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ Ошибка сервера ИИ (Статус {response.status_code}): {response.text}")
            return None
            
        result = response.json()
        csharp_code = result['choices']['message']['content'].strip()
        
        # Очищаем код от возможных маркеров markdown
        if csharp_code.startswith("```"):
            csharp_code = "\n".join(csharp_code.split("\n")[1:-1])
        return csharp_code
    except Exception as e:
        print("❌ Ошибка соединения с ИИ:", e)
        return None

def send_to_tflex(csharp_code):
    print("🚀 Отправка сгенерированного кода в T-FLEX CAD...")
    try:
        response = requests.post("http://localhost:8080/", data=csharp_code.encode('utf-8'), timeout=5)
        print("📥 Ответ от T-FLEX:", response.text)
    except Exception as e:
        print("❌ Ошибка отправки: Убедитесь, что макрос в T-FLEX запущен!", e)

if __name__ == "__main__":
    print("=== ИИ Ассистент T-FLEX CAD запущен ===")
    print("Напишите, что нужно сделать (например: Создай переменную ИИ_Тест со значением 111)")
    print("Для выхода введите 'exit'\n")
    
    while True:
        prompt = input("👤 Вы: ")
        if prompt.lower() == 'exit':
            break
            
        code = ask_qwen_to_code(prompt)
        
        if code:
            print("\n💻 Сгенерированный C# код:")
            print(code)
            print("-" * 40)
            
            send_to_tflex(code)
            print("=" * 40 + "\n")
