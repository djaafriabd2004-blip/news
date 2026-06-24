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

# قراءة مفاتيح الوصول لجميع مزودي الخدمة
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

XAI_API_KEY = os.getenv("XAI_API_KEY")
GROK_MODEL = os.getenv("GROK_MODEL", "grok-2-latest")

# تفعيل التخزين المحلي للمزود النشط
def get_active_provider():
    provider_file = os.path.join(os.path.dirname(__file__), "active_provider.txt")
    if os.path.exists(provider_file):
        try:
            with open(provider_file, "r", encoding="utf-8") as f:
                prov = f.read().strip().lower()
                if prov in ["gemini", "groq", "grok"]:
                    return prov
        except Exception:
            pass
    return os.getenv("ACTIVE_PROVIDER", "gemini").lower()

def set_active_provider(provider):
    provider = provider.lower()
    if provider not in ["gemini", "groq", "grok"]:
        return False
    provider_file = os.path.join(os.path.dirname(__file__), "active_provider.txt")
    try:
        with open(provider_file, "w", encoding="utf-8") as f:
            f.write(provider)
        return True
    except Exception:
        return False

ACTIVE_PROVIDER = get_active_provider()

# قاموس البرومبات (قوالب التوجيه) لكل نوع منشورات لسهولة التعديل والتخصيص
PROMPTS_CONFIG = {
    "gainers": """
العملات التالية حققت ارتفاعات سعرية حية مع قراءة التحليل الفني من الـ API:
{gainers_text}

اكتب منشوراً تحليلياً بأسلوب رسمي وموضوعي وجاد جداً يعرض حالة العملات الصاعدة مع تحليلها الفني.
توجيه هام: بالنسبة لهذا المنشور، تجاهل شخصية 'أبو الرافعة' واللغة العامية تماماً، واكتب كأخصائي تحليل فني رسمي محترف بأسلوب عربي فصيح رصين.
الشروط:
- تجنب تماماً الكلمات العامية، المبالغات، العاطفية، أو أي عبارات شعبية/غير رسمية.
- تحدث بموضوعية عن وضعها الفني ولا تقدم توصيات شراء مباشرة بل قدم قراءة فنية.
- سطرين كحد أقصى.
- سؤال تفاعلي هادئ في النهاية حول توقعات المتابعين الفنية.
""",

    "losers": """
العملات التالية شهدت انخفاضات سعرية حية مع قراءة التحليل الفني من الـ API:
{losers_text}

اكتب منشوراً تحليلياً بأسلوب رسمي وموضوعي وجاد جداً يعرض حالة العملات الهابطة مع تحليلها الفني.
توجيه هام: بالنسبة لهذا المنشور، تجاهل شخصية 'أبو الرافعة' واللغة العامية تماماً، واكتب كأخصائي تحليل فني رسمي محترف بأسلوب عربي فصيح رصين.
الشروط:
- تجنب تماماً الكلمات العامية، المبالغات، العاطفية، أو أي عبارات شعبية/غير رسمية.
- تحدث بموضوعية عن وضعها الفني ولا تقدم توصيات بيع مباشرة بل قدم قراءة فنية.
- سطرين كحد أقصى.
- سؤال تفاعلي هادئ في النهاية حول توقعات المتابعين الفنية.
""",

    "news_security": """
الخبر: {news_text}
اكتب تغريدة تعرض خبر الاختراق/الحماية كما هو بشكل مباشر وموضوعي وموجز.
الشروط:
- ممنوع تماماً استخدام عبارات مثل "والله" أو "بصراحة" أو أي صيغ حلفان أو نبرة شخصية مبالغة.
- سطرين كحد أقصى.
- سؤال تفاعلي في النهاية حول الخبر.
""",

    "news_regulation": """
الخبر: {news_text}
اكتب تغريدة تعرض خبر القوانين/التنظيمات كما هو بشكل مباشر وموضوعي وموجز.
الشروط:
- ممنوع تماماً استخدام عبارات مثل "والله" أو "بصراحة" أو أي صيغ حلفان أو نبرة شخصية مبالغة.
- سطرين كحد أقصى.
- سؤال تفاعلي في النهاية حول الخبر.
""",

    "news_adoption": """
الخبر: {news_text}
اكتب تغريدة تعرض خبر التبني/دخول المؤسسات كما هو بشكل مباشر وموضوعي وموجز.
الشروط:
- ممنوع تماماً استخدام عبارات مثل "والله" أو "بصراحة" أو أي صيغ حلفان أو نبرة شخصية مبالغة.
- سطرين كحد أقصى.
- سؤال تفاعلي في النهاية حول الخبر.
""",

    "news_tech": """
الخبر: {news_text}
اكتب تغريدة تعرض خبر التحديث التقني كما هو بشكل مباشر وموضوعي وموجز.
الشروط:
- ممنوع تماماً استخدام عبارات مثل "والله" أو "بصراحة" أو أي صيغ حلفان أو نبرة شخصية مبالغة.
- سطرين كحد أقصى.
- سؤال تفاعلي في النهاية حول الخبر.
""",

    "news_general": """
الخبر: {news_text}
اكتب تغريدة تعرض الخبر العام كما هو بشكل مباشر وموضوعي وموجز.
الشروط:
- ممنوع تماماً استخدام عبارات مثل "والله" أو "بصراحة" أو أي صيغ حلفان أو نبرة شخصية مبالغة.
- سطرين كحد أقصى.
- سؤال تفاعلي في النهاية حول الخبر.
""",

    "tips": """
الموضوع: "{chosen_topic}"
العملة المرجعية: {chosen_coin}

اكتب تغريدة بأسلوب "أبو الرافعة" — كلام من تجربة مؤلمة حقيقية، مو محاضرة ومو نصيحة جاهزة.
الشروط:
- اجعل الكلام يلمس الواقع ويخلي المتداول يحس إن أحد يفهمه فعلاً.
- اعترف إنك وقعت في نفس الخطأ قبل كذا.
- سطرين كحد أقصى، سؤال تفاعلي في النهاية.
""",

    "alpha": """
العملات دي عليها ضجة واهتمام كبير: {alpha_text}.
اكتب تغريدة بأسلوب "أبو الرافعة" — تساؤل صريح: الضجة دي حقيقية ولا مجرد هايب وتصريف للمتسرعين?
الشروط:
- رأي جريء مع تحذير خفيف للي بيدخل متأخر.
- سطرين كحد أقصى، سؤال تفاعلي في النهاية.
""",

    "digest": """
الأخبار المتاحة:
{news_text}

اكتب موجزاً إخبارياً يعرض الأخبار كما هي بشكل مباشر وموضوعي وموجز (بدون استخدام كلمات مثل "والله" أو "بصراحة" أو أي ألفاظ قسم أو نبرة شخصية).
يجب أن يبدأ السطر الأول تماماً بـ:
موجز رقم {digest_number} بتاريخ {today_date}
وينتهي بهاشتاج واحد فقط: #موجز_الكريبتو_اليومي
""",

    "opportunities": """
العملات التالية تظهر بها احتمالية صعود كبيرة بناءً على المؤشرات الفنية:
{opportunities_text}

اكتب تغريدة بأسلوب "أبو الرافعة" يتحدث فيها عن احتمالية الصعود القوية لهذه العملات بناءً على وضعها الفني الحالي.
الشروط:
- لا تذكر أبداً أن هناك "بوت" أو "برنامج" أو "نظام تلقائي" يرشحها أو يوصي بها.
- تحدث عنها كفرص فنية ذات احتمالية صعود جيدة في السوق.
- نبه المتداولين كالمعتاد لضرورة عدم التسرع بالرافعة المالية والالتزام بوقف الخسارة.
- سطرين كحد أقصى.
- سؤال تفاعلي في النهاية.
""",

    "market_status": """
حالة سوق البيتكوين والمؤشرات الحالية:
سعر البيتكوين: ${btc_price} ({btc_change}%)
حالة جدار حماية البوت: {defense_state}
مؤشر RSI: {rsi}
مؤشر ADX: {adx}
مؤشر MACD: {macd}

اكتب تغريدة بأسلوب "أبو الرافعة" — يعلق فيها على المؤشرات دي بنظرة شك صحي وجريء، وحالة السوق الحالية للعملات البديلة وإذا كان هذا وقت مناسب للمخاطرة بالرافعة المالية أم يفضل الجلوس على المدرجات.
الشروط:
- سطرين كحد أقصى، سؤال تفاعلي في النهاية.
""",

    "coin_analysis": """
نتائج التحليل الفني والاتجاه لعملة {ticker}:
القرار: {decision}
نسبة احتمالية الحركة: {confidence}%
المؤشرات الفنية بالتفصيل: {indicators_text}

اكتب منشوراً تحليلياً بأسلوب رسمي وموضوعي وجاد جداً يعرض حالة هذه العملة مع تحليل مؤشراتها الفنية.
توجيه هام: بالنسبة لهذا المنشور، تجاهل شخصية 'أبو الرافعة' واللغة العامية تماماً، واكتب كأخصائي تحليل فني رسمي محترف بأسلوب عربي فصيح رصين.
الشروط:
- لا تذكر كلمة "بوت" أو "برنامج" أو "نظام تلقائي".
- ممنوع منعاً باتاً استخدام كلمة "والله" أو أي صيغ حلفان أو قسم.
- تجنب تماماً الكلمات العامية، المبالغات، أو التعبيرات غير الرسمية.
- اشرح باختصار شديد وبطريقة فنية موضوعية سبب الاتجاه الحالي بناءً على قراءات المؤشرات (مثل RSI وMACD).
- سطرين كحد أقصى (لا يتجاوز 280 حرف).
- سؤال تفاعلي هادئ في النهاية حول توقعات المتابعين الفنية.
"""
}

