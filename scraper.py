import os
import time
import random
import requests
from typing import TypedDict, List
from dotenv import load_dotenv

load_dotenv()

class Profile(TypedDict):
    username: str
    platform: str
    followers_count: int
    bio: str
    recent_posts: str

def get_profiles() -> List[Profile]:
    """
    محرك السحب الفعلي:
    يقوم بالاتصال المباشر باستخدام Session ID، يسحب البيانات،
    ويطبق نظام التمويه (التوقف العشوائي) لتفادي الحظر.
    """
    results = []
    
    # جلب المفاتيح من ملف البيئة السري (لا تكتبها هنا أبداً)
    IG_SESSION = os.getenv("IG_SESSION_ID")
    
    # قائمة الحسابات أو الكلمات المفتاحية المستهدفة للبحث
    # (يمكنك لاحقاً تغذية هذه القائمة بأسماء حسابات استخرجتها من هاشتاقات معينة)
    target_usernames = ["target_user_1", "target_user_2", "target_user_3"] 

    # إعدادات التخفي (لجعل الطلب يبدو وكأنه من متصفح حقيقي)
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        "x-ig-app-id": "936619743392459", # ID تطبيق انستقرام الرسمي للويب
    }
    
    cookies = {"sessionid": IG_SESSION}

    for username in target_usernames:
        print(f"\n🔍 جاري فحص حساب: {username} ...")

        try:
            # طلب بيانات الحساب من خوادم انستقرام المخفية
            url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
            response = requests.get(url, headers=headers, cookies=cookies, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']['user']:
                    user = data['data']['user']
                    followers = user['edge_followed_by']['count']
                    bio = user['biography']

                    # سحب وصف آخر 3 منشورات ليعرف Groq نوع المحتوى
                    recent_posts_texts = []
                    edges = user['edge_owner_to_timeline_media']['edges'][:3]
                    for edge in edges:
                        captions = edge['node']['edge_media_to_caption']['edges']
                        if captions:
                            recent_posts_texts.append(captions[0]['node']['text'])

                    # دمج النصوص واقتطاعها لـ 400 حرف لتوفير الحد المجاني لـ Groq API
                    recent_posts_str = " | ".join(recent_posts_texts)[:400] 

                    # 1. التصفية الصارمة: فقط الحسابات بين 9,000 و 100,000 متابع
                    if 9000 <= followers <= 100000:
                        results.append({
                            "username": username,
                            "platform": "instagram",
                            "followers_count": followers,
                            "bio": bio,
                            "recent_posts": recent_posts_str
                        })
                        print(f"✅ تم القبول الأولي للحساب ({followers} متابع). سيتم تسليمه لعقل Groq.")
                    else:
                        print(f"❌ تم تخطي الحساب ({followers} متابع). خارج النطاق المستهدف.")
                else:
                    print(f"⚠️ لم يتم العثور على بيانات للحساب.")
            else:
                print(f"⚠️ فشل الاتصال بالمنصة. رمز الخطأ: {response.status_code}")

        except Exception as e:
            print(f"⚠️ خطأ تقني أثناء فحص {username}: {e}")

        # 2. التأخير العشوائي المضاد للحظر (Anti-bot Delay)
        # توقف إجباري مدته عشوائية بين 45 و 90 ثانية
        delay = random.uniform(45.0, 90.0)
        print(f"⏳ إيقاف مؤقت لمدة {int(delay)} ثانية للتمويه...")
        time.sleep(delay)

    return results

# ملاحظة بخصوص تيك توك: 
# تم التركيز هنا على انستقرام لأن حمايته يمكن تخطيها بـ SessionID بسهولة عبر الـ Requests. 
# تيك توك يتطلب توقيعات معقدة (X-Bogus) تتغير يومياً، ولإضافته ستحتاج لاحقاً لمكتبة مثل TikTokApi.
