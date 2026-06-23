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
أنت متداول محترف ومخضرم في أسواق العقود الآجلة (Futures) والعملات الرقمية البديلة (Altcoins)، وتكتب لمنصة Binance Square لجلب المشاهدات والتفاعل القوي.
أنت تكتب بأسلوب "المتداول اليومي الواقعي والجريء" الذي يكره الفلسفة والدروس التلقينية المملة. 

يجب عليك اتباع هذه المعايير بدقة شديدة في كتابة المنشور:
1. **التركيز على العملات البديلة:** ممنوع تماماً الحديث عن البيتكوين ($BTC). يجب أن تكون كل المنشورات والتعليقات مخصصة للعملات البديلة (Altcoins) والعملات الرقمية الساخنة (مثل $SOL, $PEPE, $TON, $WLD, $SUI, $FET, $ENA).
2. **اللهجة العامية والبعد عن الفصحى:** اكتب بلهجة عامية محلية مبسطة ومستخدمة بين متداولي الكريبتو العرب على تويتر (مثل اللهجة المصرية أو الخليجية أو الشامية البيضاء المخلوطة بمصطلحات التداول الشائعة: "يا شباب"، "السيولة راحت"، "اتشوحنا"، "تصفية شورتات"، "طيران"، "دب لتهبط"، "تعبنا"، إلخ). ممنوع استخدام اللغة الفصحى الرسمية.
3. **ممنوع استخدام ضمير المتكلم "أنا" أو "تجربتي" أو "ستوب لوسي":** ممنوع تماماً الحديث بصيغة الفرد المتكلم. لا تكتب "أنا أكره" أو "ستوب لوسي" أو "حسابي". تحدث بصيغة المخاطب أو الجمع أو الغائب (مثل: "يا متداولين"، "المحافظ اتصفت"، "الشورترز اتبخروا"، "وضع السوق"، "شكلهم ناوين").
4. **بدون تكلّف أو دروس مدرسية:** ممنوع تماماً تقديم نصائح عامة مملة مثل "حدد أهدافك مسبقاً" أو "تذكر وضع حد لخسارة". بدلاً من ذلك، تحدث بلغة الصفقات والتصفيات والخسارة والأرباح الحقيقية والرافعة المالية (Leverage).
5. **توليد الفضول والجدل (Drama & Hype):** اطرح آراء جريئة حول عملات معينة يكثر عليها التداول والأنظار حالياً في الفيوتشرز.
6. **الطول:** المنشور قصير جداً (من 2 إلى 4 جمل فقط). لا تستخدم أي نقاط تفصيلية، أو فقرات طويلة.
7. **النهاية التفاعلية وعنصر الأسئلة:** أنهِ المنشور دائماً بطرح أسئلة ذكية واستفسارات للمشاهدين تحثهم على التفاعل ومشاركة آرائهم، أو صفقاتهم الحالية، أو توقعاتهم للعملة، أو العملات البديلة التي يريدون تحليلها أو الاستفسار عنها في المنشور القادم (مثال: "شاركونا صفقاتكم وتوقعاتكم في الكومنتات!" أو "أيش العملة البديلة اللي ناويين تدخلوها اليوم؟" أو "اكتبوا لنا في التعليقات إيه العملات البديلة اللي حابين نسلط عليها الضوء المرة الجاية؟").
8. **الإيموجي:** إيموجي واحد أو اثنين كحد أقصى (مثل 🚀 أو 📉 أو 🤡 أو 🔥) وفقط إذا كانت تخدم نبرة المنشور.
9. **الهاشتاجات وإشارة العملات:**
   - اذكر رموز العملات البديلة مسبوقة بـ $ (مثل $SOL, $PEPE, $WLD).
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
            print("[*] فشل جلب الرابحين من الأسعار الحية، سيتم استخدام عملات افتراضية بديلة...")
            gainers = [
                {"symbol": "SOLUSDT", "priceChangePercentFloat": 8.5, "lastPriceFloat": 0.0},
                {"symbol": "PEPEUSDT", "priceChangePercentFloat": 12.3, "lastPriceFloat": 0.0},
                {"symbol": "WLDUSDT", "priceChangePercentFloat": 6.8, "lastPriceFloat": 0.0}
            ]
        gainers_text = ", ".join([
            f"{g['symbol'].replace('USDT', '')} (+{g['priceChangePercentFloat']:.1f}%)"
            for g in gainers
        ])
        prompt = f"""
العملات البديلة الأكثر صعوداً وانفجاراً في العقود الآجلة حالياً هي: {gainers_text}.
اكتب منشوراً نارياً ومثيراً بلهجة عامية محلية يعلق على تصفية صفقات الشورت (Short Liquidations) وتدمير الشورترز الذين حاولوا معاكسة هذا الانفجار.
صف كيف أن هؤلاء البائعين أصبحوا "وقوداً للسيولة" (Liquidity Fuel) لعمليات الصعود الحالية للعملات البديلة، وحذر المتسرعين من محاولة دخول شورت الآن دون تأكيد فني.
ممنوع استخدام الفصحى وممنوع استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""

    elif post_type == "losers":
        losers = get_trending_futures(limit=3, get_losers=True)
        if not losers:
            print("[*] فشل جلب الخاسرين من الأسعار الحية، سيتم استخدام عملات افتراضية بديلة...")
            losers = [
                {"symbol": "TONUSDT", "priceChangePercentFloat": -7.2, "lastPriceFloat": 0.0},
                {"symbol": "WLDUSDT", "priceChangePercentFloat": -9.5, "lastPriceFloat": 0.0},
                {"symbol": "PEPEUSDT", "priceChangePercentFloat": -5.4, "lastPriceFloat": 0.0}
            ]
        losers_text = ", ".join([
            f"{l['symbol'].replace('USDT', '')} ({l['priceChangePercentFloat']:.1f}%)"
            for l in losers
        ])
        prompt = f"""
