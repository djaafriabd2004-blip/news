import os
import sys
import argparse
import requests
import random
import re
from dotenv import load_dotenv
from openai import OpenAI

# إعادة تهيئة الترميز لدعم الحروف العربية على نظام التشغيل Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

BINANCE_SQUARE_API_KEY = os.getenv("BINANCE_SQUARE_API_KEY")

# قراءة مفاتيح الوصول للذكاء الاصطناعي مع دعم كلاً من Groq و Grok
AI_API_KEY = os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY")
AI_MODEL = os.getenv("GROQ_MODEL") or os.getenv("GROK_MODEL") or "llama-3.3-70b-versatile"

# تحديد الرابط الأساسي تلقائياً بناءً على اسم النموذج أو مفتاح الوصول المستخدم
if "llama" in AI_MODEL.lower() or os.getenv("GROQ_API_KEY"):
    BASE_URL = "https://api.groq.com/openai/v1"
    PROVIDER_NAME = "Groq (LPU)"
else:
    BASE_URL = "https://api.x.ai/v1"
    PROVIDER_NAME = "xAI (Grok)"

VETERAN_SYSTEM_PROMPT = """
أنت متداول محترف ومخضرم في أسواق العقود الآجلة (Futures) والعملات الرقمية، وتكتب لمنصة Binance Square لجلب المشاهدات والتفاعل القوي.
أنت تكتب بأسلوب "المتداول اليومي الواقعي والجريء" الذي يكره الفلسفة والدروس التلقينية المملة. 

يجب عليك اتباع هذه المعايير بدقة شديدة في كتابة المنشور:
1. **الأسلوب واللغة:** اكتب كشخص حقيقي يتداول يومياً ويرى الشارت والسيولة أمام عينيه. استخدم جمل قصيرة جداً، مباشرة، وسريعة. كأنك تكتب تغريدة سريعة أو منشوراً جريئاً.
2. **بدون تكلّف أو دروس مدرسية:** ممنوع تماماً تقديم نصائح عامة مملة مثل "حدد أهدافك مسبقاً" أو "تذكر وضع حد لخسارة". بدلاً من ذلك، تحدث بلغة الصفقات والتصفيات والخسارة والأرباح الحقيقية والرافعة المالية (Leverage).
3. **توليد الفضول والجدل (Drama & Hype):** اطرح آراء جريئة حول عملات معينة يكثر عليها التداول والأنظار حالياً في الفيوتشرز (مثل WLD, TON, TRUMP, PEPE, SOL, BTC).
4. **الطول:** المنشور قصير جداً (من 2 إلى 4 جمل فقط). لا تستخدم أي نقاط تفصيلية، أو فقرات طويلة.
5. **اللهجة:** عربية فصحى مبسطة وعامية بيضاء خفيفة جداً يفهمها أي متداول عربي (مثل لغة متداولي تويتر وكريبتو سكوير).
6. **النهاية التفاعلية:** أنهِ المنشور دائماً بسؤال ذكي وجريء يستفز القارئ للتعليق ويفتح باب الجدال (مثال: "هل أنت مستعد لتكون وقود السيولة القادم؟" أو "من دخل شورت ومستعد للتصفية؟").
7. **الإيموجي:** إيموجي واحد أو اثنين كحد أقصى (مثل 🚀 أو 📉 أو 🤡 أو 🔥) وفقط إذا كانت تخدم نبرة المنشور.
8. **الهاشتاجات وإشارة العملات:**
   - اذكر رمز العملة مسبوقاً بـ $ أو اسم الزوج (مثل $WLD, $TON, $BTC, $PEPE).
   - ضع **ما لا يزيد عن 2 إلى 3 هاشتاجات فقط** في نهاية المنشور.
"""

