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
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
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
    resp = requests.post(url, headers=headers, data={"template_object": json.dumps(template)}, timeout=10)
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


def save_date_page(date_dir, today):
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 뉴스 · {today}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;700&family=Noto+Sans+KR:wght@300;400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0d0d0f;
    --surface: #16161a;
    --border: #2a2a32;
    --accent: #c8f060;
    --accent2: #60c8f0;
    --text: #f0ede8;
    --muted: #888;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Noto Sans KR', sans-serif; min-height: 100vh; }}

  header {{ padding: 28px 40px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 20px; }}
  .back {{ color: var(--muted); text-decoration: none; font-size: 13px; display: flex; align-items: center; gap: 6px; transition: color 0.15s; white-space: nowrap; }}
  .back:hover {{ color: var(--accent); }}
  .header-info h1 {{ font-family: 'Noto Serif KR', serif; font-size: 22px; font-weight: 700; }}
  .header-info h1 span {{ color: var(--accent); }}
  .header-info p {{ font-size: 12px; color: var(--muted); margin-top: 4px; font-weight: 300; }}

  main {{ max-width: 800px; margin: 0 auto; padding: 40px 24px; }}

  .news-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
    animation: fadeUp 0.3s ease both;
  }}
  .news-card:hover {{ border-color: #3a3a48; }}
  .news-card::before {{
    content: '';
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, var(--accent), var(--accent2));
    opacity: 0.6;
  }}

  .news-num {{ font-size: 10px; letter-spacing: 0.15em; color: var(--accent); text-transform: uppercase; margin-bottom: 8px; font-weight: 500; }}
  .news-title {{ font-family: 'Noto Serif KR', serif; font-size: 17px; font-weight: 700; line-height: 1.5; margin-bottom: 12px; color: var(--text); }}
  .news-summary {{ font-size: 14px; color: #b0b0b8; line-height: 1.8; margin-bottom: 14px; font-weight: 300; }}
  .news-meta {{ display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--muted); }}
  .news-source {{ background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 4px; }}
  .news-link {{ color: var(--accent2); text-decoration: none; margin-left: auto; }}
  .news-link:hover {{ text-decoration: underline; }}

  .loading {{ text-align: center; padding: 80px; color: var(--muted); font-size: 14px; }}
  @keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(12px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
</head>
<body>
<header>
  <a class="back" href="../">← 목록으로</a>
  <div class="header-info">
    <h1>AI 뉴스 <span>{today}</span></h1>
    <p id="header-updated">업데이트 정보 로딩 중...</p>
  </div>
</header>
<main id="content">
  <div class="loading">뉴스를 불러오는 중...</div>
</main>
<script>
fetch('./news.json')
  .then(r => r.json())
  .then(data => {{
    document.getElementById('header-updated').textContent = '업데이트: ' + data.updated + ' · EXAONE 요약';
    const main = document.getElementById('content');
    main.innerHTML = '';
    data.articles.forEach((a, i) => {{
      const card = document.createElement('div');
      card.className = 'news-card';
      card.style.animationDelay = (i * 0.04) + 's';
      const date = a.publishedAt ? new Date(a.publishedAt).toLocaleDateString('ko-KR') : '';
      card.innerHTML =
        '<div class="news-num">NEWS ' + String(i+1).padStart(2,'0') + '</div>'
        + '<div class="news-title">' + a.title + '</div>'
        + '<div class="news-summary">' + a.summary + '</div>'
        + '<div class="news-meta">'
        + (a.source ? '<span class="news-source">' + a.source + '</span>' : '')
        + '<span>' + date + '</span>'
        + (a.url ? '<a class="news-link" href="' + a.url + '" target="_blank">원문 보기 →</a>' : '')
        + '</div>';
      main.appendChild(card);
    }});
  }})
  .catch(() => {{
    document.getElementById('content').innerHTML = '<div class="loading">데이터를 불러올 수 없습니다.</div>';
  }});
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
    with open(os.path.join(date_dir, "news.json"), "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"docs/{today}/news.json 저장 완료")

    save_date_page(date_dir, today)
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
