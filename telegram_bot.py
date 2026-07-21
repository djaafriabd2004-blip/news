import os
import time
import threading
import requests
import json
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# استيراد الوظائف من سكربت النشر الرئيسي
from ai_poster import generate_post_content, post_to_binance_square, enforce_length_limit, get_active_provider, set_active_provider

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# قاموس لتتبع حالات المستخدمين التفاعلية
USER_STATES = {}

# هيكل أزرار لوحة المفاتيح الملتصقة بالهاتف
KEYBOARD_MARKUP = {
    "keyboard": [
        [{"text": "📈 الفرص الصعودية"}, {"text": "📊 تحليل السوق والبيتكوين"}],
        [{"text": "🔍 تحليل عملة محددة"}, {"text": "⚡ منشور قصير (مربح)"}],
        [{"text": "🟢 عملات صاعدة"}, {"text": "🔴 عملات هابطة"}],
        [{"text": "📰 آخر الأخبار"}, {"text": "💡 نصيحة تداول"}],
        [{"text": "🎯 منشور عشوائي"}, {"text": "🤖 المزود النشط"}],
        [{"text": "🔄 تبديل (Gemini ⇄ Grok)"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

def handle_message(text, url, chat_id):
    # خريطة الأزرار النصية إلى الأوامر الداخلية
    button_mapping = {
        "📊 تحليل السوق والبيتكوين": "/post market_status",
        "🔍 تحليل عملة محددة": "/post coin_analysis_ask",
        "⚡ منشور قصير (مربح)": "/post short",
        "📈 الفرص الصعودية": "/post opportunities",
        "🟢 عملات صاعدة": "/post gainers",
        "🔴 عملات هابطة": "/post losers",
        "📰 آخر الأخبار": "/post news",
        "💡 نصيحة تداول": "/post tips",
        "🎯 منشور عشوائي": "/post random",
        "🤖 المزود النشط": "/provider",
        "🔄 تبديل (Gemini ⇄ Grok)": "/toggle_provider"
    }
    
    if text in button_mapping:
        text = button_mapping[text]

    def send_reply(msg):
        try:
            requests.post(f"{url}/sendMessage", json={
                "chat_id": chat_id,
                "text": msg,
                "reply_markup": KEYBOARD_MARKUP
            }, timeout=10)
        except Exception as e:
            print(f"[-] خطأ أثناء إرسال رد تلغرام: {e}")

    def send_reply_with_photo_if_exists(content, success, target_type):
        chart_path = os.path.join(os.path.dirname(__file__), "latest_chart.png")
        
        # إعداد نص الرسالة
        status_header = "✅ تم النشر بنجاح على Binance Square!" if success else "❌ فشل النشر على Binance Square. تأكد من صلاحية المفاتيح."
        full_message = f"{status_header}\n\n📝 **المنشور المرفوع ({target_type}):**\n{content}"
        
        if os.path.exists(chart_path):
            try:
                # إرسال الصورة مع النص كـ Caption
                with open(chart_path, "rb") as photo:
                    files = {"photo": photo}
                    data = {
                        "chat_id": chat_id,
                        "caption": full_message[:1024],
                        "reply_markup": json.dumps(KEYBOARD_MARKUP)
                    }
                    res = requests.post(f"{url}/sendPhoto", data=data, files=files, timeout=20)
                    res.raise_for_status()
                # حذف الصورة المؤقتة بعد الإرسال
                os.remove(chart_path)
                print("[+] تم إرسال الصورة والمخطط بنجاح إلى تلغرام.")
                return
            except Exception as e:
                print(f"[-] فشل إرسال الصورة إلى تلغرام ({e}). سيتم إرسال النص فقط...")
                if os.path.exists(chart_path):
                    try:
                        os.remove(chart_path)
                    except Exception:
                        pass
        
        # في حال عدم وجود صورة أو فشل إرسالها، نرسل النص كالمعتاد
        send_reply(full_message)

    # التحقق من حالة المستخدم لانتظار إدخال عملة
    if USER_STATES.get(chat_id) == "awaiting_coin_symbol":
        # إذا كتب المستخدم أمراً آخر أو زر من الكيبورد، نقوم بإلغاء الحالة ومعالجة الأمر الجديد
        if text.startswith("/") or text in button_mapping.values() or text in button_mapping.keys():
            USER_STATES[chat_id] = None
        else:
            coin_symbol = text.strip().upper().replace("#", "").replace("$", "")
            USER_STATES[chat_id] = None
            
            send_reply(f"⏳ جاري جلب منشور تحليل جاهز لـ [{coin_symbol}] ونشره...")
            
            def do_generation():
                try:
                    content = generate_post_content("coin_analysis", ticker=coin_symbol)
                    if not content:
                        send_reply("❌ فشل توليد أو جلب المنشور. تأكد من صلاحية الاتصال بالسيرفر والـ API.")
                        return
                        
                    success = post_to_binance_square(content)
                    send_reply_with_photo_if_exists(content, success, f"coin_analysis {coin_symbol}")
                except Exception as ex:
                    send_reply(f"❌ حدث خطأ غير متوقع: {ex}")
                    
            threading.Thread(target=do_generation).start()
            return

    # معالجة أوامر المساعدة
    if text.startswith("/start") or text.startswith("/help"):
        help_text = (
            "📋 **بوت التحكم بنشر Binance Square**\n\n"
            "الخيار 1: توليد ونشر تلقائي بالذكاء الاصطناعي:\n"
            "أرسل `/post <النوع>` لتوليد ونشر منشور فوراً.\n"
            "الأنواع المتاحة: `gainers`, `losers`, `alpha`, `news`, `tips`, `opportunities`, `market_status`, `coin_analysis`, `random`, `short`.\n\n"
            "الخيار 2: كتابة ونشر منشور يدوي خاص بك:\n"
            "أرسل: `/write <نص المنشور>`\n"
            "سيقوم البوت بمراجعته وقصه إذا تجاوز الطول (1000 حرف) ونشره فوراً.\n\n"
            "الخيار 3: إدارة مزود الذكاء الاصطناعي:\n"
            "- لمعرفة المزود الحالي: أرسل `/provider` أو اضغط زر '🤖 المزود النشط'\n"
            "- للتبديل بين جمناي وغروك: اضغط زر '🔄 تبديل (Gemini ⇄ Grok)'\n"
            "- لتحديد مزود معين: أرسل `/provider <gemini|grok|groq>`"
        )
        send_reply(help_text)
        return

    # معالجة أمر الاستعلام وتعديل المزود النشط
    if text.startswith("/provider"):
        parts = text.split(" ", 1)
        provider_names = {
            "gemini": "Google Gemini",
            "groq": "Groq (LPU)",
            "grok": "xAI (Grok)"
        }
        if len(parts) > 1:
            req_prov = parts[1].strip().lower()
            if req_prov in ["gemini", "groq", "grok"]:
                success = set_active_provider(req_prov)
                if success:
                    send_reply(f"🚀 تم تغيير مزود الذكاء الاصطناعي النشط إلى:\n✨ **{provider_names[req_prov]}**")
                else:
                    send_reply("❌ فشل تحديث المزود النشط.")
            else:
                send_reply(f"❌ مزود غير صالح. الخيارات المتاحة: `gemini`, `grok`, `groq`")
        else:
            current = get_active_provider()
            name = provider_names.get(current, current)
            send_reply(f"🤖 مزود الذكاء الاصطناعي النشط حالياً هو:\n✨ **{name}**")
        return

    # معالجة أمر التبديل التلقائي بين جمناي وغروك
    if text.startswith("/toggle_provider") or text.startswith("/toggle"):
        current = get_active_provider()
        next_provider = "grok" if current == "gemini" else "gemini"
        success = set_active_provider(next_provider)
        
        provider_names = {
            "gemini": "Google Gemini",
            "groq": "Groq (LPU)",
            "grok": "xAI (Grok)"
        }
        
        if success:
            new_name = provider_names.get(next_provider, next_provider)
            send_reply(f"🔄 تم تبديل المزود النشط بنجاح!\n🚀 المزود الجديد: **{new_name}**")
        else:
            send_reply("❌ فشل تحديث المزود النشط.")
        return

    # معالجة أمر النشر والتوليد التلقائي
    if text.startswith("/post"):
        parts = text.split()
        post_type = "random"
        coin_arg = None
        if len(parts) > 1:
            post_type = parts[1].strip().lower()
        if len(parts) > 2:
            coin_arg = parts[2].strip().upper()
            
        # فرز طلبات التحليل المحددة أو التلقائية
        if post_type == "coin_analysis_ask":
            USER_STATES[chat_id] = "awaiting_coin_symbol"
            send_reply("✍️ يرجى كتابة رمز العملة التي تريد فحصها ونشر تحليلها (مثال: SOL, BTC, PEPE):")
            return
            
        if post_type == "coin_analysis_random":
            post_type = "coin_analysis"
            coin_arg = None
            
        valid_types = ["gainers", "losers", "news", "tips", "alpha", "opportunities", "market_status", "coin_analysis", "random", "short"]
        if post_type not in valid_types:
            send_reply(f"❌ نوع غير صالح. الأنواع المتاحة هي:\n{', '.join(valid_types)}")
            return

        msg_verb = "جلب منشور تحليل جاهز لـ" if (post_type == "coin_analysis" and coin_arg) else "توليد منشور من نوع"
        target_name = f"[{post_type} {coin_arg}]" if coin_arg else f"[{post_type}]"
        send_reply(f"⏳ جاري {msg_verb} {target_name}...")
        
        def do_generation():
            try:
                # إذا كان عشوائياً، نقوم بالاختيار بالأوزان النسبية
                target_type = post_type
                if target_type == "random":
                    import random
                    types = ["gainers", "losers", "alpha", "news", "tips", "short"]
                    weights = [15, 15, 15, 15, 15, 25]
                    target_type = random.choices(types, weights=weights, k=1)[0]
                
                content = generate_post_content(target_type, ticker=coin_arg)
                if not content:
                    send_reply("❌ فشل توليد أو جلب المنشور. تأكد من صلاحية الاتصال بالسيرفر والـ API.")
                    return
                    
                success = post_to_binance_square(content)
                send_reply_with_photo_if_exists(content, success, target_type)
            except Exception as ex:
                send_reply(f"❌ حدث خطأ غير متوقع: {ex}")
                
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
        processed_content = enforce_length_limit(user_content, max_chars=1000)
        
        if len(user_content) > 1000:
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
            "text": "🟢 تم بدء تشغيل بوت التحكم بنشر Binance Square بنجاح!",
            "reply_markup": KEYBOARD_MARKUP
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
