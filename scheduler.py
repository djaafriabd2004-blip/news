import os
import time
import sys
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

# إضافة المسار الحالي للمكتبات لضمان إمكانية الاستيراد
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# استيراد دالة التشغيل الرئيسية من السكربت الأصلي
from ai_poster import main as run_poster

# تحميل متغيرات البيئة
load_dotenv()

# المدة الافتراضية الأساسية بين المنشورات (2.4 ساعة = 8640 ثانية للحصول على 10 منشورات يومياً)
INTERVAL_SECONDS = int(os.getenv("POST_INTERVAL_SECONDS", 8640))

# تفعيل التباعد العشوائي البشري (Human-like Jitter)
# يقوم بإضافة أو طرح دقائق عشوائية لجعل أوقات النشر تبدو طبيعية وغير آلية تماماً
USE_JITTER = os.getenv("USE_JITTER", "True").lower() in ("true", "1", "yes")
JITTER_MAX_SECONDS = int(os.getenv("JITTER_MAX_SECONDS", 900)) # 15 دقيقة كحد أقصى افتراضي

def start_scheduler():
    # تهيئة الترميز للغة العربية
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass

    print("="*60)
    print("  بدء تشغيل جدولة النشر التلقائي للذكاء الاصطناعي على الاستضافة")
    print(f"  الفاصل الزمني الأساسي: كل {INTERVAL_SECONDS / 3600:.2f} ساعة")
    if USE_JITTER:
        print(f"  وضع التباعد العشوائي نشط: تفاوت عشوائي يصل إلى ±{JITTER_MAX_SECONDS / 60:.1f} دقيقة لجعل النشر يبدو بشرياً.")
    print("="*60)

    try:
        while True:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\n[*] [{current_time}] بدء دورة النشر التلقائي الحالية...")
            
            try:
                # تشغيل السكربت ونشر منشور جديد
                run_poster()
                print(f"[+] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] اكتملت دورة النشر بنجاح.")
            except Exception as e:
                print(f"[-] خطأ أثناء تشغيل عملية النشر: {e}")
                
            # حساب الفاصل الزمني الفعلي للدورة القادمة بإضافة التفاوت العشوائي
            current_jitter = 0
            if USE_JITTER:
                current_jitter = random.randint(-JITTER_MAX_SECONDS, JITTER_MAX_SECONDS)
                
            actual_wait = max(60, INTERVAL_SECONDS + current_jitter) # التأكد من عدم النزول عن دقيقة واحدة
            
            # حساب موعد النشر القادم
            next_run = datetime.now() + timedelta(seconds=actual_wait)
            print(f"[*] تباعد عشوائي مطبق في هذه الدورة: {current_jitter/60:+.1f} دقيقة.")
            print(f"[*] الانتظار قيد التشغيل لمدة {actual_wait/3600:.2f} ساعة. موعد النشر القادم: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # النوم للمدة الفعالة
            time.sleep(actual_wait)
            
    except KeyboardInterrupt:
        print("\n[!] تم إيقاف المجدول بواسطة المستخدم. إغلاق.")
        sys.exit(0)

if __name__ == "__main__":
    start_scheduler()
