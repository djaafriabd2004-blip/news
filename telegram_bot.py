import os
import time
import threading
import requests
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# استيراد الوظائف من سكربت النشر الرئيسي
from ai_poster import generate_post_content, post_to_binance_square, enforce_length_limit

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def handle_message(text, url, chat_id):
    def send_reply(msg):
        try:
            requests.post(f"{url}/sendMessage", json={"chat_id": chat_id, "text": msg}, timeout=10)
        except Exception as e:
            print(f"[-] خطأ أثناء إرسال رد تلغرام: {e}")

    # معالجة أوامر المساعدة
    if text.startswith("/start") or text.startswith("/help"):
        help_text = (
            "📋 **بوت التحكم بنشر Binance Square**\n\n"
            "الخيار 1: توليد ونشر تلقائي بالذكاء الاصطناعي:\n"
            "أرسل `/post <النوع>` لتوليد ونشر منشور فوراً.\n"
            "الأنواع المتاحة: `gainers`, `losers`, `alpha`, `news`, `tips`, `opportunities`, `market_status`, `coin_analysis`, `random`.\n\n"
            "الخيار 2: كتابة ونشر منشور يدوي خاص بك:\n"
            "أرسل: `/write <نص المنشور>`\n"
            "سيقوم البوت بمراجعته وقصه إذا تجاوز الطول (400 حرف) ونشره فوراً."
        )
        send_reply(help_text)
        return

    # معالجة أمر النشر والتوليد التلقائي
    if text.startswith("/post"):
        parts = text.split(" ", 1)
        post_type = "random"
        if len(parts) > 1:
            post_type = parts[1].strip().lower()
            
        valid_types = ["gainers", "losers", "news", "tips", "alpha", "digest", "opportunities", "market_status", "coin_analysis", "random"]
        if post_type not in valid_types:
            send_reply(f"❌ نوع غير صالح. الأنواع المتاحة هي:\n{', '.join(valid_types)}")
            return
            
        send_reply(f"⏳ جاري توليد منشور من نوع [{post_type}] عبر الذكاء الاصطناعي...")
        
        def do_generation():
            try:
                # إذا كان عشوائياً، نقوم بالاختيار بالأوزان النسبية
                target_type = post_type
                if target_type == "random":
                    import random
                    types = ["gainers", "losers", "alpha", "news", "tips", "opportunities", "market_status", "coin_analysis"]
                    weights = [15, 15, 15, 15, 10, 10, 10, 10]
                    target_type = random.choices(types, weights=weights, k=1)[0]
                
                content = generate_post_content(target_type)
                if not content:
                    send_reply("❌ فشل توليد المنشور من الذكاء الاصطناعي. راجع سجلات السيرفر.")
                    return
                    
                # النشر على بينانس سكوير
                success = post_to_binance_square(content)
                if success:
                    send_reply(f"✅ تم النشر بنجاح على Binance Square!\n\n📝 **المنشور المرفوع ({target_type}):**\n{content}")
                else:
                    send_reply(f"❌ فشل النشر على Binance Square. تأكد من صلاحية المفاتيح.\n\n📝 **المحتوى المتولد:**\n{content}")
            except Exception as ex:
                send_reply(f"❌ حدث خطأ غير متوقع أثناء التوليد: {ex}")
                
        threading.Thread(target=do_generation).start()
        return

    # معالجة أمر النشر اليدوي المباشر
    if text.startswith("/write"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            send_reply("❌ يرجى كتابة نص المنشور بعد الأمر. مثال:\n`/write بيتكوين ينفجر! 🚀`")
            return
            
        user_content = parts[1].strip()
        # فحص وتقصير الطول بشكل آمن
        processed_content = enforce_length_limit(user_content, max_chars=400)
        
        if len(user_content) > 400:
            send_reply(f"⚠️ النص طويل جداً ({len(user_content)} حرف). تم تقليمه تلقائياً إلى الحد الآمن:\n\n{processed_content}")
            
        send_reply("⏳ جاري رفع ونشر المنشور اليدوي على Binance Square...")
        
        def do_manual_post():
            try:
                success = post_to_binance_square(processed_content)
                if success:
                    send_reply(f"✅ تم النشر اليدوي بنجاح على Binance Square!\n\n📝 **المنشور المنشور:**\n{processed_content}")
                else:
                    send_reply("❌ فشل النشر اليدوي على Binance Square. تأكد من صلاحية مفاتيح API الخاصة بك.")
            except Exception as ex:
                send_reply(f"❌ حدث خطأ أثناء النشر: {ex}")
                
        threading.Thread(target=do_manual_post).start()
        return

    # معالجة الرسائل العادية (غير الأوامر) لمساعدة المستخدم
    send_reply(
        "👋 أهلاً بك! لقد تلقيت رسالتك.\n"
        "لنشر هذا النص على بينانس سكوير، يرجى إرساله مسبوقاً بأمر `/write`.\n\n"
        "مثال:\n"
        f"`/write {text}`"
    )

def run_telegram_bot():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[!] تحذير: لم يتم تكوين TELEGRAM_BOT_TOKEN أو TELEGRAM_CHAT_ID. لن يعمل بوت التلغرام.")
        return

    print("="*60)
    print("  بدء تشغيل بوت التلغرام للتحكم بنشر Binance Square في الخلفية")
    print(f"  معرف الدردشة المصرح له بالتحكم: {TELEGRAM_CHAT_ID}")
    print("="*60)

    offset = 0
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    
    # إرسال رسالة ترحيبية عند تشغيل السيرفر لتأكيد الاتصال
    try:
        requests.post(f"{url}/sendMessage", json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🟢 تم بدء تشغيل بوت التحكم بنشر Binance Square بنجاح!"
        }, timeout=10)
    except Exception as e:
        print(f"[-] فشل إرسال رسالة التشغيل للتلغرام (ربما البوت غير مفعل أو التوكن خاطئ): {e}")

    while True:
        try:
            # استخدام Long Polling للاستماع الفوري للرسائل دون تحميل المعالج
            response = requests.get(f"{url}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            if response.status_code != 200:
                time.sleep(5)
                continue
                
            updates = response.json().get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message:
                    continue
                    
                chat_id = str(message["chat"]["id"])
                
                # جدار الحماية الأمني للبوت
                if chat_id != str(TELEGRAM_CHAT_ID):
                    print(f"[!] محاولة تحكم غير مصرح بها من chat_id: {chat_id}")
                    try:
                        requests.post(f"{url}/sendMessage", json={
                            "chat_id": chat_id,
                            "text": "❌ عذراً، أنت غير مصرح لك بالتحكم بنشر هذا البوت."
                        }, timeout=10)
                    except Exception:
                        pass
                    continue
                    
                text = message.get("text", "").strip()
                if not text:
                    continue
                    
                handle_message(text, url, chat_id)
                
        except Exception as e:
            print(f"[-] خطأ في حلقة استماع التلغرام: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_telegram_bot()