VETERAN_SYSTEM_PROMPT = """
أنت "أبو الرافعة" — متداول عربي حقيقي في العقود الآجلة والعملات البديلة، عندك سنوات في السوق، شفت خسائر موجعة وكمان ربحت صفقات حلوة. مو بوت ولا كاتب محتوى، أنت واحد من الناس يشارك اللي يشوفه في السوق بصدق وبدون تصنع.

## شخصيتك الحقيقية:
- خسرت صفقات كثير في البداية وتعلمت بالطريقة الصعبة، هذا خلاك تفهم ألم الناس
- أحياناً تغلط في توقعاتك وما تخجل تعترف، لأن السوق ما يرحم حتى الخبراء
- تحس بالشماتة الخفيفة لما الشورترز يتصفون، لأنك كنت زيهم قبل كذا
- تحذر الناس لأنك شفت كم حساب طار بسببك أنت نفسك في البداية
- أحياناً تكون متفائل، وأحياناً تحس إن السوق مو وقته

## قواعد الكتابة:
1. **اللهجة:** عامية بيضاء مزيج خليجي-مصري طبيعي. كلمات زي: "تبهدلوا"، "طار"، "اتصفت"، "طارت"، "انتحار"، "عاند"، "ما شفتوا شي"، "الله يعين"
2. **الأسلوب الإنساني المتنوع:** ابدأ بأساليب مختلفة وجمل متنوعة لتجعل الكلام يبدو طبيعياً وبشرياً وليس كبوت مكرر. لا تلتزم بكلمة أو بداية معينة في كل المنشورات واجعل الأسلوب مرناً وتلقائياً.
3. **القسم والأيمان (مهم جداً):** ممنوع منعاً باتاً وقاطعاً استخدام كلمة "والله" أو أي حلفان أو قسم في أي منشور تحت أي ظرف كان.
4. **الطول:** سطرين أو ثلاثة كحد أقصى — مو أكثر
5. **ممنوع:** "أنا"، "تجربتي"، "ستوب لوسي"، أي كلام فصيح، مقدمات ترحيبية
6. **البيتكوين:** ممنوع تذكره، الكلام كله عن الألتكوينز فقط
7. **العملات:** اذكرها بـ$ وما تكرر نفس العملة في منشورات متتالية
8. **الهاشتاجات:** 2 إلى 3 فقط في النهاية
9. **المصطلحات:** "تصفية" أو "تصفيات" أو "ليكويديشن" — ممنوع "ليكود"
10. **النهاية:** اطرح سؤال تفاعلي واحد يخلي الناس يردون

## النبرة المطلوبة حسب السياق:
- **صعود قوي:** شماتة خفيفة + تحذير من الشورترز الجدد اللي ما تعلموا
- **هبوط حاد:** تفهم حقيقي لألم اللونجات + تحذير من "الارتداد الوهمي"
- **أخبار:** رأي جريء مع شك صحي — "هل هذا حقيقي ولا تصريف؟"
- **نصائح:** كلام من تجربة مؤلمة، مو محاضرة

## أمثلة على الأسلوب المطلوب (بدايات متنوعة):
- "الشورترز على $PEPE اليوم تبهدلوا ع الآخر 😅 السوق طار بيهم وهم لسه معاندين. مين منكم لسه مصمم يفتح شورت؟"
- "اللونجات على $SOL اتصفت بشكل موجع الليلة. الرافعة العالية دي انتحار حقيقي. الله يعين اللي ما وضع ستوب، شاركونا وين دخلتوا؟"  
- "خبر الـ ETF ده ما أدري أصدقه ولا لأ، الحيتان شاطرين يلبسونها للمتداولين وهم بيصرفون. إيه رأيكم؟"
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

def get_trending_bybit(limit=5, get_losers=False):
    """
    جلب البيانات الحية لأسعار العملات البديلة من Bybit Spot API كبديل قوي ومقاوم للقيود الجغرافية.
    """
    print("[*] جاري جلب الأسعار البديلة من Bybit Spot API...")
    url = "https://api.bybit.com/v5/market/tickers?category=spot"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        ticker_list = data.get("result", {}).get("list", [])
        
        formatted_assets = []
        for item in ticker_list:
            symbol = item.get("symbol", "")
            # تصفية أزواج USDT فقط واستبعاد البيتكوين
            if symbol.endswith("USDT") and not symbol.startswith("BTC"):
                try:
                    change_ratio = float(item.get("price24hPcnt", 0.0))
                    change_pct = change_ratio * 100.0
                    price = float(item.get("lastPrice", 0.0))
                    formatted_assets.append({
                        "symbol": symbol,
                        "priceChangePercentFloat": change_pct,
                        "lastPriceFloat": price
                    })
                except ValueError:
                    continue
                    
        formatted_assets.sort(key=lambda x: x["priceChangePercentFloat"], reverse=not get_losers)
        return formatted_assets[:limit]
    except Exception as e:
        print(f"[-] خطأ أثناء جلب البيانات من Bybit: {e}")
        return []

def get_trending_mexc(limit=5, get_losers=False):
    """
    جلب البيانات الحية لأسعار العملات البديلة من MEXC Spot API كبديل احتياطي ذو نسبة إتاحة عالية جداً.
    """
    print("[*] جاري جلب الأسعار البديلة من MEXC Spot API...")
    url = "https://api.mexc.com/api/v3/ticker/24hr"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        ticker_list = response.json()
        
        formatted_assets = []
        for item in ticker_list:
            symbol = item.get("symbol", "")
            if symbol.endswith("USDT") and not symbol.startswith("BTC"):
                try:
                    change_ratio = float(item.get("priceChangePercent", 0.0))
                    change_pct = change_ratio * 100.0
                    price = float(item.get("lastPrice", 0.0))
                    formatted_assets.append({
                        "symbol": symbol,
                        "priceChangePercentFloat": change_pct,
                        "lastPriceFloat": price
                    })
                except ValueError:
                    continue
                    
        formatted_assets.sort(key=lambda x: x["priceChangePercentFloat"], reverse=not get_losers)
        return formatted_assets[:limit]
    except Exception as e:
        print(f"[-] خطأ أثناء جلب البيانات من MEXC: {e}")
        return []

def get_trending_futures(limit=5, get_losers=False):
    """
    جلب البيانات الحية لـ Binance Futures (أفضل العملات صعوداً أو هبوطاً).
    في حال كان الخادم في منطقة محظورة جغرافيًا (مثل خوادم أمريكا التي تعيد خطأ 451)، 
    يتحول السكربت تلقائيًا لسلسلة من البدائل الآمنة (Bybit -> MEXC -> CoinCap).
    """
    print(f"[*] جاري جلب أسعار العملات الرقمية ({'الهابطة' if get_losers else 'الصاعدة'})...")
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 451:
            print("[!] خطأ 451: خادم الاستضافة موجود في منطقة محظورة من Binance. يتم الانتقال للبدائل الآمنة...")
            # محاولة Bybit
            bybit_data = get_trending_bybit(limit, get_losers)
            if bybit_data:
                return bybit_data
            # محاولة MEXC
            mexc_data = get_trending_mexc(limit, get_losers)
            if mexc_data:
                return mexc_data
            # محاولة CoinCap
            return get_trending_coincap(limit, get_losers)
            
        response.raise_for_status()
        tickers = response.json()
        
        usdt_tickers = [
            t for t in tickers 
            if t.get("symbol", "").endswith("USDT") and not t.get("symbol", "").startswith("BTC")
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
        print(f"[!] حدث خطأ أثناء الاتصال بـ Binance ({e}). يتم الانتقال للبدائل الآمنة...")
        # محاولة Bybit
        bybit_data = get_trending_bybit(limit, get_losers)
        if bybit_data:
            return bybit_data
        # محاولة MEXC
        mexc_data = get_trending_mexc(limit, get_losers)
        if mexc_data:
            return mexc_data
        # محاولة CoinCap
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
    في حال الفشل، نستخدم كبديل العملات الأكثر تداولاً من حيث حجم التداول (Volume) على Bybit Spot.
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
        if alpha_coins:
            return alpha_coins
    except Exception as e:
        print(f"[-] خطأ أثناء جلب عملات الألفا من CoinGecko ({e}). يتم الانتقال للبديل الآمن (Bybit Volumes)...")
        
    # البديل: جلب العملات الأعلى حجماً من Bybit
    print("[*] جاري جلب العملات الأكثر نشاطاً وحجماً من Bybit...")
    bybit_url = "https://api.bybit.com/v5/market/tickers?category=spot"
    try:
        response = requests.get(bybit_url, timeout=10)
        response.raise_for_status()
        ticker_list = response.json().get("result", {}).get("list", [])
        
        volume_assets = []
        for item in ticker_list:
            symbol = item.get("symbol", "")
            if symbol.endswith("USDT") and not symbol.startswith("BTC") and not symbol.startswith("USDC"):
                try:
                    turnover = float(item.get("turnover24h", 0.0))
                    clean_symbol = symbol.replace("USDT", "")
                    volume_assets.append({
                        "symbol": clean_symbol,
                        "name": clean_symbol,
                        "turnover": turnover
                    })
                except ValueError:
                    continue
        # ترتيب حسب الحجم التداولي الأكبر تنازلياً
        volume_assets.sort(key=lambda x: x["turnover"], reverse=True)
        return volume_assets[:limit]
    except Exception as ex:
        print(f"[-] خطأ أثناء جلب العملات الأكثر نشاطاً من Bybit: {ex}")
        return []

def format_ticker_for_scan(symbol):
    """
    تحويل صيغة اسم العملة إلى الصيغة المقبولة في API التحليل (مثلاً SOLUSDT -> SOL-USD)
    """
    if not symbol:
        return ""
    clean = symbol.replace("-USDT", "").replace("-USD", "").replace("USDT", "").replace("USDC", "").strip()
    return f"{clean}-USD"

import base64

def save_base64_chart(chart_b64):
    """
    تحويل الصورة المشفرة بترميز Base64 وحفظها كملف مؤقت latest_chart.png.
    """
    if not chart_b64:
        return False
    try:
        # إزالة البادئة إذا وجدت (مثل data:image/png;base64,)
        if "," in chart_b64:
            chart_b64 = chart_b64.split(",", 1)[1]
        
        img_data = base64.b64decode(chart_b64)
        chart_file = os.path.join(os.path.dirname(__file__), "latest_chart.png")
        with open(chart_file, "wb") as f:
            f.write(img_data)
        print(f"[+] تم حفظ صورة المخطط البياني بنجاح في {chart_file}")
        return True
    except Exception as e:
        print(f"[-] فشل فك تشفير وحفظ صورة المخطط البياني: {e}")
        return False

def scan_coin(ticker, timeframe="1d"):
    """
    إجراء تحليل فني فوري وشامل لعملة محددة من خلال واجهة البوت مع كتابة سجلات تفصيلية للتشخيص.
    """
    formatted_ticker = format_ticker_for_scan(ticker)
    print(f"[*] جاري فحص وتحليل العملة {formatted_ticker} عبر API...")
    url = f"{TRADING_BOT_URL}/api/scan_coin"
    params = {
        "ticker": formatted_ticker,
        "timeframe": timeframe
    }
    
    log_file = os.path.join(os.path.dirname(__file__), "api_debug.log")
    
    try:
        response = requests.get(url, params=params, timeout=10)
        # تسجيل المحاولة الناجحة في ملف اللوغ
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS: Called {url} with params {params}. Status Code: {response.status_code}\n")
        response.raise_for_status()
        data = response.json()
        
        # حفظ المخطط البياني إذا وجد بترميز Base64
        if isinstance(data, dict) and data.get("chart_image"):
            save_base64_chart(data["chart_image"])
            
        return data
    except Exception as e:
        # تسجيل الخطأ بالتفصيل في ملف اللوغ
        err_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed calling {url} with params {params}. Exception: {e}\n"
        if 'response' in locals() and response is not None:
            err_msg += f"Status Code: {response.status_code} | Response: {response.text}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(err_msg + "-"*50 + "\n")
        except Exception:
            pass
            
        print(f"[-] فشل الاتصال بواجهة فحص العملة ({e}). سيتم استخدام بيانات تحليل نموذجية...")
        return {
            "ticker": formatted_ticker,
            "decision": random.choice(["BUY", "SELL", "HOLD"]),
            "confidence": random.randint(70, 95),
            "indicators": {
                "rsi": random.randint(30, 70),
                "macd": random.choice(["Bullish Crossover", "Bearish Crossover", "Neutral"]),
                "adx": random.randint(15, 35)
            }
        }

def prune_hashtags(content, max_hashtags=3):
    """
    التحقق من عدد الهاشتاجات في النص وتقليصها إلى الحد المسموح به من بايننس سكوير (بحد أقصى 3) لمنع الخطأ 220094.
    """
    if not content:
        return content
        
    # البحث عن الهاشتاجات باستخدام التعبير النمطي
    hashtags = re.findall(r'#[\w_]+', content)
    
    if len(hashtags) <= max_hashtags:
        return content
        
    print(f"[!] تحذير: عدد الهاشتاجات ({len(hashtags)}) يتجاوز الحد المسموح به ({max_hashtags}). جاري تقليصها إلى {max_hashtags}...")
    
    # الهاشتاجات الإضافية التي سيتم حذفها
    extra_hashtags = hashtags[max_hashtags:]
    
    # حذف الهاشتاجات الزائدة من النص
    for ht in extra_hashtags:
        content = content.replace(ht, "").strip()
        
    # إزالة الفراغات المكررة
    content = re.sub(r' +', ' ', content)
    return content

def enforce_length_limit(content, max_chars=400):
    """
    التأكد من أن المنشور لا يتجاوز الحد الأقصى للحروف على بايننس سكوير.
    يتم قطع النص بشكل ذكي عند آخر علامة ترقيم أو فراغ لمنع تشويه الكلمات.
    """
    if not content:
        return content
        
    content = content.strip()
    if len(content) <= max_chars:
        return content
        
    print(f"[!] تحذير: النص المتولد طويل جداً ({len(content)} حرف). جاري تقليصه تلقائياً إلى {max_chars} حرف...")
    
    # محاولة القص عند نهاية جملة مفيدة
    truncated = content[:max_chars - 10]
    
    # البحث عن آخر نقطة أو علامة استفهام أو سطر جديد
    last_stop = -1
    for char in ['.', '!', '؟', '\n']:
        idx = truncated.rfind(char)
        if idx > last_stop:
            last_stop = idx
            
    # إذا تم العثور على علامة نهاية جملة على مسافة معقولة (لا تقل عن 70% من الحد الأقصى)
    if last_stop > int(max_chars * 0.7):
        return content[:last_stop + 1].strip() + " #العملات_الرقمية"
        
    # إذا لم نعثر على جملة كاملة قريبة، نقطع عند آخر فراغ لمنع تشويه الكلمة
    last_space = truncated.rfind(' ')
    if last_space > int(max_chars * 0.5):
        return content[:last_space].strip() + "... #العملات_الرقمية"
        
    return truncated.strip() + "... #العملات_الرقمية"

TRADING_BOT_URL = os.getenv("TRADING_BOT_URL", "https://worker-production-d1ab.up.railway.app")

def get_bot_status():
    """
    جلب حالة بوت التداول والصفقات النشطة من واجهة الـ API الخاصة به.
    """
    print("[*] جاري جلب حالة صفقات بوت التداول...")
    url = f"{TRADING_BOT_URL}/api/status"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[-] فشل الاتصال بواجهة حالة البوت ({e}). سيتم استخدام بيانات نموذجية...")
        return {
            "active_trades": [
                {"ticker": "SOL-USDT", "entry_price": 142.50, "unrealized_pnl": 5.4},
                {"ticker": "PEPE-USDT", "entry_price": 0.000012, "unrealized_pnl": -1.2},
                {"ticker": "SUI-USDT", "entry_price": 0.88, "unrealized_pnl": 12.3}
            ],
            "win_rate": 78.5,
            "total_trades": 142
        }

def get_bullish_opportunities():
    """
    جلب الفرص الصعودية المكتشفة حالياً من بوت التداول.
    """
    print("[*] جاري جلب الفرص الصعودية من البوت...")
    url = f"{TRADING_BOT_URL}/api/bullish_opportunities"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[-] فشل الاتصال بواجهة الفرص الصعودية ({e}). سيتم استخدام بيانات نموذجية...")
        return [
            {"ticker": "NEAR-USDT", "entry_price": 4.25, "targets": [4.60, 4.90], "stop_loss": 3.90, "confidence": 88},
            {"ticker": "RENDER-USDT", "entry_price": 7.80, "targets": [8.40, 9.00], "stop_loss": 7.30, "confidence": 82},
            {"ticker": "TON-USDT", "entry_price": 7.10, "targets": [7.60, 8.10], "stop_loss": 6.80, "confidence": 91}
        ]

def get_explosion_opportunity_post():
    """
    جلب المنشورات الجاهزة لفرص الانفجار من البوت واختيار منشور عشوائي.
    """
    print("[*] جاري جلب فرص الانفجار والمنشورات الجاهزة...")
    url = f"{TRADING_BOT_URL}/api/explosion_opportunities"
    log_file = os.path.join(os.path.dirname(__file__), "api_debug.log")
    try:
        response = requests.get(url, timeout=10)
        # تسجيل المحاولة الناجحة في ملف اللوغ
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS: Called {url}. Status Code: {response.status_code}\n")
        response.raise_for_status()
        data = response.json()
        
        # التعامل مع الاحتمالات المختلفة للاستجابة (قائمة أو كائن يحتوي على قائمة)
        coins_list = []
        if isinstance(data, list):
            coins_list = data
        elif isinstance(data, dict):
            # محاولة البحث عن أي حقل يحتوي على قائمة
            for val in data.values():
                if isinstance(val, list):
                    coins_list = val
                    break
        
        valid_items = []
        for item in coins_list:
            if isinstance(item, dict) and item.get("binance_post"):
                valid_items.append(item)
                
        if valid_items:
            # نختار أحد العناصر عشوائياً
            selected_item = random.choice(valid_items)
            print(f"[+] تم العثور على {len(valid_items)} فرص انفجار جاهزة. تم اختيار واحدة عشوائياً.")
            
            # حفظ المخطط البياني المرفق إن وجد
            if selected_item.get("chart_image"):
                save_base64_chart(selected_item["chart_image"])
                
            return selected_item["binance_post"].strip()
            
        print("[-] لم يتم العثور على أي منشور جاهز (binance_post) في استجابة فرص الانفجار.")
        return None
    except Exception as e:
        # تسجيل الخطأ بالتفصيل في ملف اللوغ
        err_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed calling {url}. Exception: {e}\n"
        if 'response' in locals() and response is not None:
            err_msg += f"Status Code: {response.status_code} | Response: {response.text}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(err_msg + "-"*50 + "\n")
        except Exception:
            pass
            
        print(f"[-] فشل جلب منشورات فرص الانفجار من الـ API ({e}).")
        return None

def get_btc_market_status():
    """
    جلب حالة السوق والبيتكوين والمؤشرات الفنية من البوت.
    """
    print("[*] جاري جلب حالة سوق البيتكوين والمؤشرات...")
    url = f"{TRADING_BOT_URL}/api/btc_market_status"
    log_file = os.path.join(os.path.dirname(__file__), "api_debug.log")
    try:
        response = requests.get(url, timeout=10)
        # تسجيل المحاولة الناجحة في ملف اللوغ
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SUCCESS: Called {url}. Status Code: {response.status_code}\n")
        response.raise_for_status()
        data = response.json()
        
        # حفظ المخطط البياني للبيتكوين إذا وجد بترميز Base64
        if isinstance(data, dict) and data.get("chart_image"):
            save_base64_chart(data["chart_image"])
            
        return data
    except Exception as e:
        # تسجيل الخطأ بالتفصيل في ملف اللوغ
        err_msg = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Failed calling {url}. Exception: {e}\n"
        if 'response' in locals() and response is not None:
            err_msg += f"Status Code: {response.status_code} | Response: {response.text}\n"
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(err_msg + "-"*50 + "\n")
        except Exception:
            pass
            
        print(f"[-] فشل الاتصال بواجهة مؤشرات البيتكوين ({e}). سيتم استخدام بيانات نموذجية...")
        return {
            "btc_price": 64850,
            "price_change_24h": -1.45,
            "downtrend_defense": True,
            "rsi": 42.5,
            "macd": "Bearish crossover",
            "adx": 22.1,
            "ema200": 63900
        }

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

def generate_post_content(post_type, provider=None, ticker=None):
    """
    توليد نص المنشور بواسطة الذكاء الاصطناعي حسب النوع المحدد مع دعم التبديل بين المزودين والتراجع التلقائي.
    """
    # تحديد المزود المختار (الممرر أو النشط حالياً)
    selected_provider = provider or get_active_provider()
    if selected_provider not in ["gemini", "groq", "grok"]:
        selected_provider = "gemini"
        
    print(f"[*] جاري توليد منشور من نوع [{post_type}] مع تحديد المزود الافتراضي: [{selected_provider}]...")
    
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
        
        gainers_items = []
        for g in gainers[:3]:
            sym = g["symbol"].replace("-USDT", "").replace("-USD", "").replace("USDT", "").replace("USDC", "").strip()
            # جلب التحليل الفني من الـ API
            analysis = scan_coin(sym)
            
            decision = "HOLD"
            confidence = 50
            rsi = 50
            if isinstance(analysis, dict):
                decision = analysis.get("decision") or analysis.get("decision_type") or "HOLD"
                confidence = analysis.get("confidence") or analysis.get("confidence_score") or 50
                rsi = analysis.get("rsi")
                if "indicators" in analysis and isinstance(analysis["indicators"], dict):
                    rsi = rsi or analysis["indicators"].get("rsi")
                if rsi is None:
                    rsi = 50
                    
            gainers_items.append(
                f"- ${sym} (+{g['priceChangePercentFloat']:.1f}% | التحليل الفني: {decision} ثقة {confidence}% | RSI: {rsi})"
            )
        gainers_text = "\n".join(gainers_items)
        prompt = PROMPTS_CONFIG["gainers"].format(gainers_text=gainers_text)

    elif post_type == "losers":
        losers = get_trending_futures(limit=3, get_losers=True)
        if not losers:
            print("[*] فشل جلب الخاسرين من الأسعار الحية، سيتم استخدام عملات افتراضية بديلة...")
            losers = [
                {"symbol": "TONUSDT", "priceChangePercentFloat": -7.2, "lastPriceFloat": 0.0},
                {"symbol": "WLDUSDT", "priceChangePercentFloat": -9.5, "lastPriceFloat": 0.0},
                {"symbol": "PEPEUSDT", "priceChangePercentFloat": -5.4, "lastPriceFloat": 0.0}
            ]
        
        losers_items = []
        for l in losers[:3]:
            sym = l["symbol"].replace("-USDT", "").replace("-USD", "").replace("USDT", "").replace("USDC", "").strip()
            # جلب التحليل الفني من الـ API
            analysis = scan_coin(sym)
            
            decision = "HOLD"
            confidence = 50
            rsi = 50
            if isinstance(analysis, dict):
                decision = analysis.get("decision") or analysis.get("decision_type") or "HOLD"
                confidence = analysis.get("confidence") or analysis.get("confidence_score") or 50
                rsi = analysis.get("rsi")
                if "indicators" in analysis and isinstance(analysis["indicators"], dict):
                    rsi = rsi or analysis["indicators"].get("rsi")
                if rsi is None:
                    rsi = 50
                    
            losers_items.append(
                f"- ${sym} ({l['priceChangePercentFloat']:.1f}% | التحليل الفني: {decision} ثقة {confidence}% | RSI: {rsi})"
            )
        losers_text = "\n".join(losers_items)
        prompt = PROMPTS_CONFIG["losers"].format(losers_text=losers_text)

    elif post_type == "news":
        news_list = get_latest_news(limit=1)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية، سيتم توليد رؤية عامة للسوق كبديل...")
            prompt = PROMPTS_CONFIG["news_general"].format(
                news_text="تلاعب الحيتان في سوق العملات البديلة وتسييل صفقات العقود الآجلة للمتداولين الصغار."
            )
        else:
            news_item = news_list[0]
            title = news_item.get("title", "")
            desc = news_item.get("description", "")
            topic = classify_news_topic(title)
            
            news_text = f"عنوان الخبر: {title}\nتفاصيل: {desc}"
            print(f"[*] تم تصنيف موضوع الخبر المختار: [{topic}]")
            
            prompt_key = f"news_{topic}"
            if prompt_key in PROMPTS_CONFIG:
                prompt = PROMPTS_CONFIG[prompt_key].format(news_text=news_text)
            else:
                prompt = PROMPTS_CONFIG["news_general"].format(news_text=news_text)

    elif post_type == "tips":
        tips_topics = [
            "ليه الصفقة بتنجح وتكسب لما الواحد يدخل بمبلغ صغير جداً، وتخسر وتتصفى فوراً أول ما يدخل بمبلغ كبير ورافعة عالية؟",
            "ليه بمجرد ما يضرب السعر إيقاف الخسارة (Stop Loss) يرتد فوراً وينفجر للأعلى كأن المنصة بتراقب صفقات الناس مخصوص؟",
            "مطاردة العملة بعد ما تطير 30% (FOMO) والهبوط الفوري أول ما الواحد يقرر يشتري.",
            "استخدام رافعة مالية 50x أو 100x على عملات الميمز (مثل PEPE أو SHIB) والانتظار لحد التصفية الفورية كأنها قمار."
        ]
        chosen_topic = random.choice(tips_topics)
        
        # اختيار عملة بديلة عشوائية لكسر التكرار
        altcoins = ["SOL", "PEPE", "TON", "WLD", "SUI", "FET", "ENA", "DOGE", "SHIB", "AVAX", "NEAR", "RENDER", "OP", "ARB", "APT", "INJ", "LINK", "DOT", "ADA", "XRP", "LTC"]
        chosen_coin = "$" + random.choice(altcoins)
        prompt = PROMPTS_CONFIG["tips"].format(chosen_topic=chosen_topic, chosen_coin=chosen_coin)

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
        prompt = PROMPTS_CONFIG["alpha"].format(alpha_text=alpha_text)

    elif post_type == "digest":
        local_now = get_user_local_time()
        today_date = local_now.strftime("%d-%m-%Y")
        
        # قراءة وتحديث الرقم التسلسلي اليومي للموجز ليكون متسلسلاً بشكل صحيح كل 24 ساعة
        num_file = os.path.join(os.path.dirname(__file__), "digest_number.txt")
        digest_number = 1
        if os.path.exists(num_file):
            try:
                with open(num_file, "r") as f:
                    digest_number = int(f.read().strip()) + 1
            except Exception:
                pass
        try:
            with open(num_file, "w") as f:
                f.write(str(digest_number))
        except Exception:
            pass
        
        news_list = get_latest_news(limit=4)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية للموجز، سيتم توليد موجز عام للسوق...")
            news_text = "- هدوء نسبى في حركة العملات البديلة مع ترقب السيولة القادمة.\n- استقرار صفقات العقود الآجلة وتصفية المحافظ الهادئة."
        else:
            news_text = "\n".join([
                f"- {n['title']}: {n['description']}"
                for n in news_list
            ])
            
        prompt = PROMPTS_CONFIG["digest"].format(
            news_text=news_text,
            digest_number=digest_number,
            today_date=today_date
        )

    elif post_type == "opportunities":
        # أولاً: محاولة جلب منشور جاهز من API فرص الانفجار مباشرة
        ready_post = get_explosion_opportunity_post()
        if ready_post:
            print("[+] تم الحصول على منشور جاهز لفرص الانفجار من الـ API مباشرة. يتم استخدامه للنشر الفوري.")
            return ready_post.strip()
            
        # ثانياً: التراجع للذكاء الاصطناعي في حال عدم التوفر
        opps = get_bullish_opportunities()
        opp_items = []
        for o in opps[:3]:
            ticker = o.get("ticker", "").replace("-USDT", "").replace("-USD", "").replace("USDT", "").replace("USD", "")
            entry = o.get("entry_price", 0.0)
            targets = ", ".join([str(t) for t in o.get("targets", [])])
            opp_items.append(f"- ${ticker} (دخول: {entry} | أهداف: {targets})")
        opportunities_text = "\n".join(opp_items)
        prompt = PROMPTS_CONFIG["opportunities"].format(opportunities_text=opportunities_text)

    elif post_type == "market_status":
        status = get_btc_market_status()
        
        # أولاً: محاولة جلب منشور جاهز لحالة السوق من الـ API مباشرة
        if isinstance(status, dict) and "ready_post" in status:
            ready_post = status.get("ready_post")
            if ready_post:
                print("[+] تم الحصول على منشور جاهز لحالة السوق من الـ API مباشرة. يتم استخدامه للنشر الفوري.")
                return ready_post.strip()
                
        # ثانياً: التراجع للذكاء الاصطناعي في حال عدم التوفر
        btc_price = status.get("btc_price", 0.0)
        btc_change = status.get("price_change_24h") or status.get("price_change") or 0.0
        defense = status.get("downtrend_defense")
        defense_state = "نشط (حماية من الهبوط)" if defense else "غير نشط (السوق صاعد)"
        rsi = status.get("rsi", 50)
        adx = status.get("adx", 20)
        macd = status.get("macd", "Neutral")
        
        prompt = PROMPTS_CONFIG["market_status"].format(
            btc_price=btc_price,
            btc_change=btc_change,
            defense_state=defense_state,
            rsi=rsi,
            adx=adx,
            macd=macd
        )

    elif post_type == "coin_analysis":
        # محاولة جلب العملات الأكثر رواجاً أو صعوداً لتحديد عملة عشوائية لتحليلها
        chosen_coin = ticker or "SOL"
        if not ticker:
            try:
                alpha_list = get_trending_alpha(limit=3)
                if alpha_list:
                    chosen_coin = random.choice(alpha_list)["symbol"]
                else:
                    gainers = get_trending_futures(limit=3)
                    if gainers:
                        chosen_coin = random.choice(gainers)["symbol"]
            except Exception:
                pass
            
        # إزالة USDT/USD لضمان الحصول على الرمز الصافي
        chosen_coin = chosen_coin.replace("-USDT", "").replace("-USD", "").replace("USDT", "").replace("USDC", "").strip()
        if not chosen_coin:
            chosen_coin = random.choice(["SOL", "NEAR", "PEPE", "TON", "RENDER", "SUI", "FET", "ENA", "DOGE"])
            
        analysis = scan_coin(chosen_coin)
        
        # إذا كانت الاستجابة تحتوي على منشور جاهز من الخادم، نقوم بنشره مباشرة دون أي تعديل أو استدعاء للذكاء الاصطناعي
        if isinstance(analysis, dict) and "binance_post" in analysis:
            post_text = analysis.get("binance_post")
            if post_text:
                print(f"[+] تم الحصول على منشور جاهز لعملة {chosen_coin} من الـ API مباشرة. يتم استخدامه للنشر الفوري.")
                return post_text.strip()

        decision = analysis.get("decision") or analysis.get("decision_type", "HOLD")
        confidence = analysis.get("confidence") or analysis.get("confidence_score", 50)
        
        # استخراج المؤشرات بطريقة مرنة تدعم الصيغ المختلفة
        rsi = analysis.get("rsi")
        macd = analysis.get("macd")
        adx = analysis.get("adx")
        
        if "indicators" in analysis and isinstance(analysis["indicators"], dict):
            rsi = rsi or analysis["indicators"].get("rsi")
            macd = macd or analysis["indicators"].get("macd")
            adx = adx or analysis["indicators"].get("adx")
            
        # تنسيق المؤشرات بشكل تفصيلي يوضح حالة العملة (صاعدة/نازلة/حيادية)
        rsi_desc = "حيادي"
        if rsi is not None:
            try:
                rsi_val = float(rsi)
                if rsi_val > 70:
                    rsi_desc = f"{rsi_val} (تشبع شراء وزخم صاعد قوي)"
                elif rsi_val < 30:
                    rsi_desc = f"{rsi_val} (تشبع بيع وهبوط مستمر)"
                else:
                    rsi_desc = f"{rsi_val} (منطقة حياد واستقرار)"
            except ValueError:
                rsi_desc = str(rsi)
                
        macd_desc = str(macd) if macd else "حيادي"
        if macd and isinstance(macd, str):
            if "bull" in macd.lower() or "up" in macd.lower() or "صعود" in macd:
                macd_desc = f"{macd} (تقاطع صعودي إيجابي)"
            elif "bear" in macd.lower() or "down" in macd.lower() or "هبوط" in macd:
                macd_desc = f"{macd} (تقاطع هبوطي سلبي)"
                
        adx_desc = "حيادي"
        if adx is not None:
            try:
                adx_val = float(adx)
                if adx_val > 25:
                    adx_desc = f"{adx_val} (اتجاه قوي ونشط)"
                else:
                    adx_desc = f"{adx_val} (مسار عرضي ضعيف الاتجاه)"
            except ValueError:
                adx_desc = str(adx)

        rsi_text = f"RSI: {rsi_desc}"
        macd_text = f"MACD: {macd_desc}"
        adx_text = f"ADX: {adx_desc}"
        
        indicators_text = f"{rsi_text}، {macd_text}، {adx_text}"
        
        prompt = PROMPTS_CONFIG["coin_analysis"].format(
            ticker=f"${chosen_coin}",
            decision=decision,
            confidence=confidence,
            indicators_text=indicators_text
        )

    # تحديد ترتيب المحاولة للمزودين لضمان التراجع التلقائي (Fallback)
    providers_order = [selected_provider]
    for p in ["gemini", "groq", "grok"]:
        if p not in providers_order:
            providers_order.append(p)

    generated_content = None
    provider_names = {
        "gemini": "Google Gemini",
        "groq": "Groq (LPU)",
        "grok": "xAI (Grok)"
    }

    for p in providers_order:
        api_key = None
        base_url = None
        model = None
        
        if p == "gemini":
            api_key = GEMINI_API_KEY
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
            model = GEMINI_MODEL
        elif p == "groq":
            api_key = GROQ_API_KEY
            base_url = "https://api.groq.com/openai/v1"
            model = GROQ_MODEL
        elif p == "grok":
            api_key = XAI_API_KEY
            base_url = "https://api.x.ai/v1"
            model = GROK_MODEL

        if not api_key:
            # تخطي المزود لو مفتاح الوصول غير متوفر
            continue

        print(f"[*] جاري محاولة التوليد باستخدام [{provider_names[p]}] (النموذج: {model})...")
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": VETERAN_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75
            )
            generated_content = response.choices[0].message.content
            if generated_content:
                print(f"[+] تم توليد المحتوى بنجاح باستخدام [{provider_names[p]}].")
                break
        except Exception as e:
            print(f"[-] فشل استخدام [{provider_names[p]}]: {e}. سيتم الانتقال للبديل المتاح...")

    if not generated_content:
        print("[-] خطأ: فشل التوليد باستخدام جميع المزودين المتاحين!")
        return None

    return enforce_length_limit(generated_content, max_chars=400)

def upload_image_to_binance(image_path):
    """
    رفع صورة إلى Binance Square باستخدام سير العمل v2:
    1. طلب presigned URL والحصول على fileTicket
    2. رفع الصورة عبر PUT إلى presigned URL
    3. استطلاع حالة الصورة حتى تصبح جاهزة
    يُرجع imageUrl عند النجاح أو None عند الفشل.
    """
    if not BINANCE_SQUARE_API_KEY:
        print("[-] لا يمكن رفع الصورة: مفتاح BINANCE_SQUARE_API_KEY غير موجود.")
        return None
    
    if not os.path.exists(image_path):
        print(f"[-] ملف الصورة غير موجود: {image_path}")
        return None
    
    log_file = os.path.join(os.path.dirname(__file__), "api_debug.log")
    
    headers_json = {
        "X-Square-OpenAPI-Key": BINANCE_SQUARE_API_KEY,
        "Content-Type": "application/json",
        "clienttype": "binanceSkill"
    }
    
    # --- الخطوة 1: طلب presigned URL ---
    image_name = os.path.basename(image_path)
    presigned_url_endpoint = "https://www.binance.com/bapi/composite/v2/public/pgc/openApi/image/presignedUrl"
    
    try:
        print(f"[*] الخطوة 1: طلب رابط الرفع المسبق للصورة ({image_name})...")
        res1 = requests.post(
            presigned_url_endpoint,
            headers=headers_json,
            json={"imageName": image_name},
            timeout=15
        )
        res1.raise_for_status()
        result1 = res1.json()
        
        if result1.get("code") != "000000" or not result1.get("data"):
            err = f"فشل طلب presigned URL: code={result1.get('code')}, message={result1.get('message')}"
            print(f"[-] {err}")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE IMG PRESIGNED ERROR: {err}\n")
            return None
        
        presigned_url = result1["data"].get("presignedUrl")
        file_ticket = result1["data"].get("fileTicket")
        
        if not presigned_url or not file_ticket:
            print("[-] لم يتم استلام presignedUrl أو fileTicket من الاستجابة.")
            return None
        
        print(f"[+] تم الحصول على رابط الرفع المسبق و fileTicket بنجاح.")
        
    except Exception as e:
        print(f"[-] خطأ أثناء طلب presigned URL: {e}")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE IMG PRESIGNED EXCEPTION: {e}\n")
        return None
    
    # --- الخطوة 2: رفع الصورة عبر PUT ---
    try:
        print("[*] الخطوة 2: رفع الصورة إلى التخزين السحابي...")
        # تحديد نوع MIME بناءً على الامتداد
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
        content_type = mime_map.get(ext, "image/png")
        
        with open(image_path, "rb") as img_file:
            img_bytes = img_file.read()
        
        res2 = requests.put(
            presigned_url,
            data=img_bytes,
            headers={"Content-Type": content_type},
            timeout=30
        )
        res2.raise_for_status()
        print(f"[+] تم رفع الصورة بنجاح ({len(img_bytes)} بايت).")
        
    except Exception as e:
        print(f"[-] خطأ أثناء رفع الصورة إلى التخزين السحابي: {e}")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE IMG PUT EXCEPTION: {e}\n")
        return None
    
    # --- الخطوة 3: استطلاع حالة الصورة ---
    image_status_endpoint = "https://www.binance.com/bapi/composite/v2/public/pgc/openApi/image/imageStatus"
    max_attempts = 10
    poll_interval = 3  # ثوانٍ
    
    try:
        print("[*] الخطوة 3: انتظار معالجة الصورة...")
        for attempt in range(1, max_attempts + 1):
            time.sleep(poll_interval)
            res3 = requests.post(
                image_status_endpoint,
                headers=headers_json,
                json={"fileTicket": file_ticket},
                timeout=15
            )
            res3.raise_for_status()
            result3 = res3.json()
            
            if result3.get("code") == "000000" and result3.get("data"):
                status = result3["data"].get("status")
                image_url = result3["data"].get("imageUrl")
                
                if status == 1 and image_url:
                    print(f"[+] تمت معالجة الصورة بنجاح! (المحاولة {attempt}/{max_attempts})")
                    print(f"[+] رابط الصورة: {image_url}")
                    return image_url
                elif status == 0:
                    print(f"[*] الصورة قيد المعالجة... (المحاولة {attempt}/{max_attempts})")
                else:
                    print(f"[-] حالة غير متوقعة: status={status} (المحاولة {attempt}/{max_attempts})")
            else:
                print(f"[-] استجابة غير متوقعة من imageStatus: {result3.get('code')} - {result3.get('message')}")
        
        print(f"[-] انتهت مهلة انتظار معالجة الصورة بعد {max_attempts} محاولات.")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE IMG STATUS TIMEOUT: fileTicket={file_ticket}\n")
        return None
        
    except Exception as e:
        print(f"[-] خطأ أثناء استطلاع حالة الصورة: {e}")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE IMG STATUS EXCEPTION: {e}\n")
        return None


def post_to_binance_square(content):
    """
    إرسال المنشور إلى منصة Binance Square باستخدام OpenAPI.
    يتم رفع صورة المخطط البياني (latest_chart.png) تلقائياً إذا كانت موجودة.
    """
    if not BINANCE_SQUARE_API_KEY:
        print("[-] خطأ: مفتاح BINANCE_SQUARE_API_KEY غير موجود في ملف .env")
        sys.exit(1)
        
    # تقليص الهاشتاجات الزائدة لمنع الخطأ 220094
    content = prune_hashtags(content, max_hashtags=3)
        
    print("[*] جاري نشر المنشور على Binance Square...")
    
    # --- محاولة رفع الصورة إذا كانت موجودة ---
    chart_path = os.path.join(os.path.dirname(__file__), "latest_chart.png")
    image_url = None
    
    if os.path.exists(chart_path):
        print("[*] تم اكتشاف صورة مخطط بياني. جاري رفعها إلى Binance Square...")
        image_url = upload_image_to_binance(chart_path)
        if image_url:
            print("[+] تم رفع الصورة بنجاح. سيتم إرفاقها بالمنشور.")
        else:
            print("[!] فشل رفع الصورة. سيتم النشر بدون صورة (نص فقط).")
    
    # --- إعداد الحمولة ---
    url = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
    
    headers = {
        "X-Square-OpenAPI-Key": BINANCE_SQUARE_API_KEY,
        "Content-Type": "application/json",
        "clienttype": "binanceSkill"
    }
    
    payload = {
        "bodyTextOnly": content
    }
    
    # إضافة الصورة إلى الحمولة إذا تم رفعها بنجاح
    if image_url:
        payload["imageList"] = [image_url]
        payload["contentType"] = 1
        print(f"[*] المنشور سيتضمن صورة مرفقة: {image_url}")
    
    log_file = os.path.join(os.path.dirname(__file__), "api_debug.log")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        result = response.json()
        
        if result.get("code") == "000000":
            img_status = " مع صورة 📸" if image_url else ""
            print(f"[+] تم النشر بنجاح على Binance Square{img_status}! 🎉")
            if "data" in result:
                print(f"[+] تفاصيل الاستجابة: {result['data']}")
            return True
        else:
            err_msg = f"[-] فشل النشر. رمز الخطأ: {result.get('code')}, الرسالة: {result.get('message')}"
            print(err_msg)
            
            # إذا فشل النشر مع صورة، نحاول بدون صورة كخطة بديلة
            if image_url:
                print("[!] محاولة النشر بدون صورة كخطة بديلة...")
                fallback_payload = {"bodyTextOnly": content}
                try:
                    fb_response = requests.post(url, headers=headers, json=fallback_payload, timeout=15)
                    fb_response.raise_for_status()
                    fb_result = fb_response.json()
                    if fb_result.get("code") == "000000":
                        print("[+] تم النشر بنجاح بدون صورة (خطة بديلة)! 🎉")
                        if "data" in fb_result:
                            print(f"[+] تفاصيل الاستجابة: {fb_result['data']}")
                        return True
                    else:
                        print(f"[-] فشلت الخطة البديلة أيضاً: {fb_result.get('code')} - {fb_result.get('message')}")
                except Exception as fb_e:
                    print(f"[-] خطأ أثناء الخطة البديلة: {fb_e}")
            
            # تدوين الخطأ في ملف اللوغ للتشخيص
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE ERROR: code={result.get('code')} | message={result.get('message')} | Content length: {len(content)} | Has image: {bool(image_url)}\n")
            return False
            
    except Exception as e:
        err_msg = f"[-] حدث خطأ أثناء الاتصال بـ Binance Square: {e}"
        print(err_msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] BINANCE EXCEPTION: {e}\n")
        return False

def main(override_type=None, override_provider=None):
    parser = argparse.ArgumentParser(description="AI Binance Square Veteran Auto Poster")
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="توليد المنشور وطباعته محلياً للمراجعة دون نشره على المنصة"
    )
    parser.add_argument(
        "--type",
        choices=["gainers", "losers", "news", "tips", "alpha", "opportunities", "market_status", "coin_analysis", "random"],
        default="random",
        help="نوع المحتوى المراد توليده ونشره (الافتراضي: اختيار عشوائي لتنويع المنشورات)"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "groq", "grok", "default"],
        default="default",
        help="مزود الذكاء الاصطناعي لتوليد المنشور (gemini, groq, grok)"
    )
    parser.add_argument(
        "--ticker",
        default=None,
        help="رمز العملة لتقرير coin_analysis (مثال: SOL, BTC)"
    )
    args, unknown = parser.parse_known_args()
    
    # تحديد نوع المنشور
    post_type = override_type or args.type
    if post_type == "random":
        # النشر الدوري العشوائي يقتصر على الأنواع العامة فقط
        types = ["gainers", "losers", "alpha", "news", "tips"]
        weights = [20, 20, 20, 20, 20]
        post_type = random.choices(types, weights=weights, k=1)[0]
        print(f"[*] تم اختيار نوع المنشور عشوائياً بوزن نسبي: [{post_type}] لتنويع المحتوى.")
        
    # تحديد المزود المختار
    prov = override_provider or args.provider
    if prov == "default":
        prov = None
        
    custom_ticker = args.ticker

    # توليد المحتوى
    post_content = generate_post_content(post_type, provider=prov, ticker=custom_ticker)
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
