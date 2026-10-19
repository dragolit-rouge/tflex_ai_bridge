using System;
using System.Net;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using TFlex;
using TFlex.Model;

//всегда необходимо проверять, что MyExtension - public class, а Run(или другое имя макроса) - public static
namespace TFlexPlugin
{
    public class MyExtension
    {
        private static HttpListener? _listener;
        private static bool _isServerRunning = false;

        public static void Run()
        {
            if (_isServerRunning) return;

            try
            {
                _listener = new HttpListener();
                // Слушаем все запросы на порту 8080
                _listener.Prefixes.Add("http://localhost:8080/");
                _listener.Start();
                _isServerRunning = true;

                // Запускаем фоновую задачу, которая будет жить всё время работы программы
                Task.Run(() => ListenLoop());
            }
            catch (Exception ex)
            {
                File.WriteAllText(@"C:\tflexmacros\server_error.txt", "Сбой старта: " + ex.ToString());
            }
        }

        private static void ListenLoop()
        {
            while (_isServerRunning && _listener != null)
            {
                try
                {
                    HttpListenerContext context = _listener.GetContext();
                    
                    // Читаем код от Python / ИИ
                    using (var reader = new StreamReader(context.Request.InputStream, Encoding.UTF8))
                    {
                        string csharpCode = reader.ReadToEnd();
                    }

                    // Сразу создаем тестовую переменную
                    Document doc = TFlex.Application.ActiveDocument;
                    if (doc != null)
                    {
                        doc.BeginChanges("Тест ИИ");
                        Variable myVar = doc.CreateVariable("Direct_Test_999");
                        myVar.Expression = "999";
                        doc.EndChanges();
                    }

                    // Отправляем ответ обратно в Python
                    byte[] buffer = Encoding.UTF8.GetBytes("ОК");
                    context.Response.ContentLength64 = buffer.Length;
                    context.Response.OutputStream.Write(buffer, 0, buffer.Length);
                    context.Response.OutputStream.Close();
                }
                catch
                {
                    // Игнорируем внутренние сетевые сбои, чтобы сервер не падал
                }
            }
        }
    }
}
