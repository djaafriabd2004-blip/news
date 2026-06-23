import os
import sys
import argparse
import requests
import random
import re
import time
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
أريدك أن تكتب مثل شخص عربي حقيقي يتفاعل على تويتر، بأسلوب عفوي وبشري تماماً وغير متكلف.

يجب عليك اتباع هذه القواعد بدقة شديدة:
1. **التركيز على العملات البديلة:** ممنوع تماماً الحديث عن البيتكوين ($BTC). كل المنشورات مخصصة للعملات البديلة الساخنة (مثل $SOL, $PEPE, $TON, $WLD, $SUI, $FET, $ENA).
2. **اللهجة العامية والبعد التام عن الفصحى:** اكتب بلهجة عامية بيضاء مبسطة (مزيج بين اللهجة الخليجية والمصرية المستخدمة بكثرة في مجتمع الكريبتو العربي على تويتر: "تبهدلوا"، "طير"، "اتصفت"، "طارت"، "انتحار"، "عاند"، "كومنتات"، إلخ). ممنوع استخدام اللغة الفصحى أو الكلمات المترجمة حرفياً.
3. **ممنوع استخدام ضمير المتكلم "أنا" أو "تجربتي" أو "ستوب لوسي":** لا تتحدث بصيغة الفرد المتكلم. ممنوع كتابة "أنا أكره" أو "ستوب لوسي" أو "حسابي". تحدث بصيغة المخاطب أو الجمع أو الغائب (مثل: "حسابات"، "صفقات"، "تصفية صفقات"، "الشورترز").
4. **تجنب كليشيهات الذكاء الاصطناعي والمقدمات:** ابدأ في صلب الموضوع مباشرة بدون مقدمات ترحيبية أو كليشيهات الذكاء الاصطناعي (مثل: "في الواقع"، "علاوة على ذلك"، "يا شباب"، "في عالم الكريبتو"، "اتشوحنا"). ابدأ بالحدث أو الحركة فوراً.
5. **الطول والأسلوب:** المنشور قصير جداً (من 2 إلى 4 جمل فقط). استخدم جملاً قصيرة جداً ومباشرة.
6. **النهاية التفاعلية وعنصر الأسئلة:** أنهِ المنشور دائماً بطرح أسئلة تفاعلية للمشاهدين تحثهم على التفاعل ومشاركة آرائهم، أو صفقاتهم، أو توقعاتهم للعملات البديلة التي يودون مناقشتها أو الاستفسار عنها.
7. **الهاشتاجات وإشارة العملات:** اذكر رموز العملات البديلة مسبوقة بـ $ (مثل $SOL, $PEPE). ضع ما لا يزيد عن 2 إلى 3 هاشتاجات فقط في نهاية المنشور.
8. **تجنب الأخطاء والمصطلحات الخاطئة:**
    - استخدم مصطلحات "تصفية"، "تصفيات"، أو "ليكوديشن" للتعبير عن (Liquidations). ممنوع تماماً وبشكل قاطع استخدام كلمة "الليكود" أو "ليكود" بأي سياق.
    - اكتب كلمة "العقود الآجلة" بشكل صحيح ومنفصل دائماً، وتجنب الكلمات المركبة الخاطئة مثل "الليكود_آجلة".

