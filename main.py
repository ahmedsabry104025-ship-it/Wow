import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from python_aternos import Client

# ==========================================
# 1. جلب متغيرات البيئة من Railway
# ==========================================
USER = os.environ.get("ATERNOS_USER")
PASSWORD = os.environ.get("ATERNOS_PASSWORD")
SERVER_INDEX = int(os.environ.get("SERVER_INDEX", "0"))
PORT = int(os.environ.get("PORT", "8080"))

THREE_HOURS = 3 * 60 * 60
RETRY_DELAY = 5 * 60  # إعادة المحاولة بعد 5 دقائق عند حدوث خطأ

if not USER or not PASSWORD:
    print("❌ خطأ قاتل: يجب إضافة ATERNOS_USER و ATERNOS_PASSWORD في متغيرات البيئة (Railway Variables)!", flush=True)
    sys.exit(1)

# ==========================================
# 2. خادم الـ Health Check لإبقاء البوت نشطاً على Railway
# ==========================================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("Aternos Auto-Restart Bot is Running!".encode('utf-8'))

    def log_message(self, format, *args):
        return

def start_health_check_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    print(f"🚀 تم تشغيل خادم الـ Health Check على المنفذ {PORT}", flush=True)
    server.serve_forever()

# ==========================================
# 3. منطق تشغيل وإعادة تشغيل السيرفر
# ==========================================
def restart_logic():
    print("🤖 تم بدء عمل بوت إعادة تشغيل أترنوس التلقائي...", flush=True)
    
    while True:
        next_delay = THREE_HOURS
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[+] [{timestamp}] جاري الاتصال بأترنوس بحساب: {USER}...", flush=True)
            
            atclient = Client()
            atclient.login(USER, PASSWORD)
            
            aternos = atclient.account
            servers = aternos.list_servers()

            if not servers or len(servers) <= SERVER_INDEX:
                print(f"❌ لم يتم العثور على سيرفر برقم الدليل ({SERVER_INDEX})! عدد السيرفرات المتاحة: {len(servers)}", flush=True)
            else:
                server = servers[SERVER_INDEX]
                server.fetch()
                status = server.status
                print(f"📌 السيرفر: {server.address} | الحالة الحالية: {status}", flush=True)

                if status == "online":
                    print("🔄 السيرفر يعمل حالياً. جاري إرسال أمر إعادة التشغيل (Restart)...", flush=True)
                    server.restart()
                    print("✅ تم إرسال أمر Restart بنجاح!", flush=True)
                
                elif status == "offline":
                    print("▶️ السيرفر متوقف. جاري إرسال أمر التشغيل (Start)...", flush=True)
                    server.start()
                    print("✅ تم إرسال أمر Start بنجاح!", flush=True)
                
                elif status in ["loading", "preparing", "starting", "restarting"]:
                    print(f"⏳ السيرفر في حالة ({status})، لن يتم إرسال أوامر إضافية تجنباً للتعارض.", flush=True)
                
                elif status == "queue":
                    print("⏳ السيرفر حالياً في طابور الانتظار (Queue)...", flush=True)
                    if hasattr(server, 'confirm_queue'):
                        server.confirm_queue()
                        print("✅ تم تأكيد طابور الانتظار بنجاح.", flush=True)
                
                else:
                    print(f"ℹ️ حالة السيرفر حالياً: {status}، سيتم التحقق في الدورة القادمة.", flush=True)

        except Exception as e:
            print(f"⚠️ حدث خطأ أثناء تنفيذ العملية: {e}", flush=True)
            print("⏳ سيتم إعادة المحاولة بعد 5 دقائق لتفادي توقف الخدمة...", flush=True)
            next_delay = RETRY_DELAY

        print(f"⏳ الدورة القادمة بعد: {next_delay // 60} دقيقة...", flush=True)
        time.sleep(next_delay)

# ==========================================
# 4. تشغيل البرنامج
# ==========================================
if __name__ == "__main__":
    health_thread = threading.Thread(target=start_health_check_server, daemon=True)
    health_thread.start()
    restart_logic()
