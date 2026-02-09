import os
import feedparser
import requests
import google.generativeai as genai
from datetime import datetime

# 1. 설정 및 시크릿 로드
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 2. 트렌드 소스 (RSS)
RSS_FEEDS = [
    "https://dev.to/feed/tag/frontend",
    "https://ui.toast.com/rss.xml",
    "https://betterprogramming.pub/feed",
    "https://www.smashingmagazine.com/feed",
    "https://web.dev/feed.xml",
    "https://reactjs.org/feed.xml",
    "https://nextjs.org/feed.xml",
]

def fetch_latest_news():
    """RSS에서 최신 글 제목과 링크를 수집합니다."""
    news_list = []
    print("🔍 최신 트렌드를 수집 중입니다...")
    
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title = entry.title
                link = entry.link
                if not any(title in item for item in news_list):
                    news_list.append(f"- [{title}]({link})")
        except Exception as e:
            print(f"Error fetching {feed_url}: {e}")
            
    return "\n".join(news_list)

def get_best_model():
    """사용 가능한 모델 중 가장 최신/성능 좋은 모델을 자동으로 선택합니다."""
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"📋 사용 가능한 모델 목록: {available_models}")

        # 우선순위: 1.5 Pro > 1.5 Flash > 1.0 Pro
        for model in available_models:
            if 'gemini-1.5-pro' in model:
                return model
        
        for model in available_models:
            if 'gemini-1.5-flash' in model:
                return model
                
        for model in available_models:
            if 'gemini-pro' in model:
                return model
                
        # 아무것도 못 찾으면 기본값
        return 'models/gemini-pro'
        
    except Exception as e:
        print(f"⚠️ 모델 목록 조회 실패: {e}")
        return 'models/gemini-pro'

def generate_post(news_data):
    """Gemini가 주제를 선정하고 글을 작성합니다."""
    if not GOOGLE_API_KEY:
        print("❌ API Key가 없습니다.")
        return None
        
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 동적으로 최적의 모델 선택
    best_model_name = get_best_model()
    print(f"🤖 선택된 모델: {best_model_name}")
    
    try:
        model = genai.GenerativeModel(best_model_name)
    except Exception as e:
        print(f"❌ 모델 로드 실패 ({best_model_name}): {e}")
        return None

    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    prompt = f"""
    당신은 10년차 시니어 프론트엔드 개발자이자 10만 팔로워를 보유한 링크드인 인플루언서입니다.
    오늘 날짜는 {today_date}입니다.
    
    [오늘의 최신 프론트엔드 뉴스 후보]
    {news_data}

    **미션:**
    1. 위 뉴스 목록 중, 한국의 프론트엔드 개발자들이 가장 흥미로워하거나 실무에 도움이 될만한 **가장 핫한 주제 1개**를 선정하세요.
    2. 그 주제를 바탕으로 **링크드인 게시글**을 작성하세요.

    **작성 규칙 (매우 중요):**
    - **절대 괄호 `()`를 사용하여 영문 용어를 병기하지 마세요.** (예: "서버 컴포넌트(Server Components)" -> "서버 컴포넌트")
    - **AI가 쓴 티가 나지 않도록**, 개발자들끼리 메신저나 술자리에서 대화하는 듯한 **자연스러운 구어체**를 사용하세요.
    - 번역투 문장("~에 대해 알아보겠습니다", "~를 제공합니다")을 피하고, "이거 진짜 물건이네요", "조심해야겠어요" 같은 표현을 쓰세요.
    - 문단 사이에는 빈 줄을 하나씩 넣어 가독성을 높이세요.

    **작성 포맷:**
    - **제목:** 이모지를 포함하여 호기심을 자극하는 제목 (낚시성 X, 핵심 O)
    - **본문:**
        - **Hook:** "다들 이거 보셨나요?", "와, 이게 진짜 나오네요." 처럼 자연스럽게 시작.
        - **Insight:** 뉴스 내용을 요약하되, 내 생각이나 경험을 섞어서 설명.
        - **Action Item:** 실무 팁 3가지 (불렛 포인트)
        - **Conclusion:** "오늘도 즐코하세요!", "도움 되셨길 바랍니다." 처럼 **담백하고 깔끔한 마무리.** (질문이나 억지스러운 댓글 유도 금지)
    - **참고 링크:** 선정된 뉴스의 원본 링크를 맨 아래에 "🔗 원문 보기"로 남겨주세요.
    - **해시태그:** #Frontend #WebDev #트렌드 등 5개
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ 글 생성 실패: {e}")
        return None

def send_telegram_message(content):
    """작성된 글을 텔레그램으로 전송합니다."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": content
    }
    
    try:
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            print("✅ 텔레그램 메시지 전송 성공!")
        else:
            print(f"❌ 전송 실패: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"텔레그램 전송 중 오류: {e}")

if __name__ == "__main__":
    print("🚀 Daily LinkedIn Bot (Clean Ending Ver.) 시작!")
    
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
    elif not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다.")
    elif not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID 환경변수가 설정되지 않았습니다.")
    else:
        # 1. 뉴스 수집
        news_data = fetch_latest_news()
        
        if news_data:
            print(f"✅ {len(news_data.splitlines())}개의 뉴스를 수집했습니다.")
            
            # 2. AI 글 작성 (모델 자동 선택)
            print("✍️ Gemini가 글을 작성 중입니다...")
            post_content = generate_post(news_data)
            
            if post_content:
                # 3. 결과 전송 (텔레그램)
                send_telegram_message(post_content)
            else:
                print("❌ 글 생성에 실패했습니다.")
        else:
            print("❌ 수집된 뉴스가 없습니다.")
