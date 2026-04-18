import os
import json
import requests
import subprocess
from datetime import datetime, timezone

NEWS_API_KEY = "Fce93691b6a94b749c51fcc0d27c084d"
KAKAO_ACCESS_TOKEN = "QdnNMeO6PLcXDHtTyohLGUmDPKdRB3zqAAAAAQoXEO8AAAGdnmFUg1v0-avl6D9k"
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "exaone3.5:7.8b"

REPO_DIR = os.path.dirname(os.path.abspath(__file__))


def fetch_news():
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "AI OR 인공지능 OR artificial intelligence",
        "language": "ko",
        "pageSize": 10,
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("articles", [])[:10]


def summarize_with_ollama(title, description):
    prompt = f"""다음 뉴스를 한국어로 2~3문장으로 간결하게 요약해줘.

제목: {title}
내용: {description or '내용 없음'}

요약:"""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def send_kakao_message(text):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {KAKAO_ACCESS_TOKEN}"}
    template = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": "https://chonghuikim.github.io",
            "mobile_web_url": "https://chonghuikim.github.io",
        },
    }
    resp = requests.post(
        url, headers=headers,
        data={"template_object": json.dumps(template)},
        timeout=10
    )
    resp.raise_for_status()


def save_and_push(articles_data):
    docs_dir = os.path.join(REPO_DIR, "docs", "data")
    os.makedirs(docs_dir, exist_ok=True)

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "articles": articles_data,
    }
    json_path = os.path.join(docs_dir, "news.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("news.json 저장 완료")

    subprocess.run(["git", "add", "docs/data/news.json"], cwd=REPO_DIR, check=True)
    today = datetime.now().strftime("%Y-%m-%d")
    result = subprocess.run(
        ["git", "diff", "--staged", "--quiet"], cwd=REPO_DIR
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "commit", "-m", f"뉴스 업데이트 {today}"],
            cwd=REPO_DIR, check=True
        )
        subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
        print("GitHub 푸시 완료")
    else:
        print("변경사항 없음 - 푸시 스킵")


def main():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 파이프라인 시작")

    print("뉴스 수집 중...")
    articles = fetch_news()
    print(f"{len(articles)}건 수집됨")

    articles_data = []
    kakao_lines = [f"📰 AI 뉴스 요약 ({datetime.now().strftime('%Y-%m-%d')})\n"]

    for i, article in enumerate(articles, 1):
        title = article.get("title", "")
        description = article.get("description", "")
        url = article.get("url", "")
        source = article.get("source", {}).get("name", "")

        print(f"[{i}/10] 요약 중: {title[:40]}...")
        summary = summarize_with_ollama(title, description)

        articles_data.append({
            "title": title,
            "summary": summary,
            "url": url,
            "source": source,
            "publishedAt": article.get("publishedAt", ""),
        })
        kakao_lines.append(f"{i}. {title}\n{summary}\n")

    save_and_push(articles_data)

    print("카카오톡 전송 중...")
    top3 = articles_data[:3]
    lines = [f"📰 AI 뉴스 TOP 3 ({datetime.now().strftime('%Y-%m-%d')})"]
    for i, article in enumerate(top3, 1):
        lines.append(f"\n{i}. {article['title']}\n{article['summary']}")
    lines.append("\n자세히 보기: https://chonghuikim.github.io")
    send_kakao_message("\n".join(lines))
    print("카카오톡 전송 완료")

    print("파이프라인 완료!")


if __name__ == "__main__":
    main()