أمثلة توضيحية للالتزام بنفس الأسلوب البشري العفوي:
- **مثال 1:** "الشورترز على $PEPE اليوم تبهدلوا 😂 ليكويديشن محترم طير حسابات وعاندوا مع السوق بدون فايدة. إيه توقعاتكم للحركة الجاية، مين لسه مصمم يعاند ويفتح شورت؟ #العملات_البديلة #تصفية"
- **مثال 2:** "السيولة طارت في ثواني على عملات الميمز واللونجات اتصفت بالكامل. الرافعة العالية دي انتحار. مين لسه بيلعب بالنار في $SOL و $PEPE؟ شاركونا صفقاتكم وتوقعاتكم في الكومنتات. #تصفية #عملات_الميم"
- **مثال 3:** "غريب موضوع الستوب لوز، أول ما السعر يضربه يرتد فوراً وينفجر للأعلى كأن المنصة بتراقب صفقات الناس مخصوص! بيحصل معاكم نفس الحركة دي؟ شاركونا بالكومنتات. #تداول #مخاطر"
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
    جلب الأخبار الحالية من Cointelegraph RSS مع تصفية الأخبار المنشورة سابقاً لمنع التكرار اليومي.
    """
    print("[*] جاري جلب آخر الأخبار من Cointelegraph RSS...")
    url = "https://cointelegraph.com/rss"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124"
    }
    
    # مسار ملف السجل لمنع تكرار الأخبار خلال 24 ساعة
    log_file = os.path.join(os.path.dirname(__file__), "published_news_titles.txt")
    published_titles = set()
    if os.path.exists(log_file):
        try:
            # التحقق من تاريخ تعديل الملف، إذا مر أكثر من 24 ساعة نقوم بحذفه للبدء من جديد
            if time.time() - os.path.getmtime(log_file) > 86400:
                os.remove(log_file)
            else:
                with open(log_file, "r", encoding="utf-8") as f:
                    published_titles = set(line.strip() for line in f if line.strip())
        except Exception as e:
            print(f"[-] خطأ في قراءة سجل الأخبار المنشورة: {e}")

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        news_items = []
        new_titles_to_log = []
        
        for item in root.findall(".//item"):
            title = item.find("title").text if item.find("title") is not None else ""
            desc_elem = item.find("description")
            desc_text = desc_elem.text if desc_elem is not None else ""
            desc_clean = re.sub('<[^<]+?>', '', desc_text)
            
            clean_title = title.strip()
            # تصفية الأخبار المكررة التي تم نشرها في آخر 24 ساعة
            if clean_title and clean_title not in published_titles:
                news_items.append({
                    "title": clean_title,
                    "description": desc_clean[:200]
                })
                new_titles_to_log.append(clean_title)
                if len(news_items) >= limit:
                    break
                    
        # إذا لم نجد أخباراً جديدة كافية بسبب التصفية، نأخذ أي أخبار متاحة كبديل لتجنب التوقف
        if not news_items and published_titles:
            print("[*] تم تصفية جميع الأخبار الجديدة لمنع التكرار، يتم استخدام الأخبار المتاحة كملاذ أخير...")
            for item in root.findall(".//item")[:limit]:
                title = item.find("title").text if item.find("title") is not None else ""
                desc_elem = item.find("description")
                desc_text = desc_elem.text if desc_elem is not None else ""
                desc_clean = re.sub('<[^<]+?>', '', desc_text)
                news_items.append({
                    "title": title.strip(),
                    "description": desc_clean[:200]
                })
        else:
            # تسجيل الأخبار الجديدة في الملف لمنع تكرارها لاحقاً
            if new_titles_to_log:
                try:
                    with open(log_file, "a", encoding="utf-8") as f:
                        for t in new_titles_to_log:
                            f.write(t + "\n")
                except Exception as e:
                    print(f"[-] خطأ في كتابة سجل الأخبار المنشورة: {e}")
            
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

def get_user_local_time():
    """
    حساب الوقت الحالي بتوقيت المستخدم المحلي بناءً على فرق التوقيت المختار (Offset).
    """
    from datetime import datetime, timedelta, timezone
    timezone_offset = int(os.getenv("TIMEZONE_OFFSET", 1)) # توقيت الجزائر المحلي
    utc_now = datetime.now(timezone.utc)
    return utc_now + timedelta(hours=timezone_offset)

def classify_news_topic(title):
    """
    تصنيف موضوع الخبر بناءً على الكلمات المفتاحية الموجودة في العنوان.
    """
    title_lower = title.lower()
    
    # 1. الاختراقات والتهكير والحماية (Security & Hacks)
    if any(k in title_lower for k in ["hack", "exploit", "stolen", "drain", "attack", "compromise", "phish", "scam", "theft", "اختراق", "سرقة", "تهكير", "احتيال"]):
        return "security"
        
    # 2. القوانين والتنظيمات والقضايا (Regulations, Courts & SEC)
    if any(k in title_lower for k in ["sec", "regulation", "law", "court", "sue", "complaint", "ban", "government", "binance case", "ftx case", "قانون", "محكمة", "قضية", "حظر", "حكومة"]):
        return "regulation"
        
    # 3. تبني المؤسسات والتدفقات المالية وصناديق الاستثمار (Institution, Whale & ETFs)
    if any(k in title_lower for k in ["etf", "institution", "whale", "acquire", "launch", "adopt", "fund", "etfs", "invest", "بنوك", "حوت", "حيتان", "استحواذ", "صندوق", "صناديق"]):
        return "adoption"
        
    # 4. ترقية أو تحديثات تقنية أو إطلاق شبكة (Technology & Upgrades)
    if any(k in title_lower for k in ["upgrade", "hard fork", "mainnet", "testnet", "tokenomics", "staking", "developer", "تحديث", "ترقية", "إطلاق", "شبكة"]):
        return "tech"
        
    return "general"

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
العملات دي طايرة دلوقتي وصاعدة جامد: {gainers_text}.
علق على تصفية صفقات الشورت والناس اللي خسرت عشان عاندت مع الاتجاه.
قول إن الشورترز بقوا وقود للسيولة وطاروا بالكامل. وحذرهم يدخلوا شورت تاني بدون تحليل حقيقي.
اكتب بالعامية الدارجة وبشكل تغريدة تويتر قصيرة وعفوية جداً، وممنوع استخدام "أنا".
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
العملات دي نازلة وهابطة جامد وبتنزف: {losers_text}.
علق على تصفية صفقات اللونج والناس اللي خسرت حساباتها بسبب الرافعة المالية العالية.
قول إن الحسابات اتصفت والشموع الحمراء بلعت المحافظ، وحذر الناس من شراء القاع دلوقتي أو التقاط السكين الساقط قبل ما السوق يستقر.
اكتب بالعامية الدارجة وبشكل تغريدة تويتر قصيرة وعفوية جداً، وممنوع استخدام "أنا".
"""

    elif post_type == "news":
        news_list = get_latest_news(limit=1)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية، سيتم توليد رؤية عامة للسوق كبديل...")
            prompt = """
علق على تلاعب الحيتان في سوق العملات البديلة وتسييل المحافظ للشورترز واللونغز.
اكتب بالعامية الدارجة وبشكل تغريدة تويتر قصيرة وعفوية جداً، وممنوع استخدام "أنا".
"""
        else:
            news_item = news_list[0]
            title = news_item.get("title", "")
            desc = news_item.get("description", "")
            topic = classify_news_topic(title)
            
            news_text = f"عنوان الخبر: {title}\nتفاصيل: {desc}"
            print(f"[*] تم تصنيف موضوع الخبر المختار: [{topic}]")
            
            if topic == "security":
                prompt = f"""
الخبر التالي يتعلق باختراق أو مشكلة أمنية في الكريبتو:
{news_text}

اكتب تعليقاً بلهجة عامية محلية ساخرة وجريئة على خبر الاختراق ده وأثره على السوق والعملات البديلة.
صف كيف أن ثغرات المشاريع لسه بتطير ملايين في ثواني، وحذر الناس من مشاريع الديفي التعبانة وخوفهم من تقلبات السوق المفاجئة بسبب الفود (FUD).
اكتب بشكل تغريدة تويتر قصيرة جداً وعفوية، وممنوع تماماً استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""
            elif topic == "regulation":
                prompt = f"""