def get_trending_coincap(limit=5, get_losers=False):
    """
    جلب البيانات الحية لأسعار العملات البديلة من CoinCap API
    تستخدم كبديل آمن لا يتأثر بالحظر الجغرافي لخوادم السحاب الأمريكية.
    """
    print("[*] جاري جلب الأسعار البديلة من CoinCap API...")
    url = "https://api.coincap.io/v2/assets?limit=100"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", [])
        
        formatted_assets = []
        for asset in data:
            try:
                symbol = asset.get("symbol", "") + "USDT"
                change = float(asset.get("changePercent24Hr", 0.0)) if asset.get("changePercent24Hr") else 0.0
                price = float(asset.get("priceUsd", 0.0)) if asset.get("priceUsd") else 0.0
                formatted_assets.append({
                    "symbol": symbol,
                    "priceChangePercentFloat": change,
                    "lastPriceFloat": price
                })
            except ValueError:
                continue
                
        formatted_assets.sort(key=lambda x: x["priceChangePercentFloat"], reverse=not get_losers)
        return formatted_assets[:limit]
        
    except Exception as e:
        print(f"[-] خطأ أثناء جلب البيانات من CoinCap: {e}")
        return []

def get_trending_futures(limit=5, get_losers=False):
    """
    جلب البيانات الحية لـ Binance Futures (أفضل العملات صعوداً أو هبوطاً).
    في حال كان الخادم في منطقة محظورة جغرافيًا (مثل خوادم أمريكا التي تعيد خطأ 451)، 
    يتحول السكربت تلقائيًا لاستخدام CoinCap API كبديل آمن ومتاح.
    """
    print(f"[*] جاري جلب أسعار العملات الرقمية ({'الهابطة' if get_losers else 'الصاعدة'})...")
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 451:
            print("[!] خطأ 451: خادم الاستضافة موجود في منطقة محظورة من Binance. يتم الانتقال للبديل الآمن (CoinCap)...")
            return get_trending_coincap(limit, get_losers)
            
        response.raise_for_status()
        tickers = response.json()
        
        usdt_tickers = [
            t for t in tickers 
            if t.get("symbol", "").endswith("USDT")
        ]
        
        for t in usdt_tickers:
            t["priceChangePercentFloat"] = float(t.get("priceChangePercent", 0.0))
            t["lastPriceFloat"] = float(t.get("lastPrice", 0.0))
            
        usdt_tickers.sort(key=lambda x: x["priceChangePercentFloat"], reverse=not get_losers)
        
        result = []
        for t in usdt_tickers[:limit]:
            result.append({
                "symbol": t["symbol"],
                "priceChangePercentFloat": t["priceChangePercentFloat"],
                "lastPriceFloat": t["lastPriceFloat"]
            })
        return result
        
    except Exception as e:
        print(f"[!] حدث خطأ أثناء الاتصال بـ Binance ({e}). يتم الانتقال للبديل الآمن (CoinCap)...")
        return get_trending_coincap(limit, get_losers)

def get_latest_news(limit=3):
    """
    جلب الأخبار الحالية من Cointelegraph RSS.
    """
    print("[*] جاري جلب آخر الأخبار من Cointelegraph RSS...")
    url = "https://cointelegraph.com/rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        news_items = []
        for item in root.findall(".//item")[:limit]:
            title = item.find("title").text if item.find("title") is not None else ""
            desc_elem = item.find("description")
            desc_text = desc_elem.text if desc_elem is not None else ""
            desc_clean = re.sub('<[^<]+?>', '', desc_text)
            news_items.append({
                "title": title,
                "description": desc_clean[:200]
            })
            
        return news_items
    except Exception as e:
        print(f"[-] خطأ أثناء جلب الأخبار: {e}")
        return []

def get_trending_alpha(limit=4):
    """
    جلب عملات الألفا (العملات الأكثر بحثاً ورواجاً حالياً على CoinGecko).
    وهي تمثل العملات التي تشهد اهتماماً اجتماعياً ضخماً وحركة قوية.
    """
    print("[*] جاري جلب عملات الألفا الأكثر رواجاً من CoinGecko...")
    url = "https://api.coingecko.com/api/v3/search/trending"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        coins_data = response.json().get("coins", [])
        
        alpha_coins = []
        for c in coins_data[:limit]:
            item = c.get("item", {})
            symbol = item.get("symbol", "").upper()
            name = item.get("name", "")
            alpha_coins.append({
                "symbol": symbol,
                "name": name
            })
        return alpha_coins
    except Exception as e:
        print(f"[-] خطأ أثناء جلب عملات الألفا من CoinGecko: {e}")
        return []