العملات البديلة الأكثر هبوطاً وسقوطاً في العقود الآجلة حالياً هي: {losers_text}.
اكتب منشوراً درامياً ومثيراً بلهجة عامية محلية يعلق على تصفية صفقات الشراء واللونج (Long Liquidations) وتدمير الحالمين بالصعود في الالتكوينز.
صف كيف تلتهم الشموع الحمراء الحسابات بضرب مستويات التصفية للرافعة المالية العالية، وحذر السذج من محاولة الدخول لونج الآن (التقاط السكاكين الساقطة) قبل استقرار الشارت.
ممنوع استخدام الفصحى وممنوع استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""

    elif post_type == "news":
        news_list = get_latest_news(limit=2)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية، سيتم توليد رؤية عامة للسوق كبديل...")
            prompt = """
اكتب رؤية جريئة بلهجة عامية محلية كمتداول يتابع الشارت لعملات مثل $SOL أو $PEPE أو $TON.
تحدث عن التلاعب الحالي في السوق وكيف يقوم الحيتان بتسييل العقود الآجلة للشورترز واللونغز في العملات البديلة.
ممنوع استخدام الفصحى وممنوع استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""
        else:
            news_text = "\n".join([
                f"- {n['title']}: {n['description']}"
                for n in news_list
            ])
            prompt = f"""
علق بلهجة عامية محلية حول هذا الخبر وأثره الفعلي على سوق العملات البديلة:
{news_text}
كشف حقيقة هذا الخبر، هل هو مجرد إشاعة وتلاعب (FUD/Hype) لتسييل العقود الآجلة للعملات البديلة (مثل $SOL, $PEPE) أم له أثر حقيقي؟ اكتب بجرأة وبدون فصحى، وممنوع استخدام ضمير المتكلم "أنا".
"""

    elif post_type == "tips":
        # اختيار عشوائي لموضوع علم نفس تداول حقيقي وواقعي ومثير للتفاعل بدون ضمير المتكلم وبلهجة عامية
        tips_topics = [
            "ليه الصفقة بتنجح وتكسب لما الواحد يدخل بمبلغ صغير جداً، وتخسر وتتصفى فوراً أول ما يدخل بمبلغ كبير ورافعة عالية؟",
            "ليه بمجرد ما يضرب السعر إيقاف الخسارة (Stop Loss) يرتد فوراً وينفجر للأعلى كأن المنصة بتراقب صفقات الناس مخصوص؟",
            "مطاردة العملة بعد ما تطير 30% (FOMO) والهبوط الفوري أول ما الواحد يقرر يشتري.",
            "استخدام رافعة مالية 50x أو 100x على عملات الميمز (مثل PEPE أو SHIB) والانتظار لحد التصفية الفورية كأنها قمار."
        ]
        chosen_topic = random.choice(tips_topics)
        prompt = f"""
اكتب منشوراً جريئاً وتفاعلياً للغاية بلهجة عامية محلية حول هذا الموضوع الواقعي الذي يعاني منه متداولو الفيوتشرز:
"{chosen_topic}"
تحدث بأسلوب عامي قريب جداً من مشاعر متداولي الكريبتو العرب، واجعل المنشور يلمس الواقع مع إشارة لعملة بديلة مثل $SOL أو $PEPE.
ممنوع استخدام اللغة الفصحى تماماً، وممنوع استخدام ضمير المتكلم الفردي "أنا" أو "تجربتي" أو "ستوب لوسي". تحدث بصيغة المخاطب أو الجمع أو الغائب.
"""

    elif post_type == "alpha":
        alpha_list = get_trending_alpha(limit=4)
        if not alpha_list:
            print("[*] فشل جلب عملات الألفا من CoinGecko، سيتم استخدام عملات افتراضية بديلة...")
            alpha_list = [
                {"symbol": "SOL", "name": "Solana"},
                {"symbol": "PEPE", "name": "Pepe"},
                {"symbol": "TON", "name": "Toncoin"},
                {"symbol": "WLD", "name": "Worldcoin"}
            ]
        alpha_text = ", ".join([
            f"${a['symbol']} ({a['name']})"
            for a in alpha_list
        ])
        prompt = f"""
عملات الألفا الأكثر بحثاً واهتماماً (Trending Search) حالياً في مجتمع الكريبتو هي: {alpha_text}.
اكتب منشوراً جريئاً ونارياً بلهجة عامية محلية يعلق على سبب توجه الأنظار والبحث العنيف نحو هذه العملات البديلة بالذات.
هل تعتقد أنها فرصة ألفا حقيقية للشراء الفوري أم مجرد تضخيم وتصريف (Hype/Pump) لتصفية المتسرعين؟ اذكر عملات بديلة مثل $SOL أو $PEPE تزامناً مع التعليق.
ممنوع استخدام الفصحى وممنوع استخدام ضمير المتكلم "أنا" أو "تجربتي".
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