الخبر التالي يتعلق بالقوانين والـ SEC أو التدخلات الحكومية:
{news_text}

اكتب تعليقاً بلهجة عامية محلية حادة وجريئة على خبر القوانين والتدخلات دي وأثره على السوق والعملات البديلة.
اتكلم عن غباء محاولات السيطرة على الكريبتو وكيف الحيتان بيستغلوا الأخبار دي لتخويف الصغار وتسييل صفقاتهم عشان يلموا القاع برخيص.
اكتب بشكل تغريدة تويتر قصيرة جداً وعفوية، وممنوع تماماً استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""
            elif topic == "adoption":
                prompt = f"""
الخبر التالي يتعلق بدخول الحيتان أو المؤسسات أو صناديق الاستثمار (ETFs):
{news_text}

اكتب تعليقاً بلهجة عامية محلية حماسية ومثيرة للجدل على خبر دخول المؤسسات والصناديق ده وأثره على صعود العملات البديلة.
وضح هل ده صعود حقيقي وتبني ضخم ولا مجرد فخ وتصريف من الحيتان لتسييل الشورترز قبل الهبوط.
اكتب بشكل تغريدة تويتر قصيرة جداً وعفوية، وممنوع تماماً استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""
            elif topic == "tech":
                prompt = f"""