def generate_post_content(post_type):
    """
    توليد نص المنشور بواسطة الذكاء الاصطناعي حسب النوع المحدد.
    """
    if not AI_API_KEY:
        print("[-] خطأ: لم يتم العثور على مفتاح الوصول للذكاء الاصطناعي في ملف .env")
        sys.exit(1)
        
    print(f"[*] جاري توليد منشور من نوع [{post_type}] باستخدام {PROVIDER_NAME}...")
    
    prompt = ""
    
    if post_type == "gainers":
        gainers = get_trending_futures(limit=3, get_losers=False)
        if not gainers:
            return None
        gainers_text = ", ".join([
            f"{g['symbol'].replace('USDT', '')} (+{g['priceChangePercentFloat']:.1f}%)"
            for g in gainers
        ])
        prompt = f"""
العملات الأكثر صعوداً وانفجاراً في العقود الآجلة حالياً هي: {gainers_text}.
اكتب منشوراً نارياً ومثيراً كمتداول فيوتشرز محترف يعلق على تصفية صفقات البيع/الشورت (Short Liquidations) وتدمير الشورترز الذين حاولوا معاكسة هذا الانفجار.
صف كيف أن هؤلاء البائعين أصبحوا "وقوداً للسيولة" (Liquidity Fuel) لعمليات الصعود الحالية، وحذر المتسرعين من محاولة دخول شورت الآن دون تأكيد فني.
"""

    elif post_type == "losers":
        losers = get_trending_futures(limit=3, get_losers=True)
        if not losers:
            return None
        losers_text = ", ".join([
            f"{l['symbol'].replace('USDT', '')} ({l['priceChangePercentFloat']:.1f}%)"
            for l in losers
        ])
        prompt = f"""
العملات الأكثر هبوطاً وسقوطاً في العقود الآجلة حالياً هي: {losers_text}.
اكتب منشوراً درامياً ومثيراً كمتداول فيوتشرز محترف يعلق على تصفية صفقات الشراء واللونج (Long Liquidations) وتدمير الحالمين بالصعود.
صف كيف تلتهم الشموع الحمراء الحسابات بضرب مستويات التصفية للرافعة المالية العالية، وحذر السذج من محاولة الدخول لونج الآن (التقاط السكاكين الساقطة) قبل استقرار الشارت.
"""

    elif post_type == "news":
        news_list = get_latest_news(limit=2)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية، سيتم توليد رؤية عامة للسوق كبديل...")
            prompt = """
اكتب رؤية جريئة ومختلفة تماماً كمتداول كريبتو يتابع الشارت لـ $BTC أو $ETH أو $SOL.
تحدث عن التلاعب الحالي في السوق وكيف يقوم الحيتان بتسييل العقود الآجلة للشورترز والبلرين.
"""
        else:
            news_text = "\n".join([
                f"- {n['title']}: {n['description']}"
                for n in news_list
            ])
            prompt = f"""
علق كمتداول واقعي وجريء حول هذا الخبر وأثره الفعلي على السوق:
{news_text}
كشف حقيقة هذا الخبر، هل هو مجرد إشاعة وتلاعب (FUD/Hype) لتسييل العقود الآجلة لـ $BTC أو $ETH أم له أثر حقيقي؟ اكتب بجرأة وبدون فلسفة مملة.
"""

    elif post_type == "tips":
        # اختيار عشوائي لموضوع علم نفس تداول حقيقي وواقعي ومثير للتفاعل
        tips_topics = [
            "لماذا تنجح الصفقة عندما يكون المبلغ صغيراً وتخسر وتتصفى عندما تدخل بمبلغ كبير ورافعة عالية؟",
            "لماذا بمجرد أن يضرب السعر إيقاف الخسارة (Stop Loss) يرتد فوراً وينفجر للأعلى كأن المنصة تراقبه شخصياً؟",
            "مطاردة العملة بعد صعودها 30% (FOMO) ثم الهبوط الفوري عليك بمجرد الشراء.",
            "استخدام رافعة مالية 50x أو 100x على عملات الميمز (مثل PEPE أو TRUMP) والانتظار حتى التصفية الفورية كأنك تقامر."
        ]
        chosen_topic = random.choice(tips_topics)
        prompt = f"""
اكتب منشوراً جريئاً وتفاعلياً للغاية حول هذا الموضوع الواقعي الذي يعاني منه كل متداول فيوتشرز:
"{chosen_topic}"
تحدث بأسلوب المتداول الذي عاش هذه المعاناة، واجعل المنشور قريباً جداً من قلوب ومشاعر المتداولين مع إشارة لعملة كبرى مثل $BTC أو $SOL.
"""

    elif post_type == "alpha":
        alpha_list = get_trending_alpha(limit=4)
        if not alpha_list:
            return None
        alpha_text = ", ".join([
            f"${a['symbol']} ({a['name']})"
            for a in alpha_list
        ])
        prompt = f"""
عملات الألفا الأكثر بحثاً واهتماماً (Trending Search) حالياً في مجتمع الكريبتو هي: {alpha_text}.
اكتب منشوراً جريئاً ونارياً كمتداول فيوتشرز محترف يعلق على سبب توجه الأنظار والبحث العنيف نحو هذه العملات بالذات.
هل تعتقد أنها فرصة ألفا حقيقية للشراء الفوري أم مجرد تضخيم وتصريف (Hype/Pump) لتصفية المتسرعين؟ اذكر عملات كبرى مثل $BTC أو $SOL تزامناً مع التعليق.
"""

    try:
        client = OpenAI(api_key=AI_API_KEY, base_url=BASE_URL)
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": VETERAN_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.75
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"[-] خطأ أثناء التوليد من الذكاء الاصطناعي: {e}")
        return None

