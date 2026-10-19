using System;
using System.Net;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.CodeDom.Compiler;
using Microsoft.CSharp;
using System.Reflection;
using TFlex;
using TFlex.Model;

namespace TFlexPlugin
{
    public class MyExtension
    {
        private static HttpListener? _listener;
        private static bool _isServerRunning = false;
        private static Document? _savedDoc;

        public static void Run()
        {
            if (_isServerRunning) return;
            try
            {
                _savedDoc = TFlex.Application.ActiveDocument;
                _listener = new HttpListener();
                _listener.Prefixes.Add("http://localhost:8090/");
                _listener.Start();
                _isServerRunning = true;
                Task.Run(() => ListenLoop());
            }
            catch (Exception ex)
            {
                File.WriteAllText(@"C:\tflexmacros\server_error.txt", ex.ToString());
            }
        }

        private static void ListenLoop()
        {
            while (_isServerRunning && _listener != null)
            {
                try
                {
                    HttpListenerContext context = _listener.GetContext();
                    string responseText = "ОК";

                    using (var reader = new StreamReader(context.Request.InputStream, Encoding.UTF8))
                    {
                        string csharpCode = reader.ReadToEnd();
                        if (_savedDoc != null)
                        {
                            string executeError = ExecuteDynamicCode(csharpCode, _savedDoc);
                            if (!string.IsNullOrEmpty(executeError))
                            {
                                responseText = "ERROR_CS: " + executeError;
                            }
                        }
                        else
                        {
                            responseText = "ERROR_SYS: Нет active document!";
                        }
                    }

                    byte[] buffer = Encoding.UTF8.GetBytes(responseText);
                    context.Response.ContentLength64 = buffer.Length;
                    context.Response.OutputStream.Write(buffer, 0, buffer.Length);
                    context.Response.OutputStream.Close();
                }
                catch { }
            }
        }

        private static string ExecuteDynamicCode(string innerCode, Document doc)
        {
            try
            {
                // Убрали несуществующее пространство .Model3D
                string fullSource = $@"
                using System;
                using System.Windows.Forms;
                using TFlex;
                using TFlex.Model;

                public class CodeExecutor {{
                    public static void Execute(Document doc) {{
                        {innerCode}
                    }}
                }}";

                CSharpCodeProvider provider = new CSharpCodeProvider();
                CompilerParameters parameters = new CompilerParameters();
                parameters.ReferencedAssemblies.Add("System.dll");
                parameters.ReferencedAssemblies.Add("System.Windows.Forms.dll");
                parameters.ReferencedAssemblies.Add(typeof(Document).Assembly.Location);
                parameters.GenerateInMemory = true;

                CompilerResults results = provider.CompileAssemblyFromSource(parameters, fullSource);
                if (results.Errors.HasErrors)
                {
                    StringBuilder sb = new StringBuilder();
                    foreach (CompilerError error in results.Errors) sb.AppendLine(error.ErrorText);
                    return sb.ToString();
                }

                MethodInfo method = results.CompiledAssembly.GetType("CodeExecutor").GetMethod("Execute");
                method.Invoke(null, new object[] { doc });
                return string.Empty;
            }
            catch (Exception ex) { return ex.ToString(); }
        }
    }
}