الخبر التالي يتعلق بترقيات تقنية أو إطلاق شبكة أو تحديثات:
{news_text}

اكتب تعليقاً بلهجة عامية محلية ذكية ومبسطة على خبر التحديثات والترقيات التقنية للشبكات ده وأثره على حركة العملات البديلة.
ركز على هل التحديث ده هيعمل بومب وسعر العملة يطير (Pump) ولا مجرد مقولة "اشتري الإشاعة وبيع الخبر".
اكتب بشكل تغريدة تويتر قصيرة جداً وعفوية، وممنوع تماماً استخدام ضمير المتكلم "أنا" أو "تجربتي".
"""
            else: # general
                prompt = f"""
الخبر التالي هو خبر عام عن الكريبتو:
{news_text}

علق بلهجة عامية محلية وجريئة على الخبر ده وأثره على حركة صفقات الفيوتشرز وتصفية المحافظ في العملات البديلة.
قول رأيك بصراحة، هل الخبر ده مجرد تلاعب وتخويف (FUD) لتسييل الناس ولا له تأثير حقيقي؟
اكتب بشكل تغريدة تويتر قصيرة جداً وعفوية، وممنوع تماماً استخدام ضمير المتكلم "أنا" أو "تجربتي".
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
العملات دي عليها بحث واهتمام كبير دلوقتي في السوق: {alpha_text}.
علق على سبب الضجة دي وهل تستاهل الشراء ولا مجرد تصريف وتفخيم (Hype) لتصفية المتسرعين.
اكتب بالعامية الدارجة وبشكل تغريدة تويتر قصيرة وعفوية جداً، وممنوع استخدام "أنا".
"""

    elif post_type == "digest":
        local_now = get_user_local_time()
        digest_number = (local_now.hour // 4) + 1
        today_date = local_now.strftime("%d-%m-%Y")
        
        news_list = get_latest_news(limit=4)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية للموجز، سيتم توليد موجز عام للسوق...")
            news_text = "- هدوء نسبي في حركة العملات البديلة مع ترقب السيولة القادمة.\n- استقرار صفقات العقود الآجلة وتصفية المحافظ الهادئة."
        else:
            news_text = "\n".join([
                f"- {n['title']}: {n['description']}"
                for n in news_list
            ])
            
        prompt = f"""
أخبار الكريبتو المتاحة للموجز هي:
{news_text}

اكتب ملخصاً موجزاً وسريعاً جداً لأهم الأخبار بلهجة عامية محلية.
المطلب منك بدقة:
1. لخص الأخبار في 2 إلى 3 نقاط قصيرة جداً ومباشرة بدون تفاصيل مملة.
2. ممنوع استخدام الفصحى وممنوع تماماً استخدام ضمير المتكلم "أنا" أو "تجربتي".
3. يجب أن يبدأ المنشور في السطر الأول تماماً بهذه العبارة:
موجز رقم {digest_number} بتاريخ {today_date}
4. يجب أن ينتهي المنشور بهاشتاج واحد فقط وهو: #موجز_الكريبتو_اليومي
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

def main(override_type=None):
    parser = argparse.ArgumentParser(description="AI Binance Square Veteran Auto Poster")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="توليد المنشور وطباعته محلياً للمراجعة دون نشره على المنصة"
    )
    parser.add_argument(
        "--type",
        choices=["gainers", "losers", "news", "tips", "alpha", "digest", "random"],
        default="random",
        help="نوع المحتوى المراد توليده ونشره (الافتراضي: اختيار عشوائي لتنويع المنشورات)"
    )
    args = parser.parse_args()
    
    # تحديد نوع المنشور
    post_type = override_type or args.type
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