def post_to_binance_square(content):
    """
    إرسال المنشور إلى منصة Binance Square باستخدام OpenAPI.
    """
    if not BINANCE_SQUARE_API_KEY:
        print("[-] خطأ: مفتاح BINANCE_SQUARE_API_KEY غير موجود في ملف .env")
        sys.exit(1)
        
    print("[*] جاري نشر المنشور على Binance Square...")
    url = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
    
    headers = {
        "X-Square-OpenAPI-Key": BINANCE_SQUARE_API_KEY,
        "Content-Type": "application/json",
        "clienttype": "binanceSkill"
    }
    
    payload = {
        "bodyTextOnly": content
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == "000000":
            print("[+] تم النشر بنجاح على Binance Square! 🎉")
            if "data" in result:
                print(f"[+] تفاصيل الاستجابة: {result['data']}")
            return True
        else:
            print(f"[-] فشل النشر. رمز الخطأ: {result.get('code')}, الرسالة: {result.get('message')}")
            return False
            
    except Exception as e:
        print(f"[-] حدث خطأ أثناء الاتصال بـ Binance Square: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="AI Binance Square Veteran Auto Poster")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="توليد المنشور وطباعته محلياً للمراجعة دون نشره على المنصة"
    )
    parser.add_argument(
        "--type",
        choices=["gainers", "losers", "news", "tips", "alpha", "random"],
        default="random",
        help="نوع المحتوى المراد توليده ونشره (الافتراضي: اختيار عشوائي لتنويع المنشورات)"
    )
    args = parser.parse_args()
    
    # تحديد نوع المنشور
    post_type = args.type
    if post_type == "random":
        # إعطاء أولوية عظمى (80%) لمنشورات حركة وحالة العملات (gainers, losers, alpha)
        # وإعطاء 20% فقط للأخبار العامة والنصائح التفاعلية
        types = ["gainers", "losers", "alpha", "news", "tips"]
        weights = [30, 30, 20, 10, 10]
        post_type = random.choices(types, weights=weights, k=1)[0]
        print(f"[*] تم اختيار نوع المنشور عشوائياً بوزن نسبي: [{post_type}] لتنويع المحتوى.")
        
    # توليد المحتوى
    post_content = generate_post_content(post_type)
    if not post_content:
        print("[-] تعذر توليد محتوى المنشور. إيقاف العملية.")
        return
        
    # عرض المنشور المتولد
    print("\n" + "="*50)
    print(f"المنشور المتولد (النوع: {post_type}):")
    print("="*50)
    print(post_content)
    print("="*50 + "\n")
    
    # النشر أو الاكتفاء بالمعاينة
    if args.dry_run:
        print("[*] تم التشغيل في وضع المعاينة (Dry-Run). لم يتم إرسال المنشور إلى بينانس.")
    else:
        if not BINANCE_SQUARE_API_KEY:
            print("[!] تحذير: مفتاح BINANCE_SQUARE_API_KEY غير معين. يمكنك معاينة المنشور فقط.")
            return
        post_to_binance_square(post_content)

if __name__ == "__main__":
    main()
