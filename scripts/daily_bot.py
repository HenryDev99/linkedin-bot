import os
import feedparser
import google.generativeai as genai
from github import Github
from datetime import datetime

# 1. 설정 및 시크릿 로드
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GITHUB_TOKEN = os.environ.get("GH_TOKEN")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

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

def generate_post(news_data):
    """Gemini가 주제를 선정하고 글을 작성합니다."""
    # Google API 설정
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # 모델 선택 (gemini-pro 또는 gemini-1.5-flash 등)
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        # 모델 로드 실패 시 기본 모델 시도
        print(f"모델 로드 실패, gemini-pro 시도: {e}")
        model = genai.GenerativeModel('gemini-pro')

    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    prompt = f"""
    당신은 10년차 시니어 프론트엔드 개발자이자 10만 팔로워를 보유한 링크드인 인플루언서입니다.
    오늘 날짜는 {today_date}입니다.
    
    [오늘의 최신 프론트엔드 뉴스 후보]
    {news_data}

    **미션:**
    1. 위 뉴스 목록 중, 한국의 프론트엔드 개발자들이 가장 흥미로워하거나 실무에 도움이 될만한 **가장 핫한 주제 1개**를 선정하세요.
    2. 그 주제를 바탕으로 **링크드인 게시글**을 작성하세요.

    **작성 포맷:**
    - **제목:** 이모지를 포함하여 호기심을 자극하는 제목
    - **본문:**
        - **Hook (도입부):** 개발자들의 공감을 이끌어내는 질문이나 강렬한 문장으로 시작하세요.
        - **Insight (핵심 내용):** 해당 트렌드나 기술의 중요성, 장단점을 쉽고 명확하게 설명하세요. (전문 용어는 괄호로 영어 병기)
        - **Action Item (적용점):** 실무 팁 3가지를 불렛 포인트로 정리하세요.
        - **Conclusion (마무리):** 댓글을 유도하며 마무리하세요.
    - **참고 링크:** 선정된 뉴스의 원본 링크를 맨 아래에 "🔗 원문 보기"로 남겨주세요.
    - **해시태그:** #Frontend #WebDev #트렌드 등 5개
    - **톤앤매너:** 전문적이지만 친근하게, '해요체'를 사용하세요.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI 글 작성 중 오류: {e}")
        return None

def create_github_issue(content):
    """작성된 글을 GitHub Issue로 등록합니다."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"📅 [Gemini] {today} 오늘의 프론트엔드 링크드인 초안"
        
        repo.create_issue(title=title, body=content)
        print(f"✅ GitHub Issue가 생성되었습니다: {title}")
    except Exception as e:
        print(f"GitHub Issue 생성 실패: {e}")

if __name__ == "__main__":
    print("🚀 Daily LinkedIn Bot (Powered by Gemini) 시작!")
    
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")
    elif not GITHUB_TOKEN:
        print("❌ GH_TOKEN 환경변수가 설정되지 않았습니다.")
    elif not REPO_NAME:
        print("❌ GITHUB_REPOSITORY 환경변수가 설정되지 않았습니다.")
    else:
        news_data = fetch_latest_news()
        
        if news_data:
            print(f"✅ {len(news_data.splitlines())}개의 뉴스를 수집했습니다.")
            print("✍️ Gemini가 글을 작성 중입니다...")
            post_content = generate_post(news_data)
            
            if post_content:
                create_github_issue(post_content)
            else:
                print("❌ 글 생성에 실패했습니다.")
        else:
            print("❌ 수집된 뉴스가 없습니다.")
