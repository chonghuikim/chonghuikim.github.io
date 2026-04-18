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


def update_index(today):
    index_path = os.path.join(REPO_DIR, "docs", "index.json")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"dates": []}

    if today not in index["dates"]:
        index["dates"].insert(0, today)

    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def save_date_page(date_dir):
    html = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 뉴스</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f0; color: #1a1a1a; }
  header { background: #1a1a2e; color: #fff; padding: 20px 32px; display: flex; align-items: center; gap: 16px; }
  .back { color: #aaa; text-decoration: none; font-size: 14px; }
  .back:hover { color: #fff; }
  header h1 { font-size: 20px; font-weight: 500; }
  header p { font-size: 12px; color: #aaa; margin-top: 3px; }
  main { max-width: 800px; margin: 32px auto; padding: 0 16px; }
  .card { background: #fff; border: 1px solid #e8e8e0; border-radius: 12px; padding: 20px 24px; margin-bottom: 14px; }
  .card-num { font-size: 11px; font-weight: 500; color: #888; margin-bottom: 6px; }
  .card-title { font-size: 16px; font-weight: 500; color: #1a1a1a; margin-bottom: 8px; line-height: 1.5; }
  .card-summary { font-size: 14px; color: #444; line-height: 1.7; margin-bottom: 10px; }
  .card-meta { display: flex; align-items: center; gap: 10px; font-size: 12px; color: #888; }
  .card-meta a { color: #4a90d9; text-decoration: none; }
  .card-meta a:hover { text-decoration: underline; }
  .loading { text-align: center; padding: 60px; color: #888; font-size: 14px; }
</style>
</head>
<body>
<header>
  <a class="back" href="../">← 목록</a>
  <div>
    <h1 id="header-date">AI 뉴스</h1>
    <p id="header-updated"></p>
  </div>
</header>
<main id="content"><div class="loading">뉴스를 불러오는 중...</div></main>
<script>
fetch('./news.json')
  .then(r => r.json())
  .then(data => {
    document.getElementById('header-date').textContent = 'AI 뉴스 · ' + data.date;
    document.getElementById('header-updated').textContent = '업데이트: ' + data.updated;
    document.title = 'AI 뉴스 ' + data.date;
    const main = document.getElementById('content');
    main.innerHTML = '';
    data.articles.forEach((a, i) => {
      const card = document.createElement('div');
      card.className = 'card';
      const date = a.publishedAt ? new Date(a.publishedAt).toLocaleDateString('ko-KR') : '';
      card.innerHTML = '<div class="card-num">' + (i+1) + '번째 뉴스 · ' + (a.source||'') + '</div>'
        + '<div class="card-title">' + a.title + '</div>'
        + '<div class="card-summary">' + a.summary + '</div>'
        + '<div class="card-meta"><span>' + date + '</span>'
        + (a.url ? '<a href="' + a.url + '" target="_blank">원문 보기 →</a>' : '') + '</div>';
      main.appendChild(card);
    });
  })
  .catch(() => { document.getElementById('content').innerHTML = '<div class="loading">데이터를 불러올 수 없습니다.</div>'; });
</script>
</body>
</html>"""
    with open(os.path.join(date_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def save_and_push(articles_data, today):
    date_dir = os.path.join(REPO_DIR, "docs", today)
    os.makedirs(date_dir, exist_ok=True)

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "date": today,
        "articles": articles_data,
    }
    json_path = os.path.join(date_dir, "news.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"docs/{today}/news.json 저장 완료")

    save_date_page(date_dir)
    print(f"docs/{today}/index.html 생성 완료")

    update_index(today)

    subprocess.run(["git", "add", f"docs/{today}/", "docs/index.json"], cwd=REPO_DIR, check=True)
    result = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=REPO_DIR)
    if result.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"뉴스 업데이트 {today}"], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "push"], cwd=REPO_DIR, check=True)
        print("GitHub 푸시 완료")
    else:
        print("변경사항 없음 - 푸시 스킵")


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 파이프라인 시작")

    print("뉴스 수집 중...")
    articles = fetch_news()
    print(f"{len(articles)}건 수집됨")

    articles_data = []
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

    save_and_push(articles_data, today)

    print("카카오톡 전송 중...")
    top3 = articles_data[:3]
    lines = [f"📰 AI 뉴스 TOP 3 ({today})"]
    for i, article in enumerate(top3, 1):
        lines.append(f"\n{i}. {article['title']}\n{article['summary']}")
    lines.append(f"\n자세히 보기: https://chonghuikim.github.io/{today}/")
    send_kakao_message("\n".join(lines))
    print("카카오톡 전송 완료")

    print("파이프라인 완료!")


if __name__ == "__main__":
    main()
