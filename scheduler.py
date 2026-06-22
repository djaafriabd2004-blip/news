import os
import time
import sys
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# إضافة المسار الحالي للمكتبات لضمان إمكانية الاستيراد
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# استيراد دالة التشغيل الرئيسية من السكربت الأصلي
from ai_poster import main as run_poster

# تحميل متغيرات البيئة
load_dotenv()

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK")
        
    def log_message(self, format, *args):
        # لمنع إغراق السجلات بطلبات فحص الصحة من الاستضافة
        pass

def run_health_server():
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        print(f"[*] بدء خادم فحص الصحة على المنفذ: {port}")
        server.serve_forever()
    except Exception as e:
        print(f"[-] خطأ أثناء تشغيل خادم فحص الصحة: {e}")

# نمط الجدولة المختار:
# 1. 'interval': نشر دوري كل X ثانية (مثالي للنشر المتقارب مثل كل نصف ساعة).
# 2. 'peak_hours': نشر في ساعات ذروة محددة مسبقاً.
SCHEDULER_MODE = os.getenv("SCHEDULER_MODE", "interval").lower()

# الإعدادات لنمط الدوري (Interval Mode)
# 1800 ثانية تعادل 30 دقيقة تماماً (للنشر كل نصف ساعة)
INTERVAL_SECONDS = int(os.getenv("POST_INTERVAL_SECONDS", 1800))

# الإعدادات لنمط ساعات الذروة (Peak Hours Mode)
TIMEZONE_OFFSET = int(os.getenv("TIMEZONE_OFFSET", 1)) # توقيت الجزائر المحلي
DEFAULT_PEAK_HOURS = "08:00,09:30,11:00,13:00,14:30,16:00,18:00,20:00,21:30,23:00"
PEAK_HOURS_STR = os.getenv("PEAK_HOURS", DEFAULT_PEAK_HOURS)
PEAK_HOURS = [h.strip() for h in PEAK_HOURS_STR.split(",") if h.strip()]

# تفعيل التفاوت الزمني العشوائي البشري
USE_JITTER = os.getenv("USE_JITTER", "True").lower() in ("true", "1", "yes")
JITTER_MAX_SECONDS = int(os.getenv("JITTER_MAX_SECONDS", 180)) # 3 دقائق كحد أقصى للتباعد الدوري القصير

def get_user_local_time():
    """
    حساب الوقت الحالي بتوقيت المستخدم المحلي بناءً على فرق التوقيت المختار (Offset).
    """
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=TIMEZONE_OFFSET)

def get_seconds_until_next_peak():
    """
    حساب عدد الثواني المتبقية حتى وقت الذروة القادم.
    """
    user_now = get_user_local_time()
    today_runs = []
    for ph in PEAK_HOURS:
        try:
            hour, minute = map(int, ph.split(":"))
            run_dt = user_now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            today_runs.append(run_dt)
        except Exception as e:
            print(f"[-] خطأ في تنسيق وقت الذروة '{ph}': {e}")
            
    if not today_runs:
        return 7200, user_now + timedelta(hours=2)

    today_runs.sort()
    next_run = None
    for run_dt in today_runs:
        if run_dt > user_now:
            next_run = run_dt
            break
            
    if not next_run:
        first_run = today_runs[0]
        next_run = first_run + timedelta(days=1)
        
    delta = next_run - user_now
    return delta.total_seconds(), next_run

def start_scheduler():
    # تهيئة الترميز للغة العربية
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    # تشغيل خادم فحص الصحة في خلفية مستقلة لمنع إعادة تشغيل Railway للحاوية
    if os.getenv("PORT") or os.getenv("RAILWAY_STATIC_URL"):
        t = threading.Thread(target=run_health_server, daemon=True)
        t.start()

    print("="*60)
    print("  بدء تشغيل جدولة النشر التلقائي للذكاء الاصطناعي على الاستضافة")
    print(f"  نمط الجدولة الحالي: {SCHEDULER_MODE.upper()}")
    
    if SCHEDULER_MODE == "peak_hours":
        print(f"  المنطقة الزمنية للمستخدم: UTC+{TIMEZONE_OFFSET}")
        print(f"  ساعات الذروة ({len(PEAK_HOURS)} أوقات): {', '.join(PEAK_HOURS)}")
    else:
        print(f"  الفاصل الدوري المحدد: كل {INTERVAL_SECONDS / 60:.1f} دقيقة (حوالي {24 / (INTERVAL_SECONDS / 3600):.1f} منشور يومياً)")
        
    if USE_JITTER:
        print(f"  التفاوت العشوائي نشط: تفاوت يصل إلى ±{JITTER_MAX_SECONDS / 60:.1f} دقيقة لجعل النشر يبدو بشرياً.")
    print("="*60)

    try:
        # تشغيل السكربت للمرة الأولى فور تشغيله لتأكيد عمله
        print(f"\n[*] [{get_user_local_time().strftime('%H:%M:%S')}] تشغيل أولي للتحقق...")
        try:
            run_poster()
        except Exception as e:
            print(f"[-] خطأ أثناء التشغيل الأولي: {e}")

        while True:
            # حساب وقت الانتظار بناءً على النمط المختار
            current_jitter = 0
            if USE_JITTER:
                current_jitter = random.randint(-JITTER_MAX_SECONDS, JITTER_MAX_SECONDS)
                
            if SCHEDULER_MODE == "peak_hours":
                seconds_to_wait, next_run_dt = get_seconds_until_next_peak()
                actual_wait = max(10, seconds_to_wait + current_jitter)
                actual_next_run = get_user_local_time() + timedelta(seconds=actual_wait)
                print(f"\n[*] الاستراحة نشطة للوصول لوقت الذروة التالي: {next_run_dt.strftime('%H:%M:%S')}")
            else:
                # نمط الفاصل الزمني الدوري
                actual_wait = max(30, INTERVAL_SECONDS + current_jitter)
                actual_next_run = get_user_local_time() + timedelta(seconds=actual_wait)
                print(f"\n[*] الاستراحة نشطة للدورة الدورية القادمة.")
                
            print(f"[*] التفاوت العشوائي المطبق: {current_jitter/60:+.1f} دقيقة.")
            print(f"[*] الموعد الفعلي للنشر القادم: {actual_next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"[*] سيتم الانتظار لمدة {actual_wait/60:.1f} دقيقة ({actual_wait:,.0f} ثانية)...")
            
            # الانتظار
            time.sleep(actual_wait)
            
            # الاستيقاظ والنشر
            current_time = get_user_local_time().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[*] [{current_time}] حان موعد النشر المجدول! بدء العملية...")
            try:
                run_poster()
                print(f"[+] اكتملت عملية النشر بنجاح.")
            except Exception as e:
                print(f"[-] خطأ أثناء تشغيل عملية النشر: {e}")
                
    except KeyboardInterrupt:
        print("\n[!] تم إيقاف المجدول بواسطة المستخدم. إغلاق.")
        sys.exit(0)

if __name__ == "__main__":
    start_scheduler()
