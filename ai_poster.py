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
أنت متداول ومحلل أسواق عملات رقمية مخضرم (Veteran Trader) ذو خبرة تفوق 12 عاماً في أسواق المال التقليدية والعملات المشفرة.
تتميز بالخصائص التالية في كتابتك:
- أسلوبك واقعي، جاد، وحذر للغاية. لا تبيع الأوهام ولا تعد بأرباح سريعة، بل تركز على الانضباط وإدارة المخاطر.
- تستخدم لغة قوية وعبارات تدل على الخبرة مثل: (في تجربتي بالأسواق...)، (الأسواق لا ترحم العواطف...)، (رأيت هذا السيناريو يتكرر مئات المرات...)، (المبتدئون يطاردون الشموع الخضراء، بينما المحترفون...).
- تقدم تحليلات موضوعية بناءً على الأرقام والمعطيات الحقيقية.
- تكتب منشوراتك باللغة العربية الفصحى بشكل جذاب ومنسق باستخدام النقاط (bullet points) والإيموجي المناسب.
- **إشارة للعملات (Coin Mentions):** احرص على ذكر عملات معينة وتسميتها بوضوح (مثل BTC, ETH, SOL, BNB) وربطها بمحتوى المنشور في صلب النص لجذب المتابعين المهتمين بهذه العملات.
- تلتزم التزاماً صارماً بإضافة **ما لا يزيد عن 3 هاشتاجات فقط** في نهاية المنشور لتجنب حظر المنشور.
- لا تقدم أي توصيات شراء أو بيع مباشرة أو استشارات مالية قانونية، بل تقدم محتوى تعليمياً وتوعوياً.
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
        
        # تحويل البيانات وترتيبها
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
                
        # ترتيب العملات تنازلياً للصاعدة، وتصاعدياً للهابطة
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
        
        # إذا كانت الاستجابة خطأ 451 (محظور قانونياً)، ننتقل للبديل فوراً
        if response.status_code == 451:
            print("[!] خطأ 451: خادم الاستضافة موجود في منطقة محظورة من Binance. يتم الانتقال للبديل الآمن (CoinCap)...")
            return get_trending_coincap(limit, get_losers)
            
        response.raise_for_status()
        tickers = response.json()
        
        # تصفية أزواج العملات التي تنتهي بـ USDT
        usdt_tickers = [
            t for t in tickers 
            if t.get("symbol", "").endswith("USDT")
        ]
        
        # تحويل الأرقام إلى قيم عشرية
        for t in usdt_tickers:
            t["priceChangePercentFloat"] = float(t.get("priceChangePercent", 0.0))
            t["lastPriceFloat"] = float(t.get("lastPrice", 0.0))
            
        # ترتيب حسب نسبة التغير
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
            # تنظيف وسوم HTML إن وجدت
            desc_clean = re.sub('<[^<]+?>', '', desc_text)
            news_items.append({
                "title": title,
                "description": desc_clean[:200]
            })
            
        return news_items
    except Exception as e:
        print(f"[-] خطأ أثناء جلب الأخبار: {e}")
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
        gainers = get_trending_futures(limit=5, get_losers=False)
        if not gainers:
            return None
        gainers_text = "\n".join([
            f"- عملة {g['symbol'].replace('USDT', '')}: ارتفعت بنسبة +{g['priceChangePercentFloat']:.2f}% (السعر: ${g['lastPriceFloat']:,.4f})"
            for g in gainers
        ])
        prompt = f"""
اكتب منشوراً تحليلياً حاداً وواقعياً كمتداول مخضرم حول هذه العملات الأكثر صعوداً (Exploded Upward) حالياً في السوق:
{gainers_text}

ملاحظات للتضمين:
- فسر للمتداولين المبتدئين لماذا مطاردة الارتفاعات الحالية (FOMO) هي انتحار مالي.
- تحدث عن أهمية انتظار التصحيح وإيجاد الدعم بدلاً من الشراء عند القمة.
- ركز على أهمية إدارة المخاطر والرافعة المالية الحذرة.
- اذكر عملات رئيسية أخرى مثل BTC أو ETH للتأكيد على اتجاه السوق العام.
- أضف ما لا يزيد عن 3 هاشتاجات فقط مثل: #Binance #Crypto #MarketInsight
"""

    elif post_type == "losers":
        losers = get_trending_futures(limit=5, get_losers=True)
        if not losers:
            return None
        losers_text = "\n".join([
            f"- عملة {l['symbol'].replace('USDT', '')}: انخفضت بنسبة {l['priceChangePercentFloat']:.2f}% (السعر: ${l['lastPriceFloat']:,.4f})"
            for l in losers
        ])
        prompt = f"""
اكتب منشوراً تحليلياً واقعياً وجاداً كمتداول مخضرم حول هذه العملات الأكثر هبوطاً وانخفاضاً (Exploded Downward) حالياً في السوق:
{losers_text}

ملاحظات للتضمين:
- حذر من خطر "التقاط السكين الساقطة" (شراء القاع دون تأكيد فني أو إشارات انعكاس واضحة).
- اشرح كيف أن الهبوط الحاد قد يكون فرصة للمستثمر الصبور، لكنه مصيدة للمتداول المتسرع الذي يستخدم رافعة مالية عالية.
- وجه المتداولين لمراقبة مستويات الدعم التاريخية وسيولة السوق لعملة BTC أو العملات المذكورة.
- اذكر عملات رئيسية أخرى مثل BTC أو ETH للتأكيد على اتجاه السوق العام.
- أضف ما لا يزيد عن 3 هاشتاجات فقط مثل: #Binance #Crypto #MarketInsight
"""

    elif post_type == "news":
        news_list = get_latest_news(limit=3)
        if not news_list:
            print("[*] فشل جلب الأخبار الحية، سيتم توليد رؤية عامة للسوق كبديل...")
            prompt = """
اكتب مقالاً تحليلياً للمتداولين كمتداول مخضرم يقدم رؤية ونظرة عامة على أوضاع السوق الحالية (Crypto Market Sentiment).
- تحدث عن كيفية تصفية الضوضاء الإخبارية والتركيز على الاتجاهات الحقيقية (Trends).
- وجه نصائح حول كيفية التداول الهادئ بعيداً عن الشائعات المنتشرة على وسائل التواصل الاجتماعي.
- اذكر أسماء عملات رئيسية بوضوح مثل BTC, ETH أو SOL للتعليق على أدائها العام تزامناً مع الأخبار.
- أضف ما لا يزيد عن 3 هاشتاجات فقط مثل: #Binance #Crypto #MarketInsight
"""
        else:
            news_text = "\n".join([
                f"- العنوان: {n['title']}\n  التفاصيل: {n['description']}"
                for n in news_list
            ])
            prompt = f"""
اكتب منشوراً يلخص ويعلق على هذه الأخبار الاقتصادية/أخبار الكريبتو الحالية من وجهة نظر متداول مخضرم:
{news_text}

ملاحظات للتضمين:
- لخص الخبر بأسلوب بسيط.
- اشرح الأثر الفعلي الحقيقي لهذا الخبر على حركة أسعار العملات مثل BTC, ETH أو SOL بشكل صريح.
- علّم المتابعين كيف لا يندفعون وراء العناوين الرنانة.
- أضف ما لا يزيد عن 3 هاشتاجات فقط مثل: #Binance #CryptoNews #MarketInsight
"""

    elif post_type == "tips":
        prompt = """
اكتب درساً عميقاً أو نصيحة تداول نفسية للمتداولين من واقع خبرتك الطويلة التي تمتد لأكثر من 12 عاماً.
ملاحظات للتضمين:
- اختر موضوعاً واحداً مهماً وركز عليه (مثلاً: الانضباط النفسي، أهمية وضع حد للخسارة، كيفية التعامل مع الخسائر المتتالية، أو خطورة زيادة حجم الصفقة بدون خطة).
- استخدم حكمة ونصائح مباشرة ومؤثرة تفرّق بين الهاوي والمحترف.
- **ذكر وإشارة للعملات:** اذكر عملات كبرى مثل BTC أو ETH أو SOL كأمثلة عملية لتبين للمتابع كيف يؤثر عدم الانضباط على تداول هذه العملات (مثال: 'حتى لو كنت تتداول أقوى الأصول كـ بيتكوين BTC أو إيثيريوم ETH، فإن غياب إدارة المخاطر سيمحيك...').
- أضف ما لا يزيد عن 3 هاشتاجات فقط مثل: #Binance #TradingTips #RiskManagement
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
        choices=["gainers", "losers", "news", "tips", "random"],
        default="random",
        help="نوع المحتوى المراد توليده ونشره (الافتراضي: اختيار عشوائي لتنويع المنشورات)"
    )
    args = parser.parse_args()
    
    # تحديد نوع المنشور
    post_type = args.type
    if post_type == "random":
        post_type = random.choice(["gainers", "losers", "news", "tips"])
        print(f"[*] تم اختيار نوع المنشور عشوائياً: [{post_type}] لتنويع المحتوى اليومي.")
        
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
