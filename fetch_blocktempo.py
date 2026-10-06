#!/usr/bin/env python3
"""
抓取動區動趨 BlockTempo 最新文章，累積成本地資料庫，並產出手機可讀的 HTML。

用法：
  python3 fetch_blocktempo.py            # 抓最新 100 篇，合併進 data/posts.json，產出 docs/index.html
  python3 fetch_blocktempo.py --pages 3  # 抓更多頁（每頁 100 篇）

只用標準函式庫，不需要安裝任何套件。
"""
import argparse
import html
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://www.blocktempo.com/wp-json/wp/v2/posts"
FIELDS = "id,date,link,title,excerpt,categories,_links"
ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "posts.json"
OUT = ROOT / "docs" / "index.html"
KEEP = 600            # 本地最多保留幾篇
TZ = timezone(timedelta(hours=8))  # 台灣時間


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (blocktempo-daily)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s).replace("[…]", "").replace("[&hellip;]", "").strip()
    return s


def load_categories():
    """抓分類 id -> 名稱 對照表。"""
    cats = {}
    page = 1
    while True:
        rows = get_json(f"https://www.blocktempo.com/wp-json/wp/v2/categories?per_page=100&page={page}&_fields=id,name")
        if not rows:
            break
        for c in rows:
            cats[c["id"]] = html.unescape(c["name"])
        if len(rows) < 100:
            break
        page += 1
    return cats


def fetch_posts(pages):
    posts = []
    for p in range(1, pages + 1):
        rows = get_json(f"{API}?per_page=100&page={p}&_fields={FIELDS}")
        if not rows:
            break
        posts.extend(rows)
    return posts


def normalize(raw, cats):
    # 主分類：避開「即時新聞」「Uncategorized」這類沒資訊量的，挑第一個有意義的
    names = [cats.get(c, "") for c in raw.get("categories", [])]
    names = [n for n in names if n and n not in ("Uncategorized",)]
    primary = next((n for n in names if n != "即時新聞"), names[0] if names else "")
    return {
        "id": raw["id"],
        "date": raw["date"],                      # 站方時間（台灣）
        "link": raw["link"],
        "title": strip_html(raw["title"]["rendered"]),
        "excerpt": strip_html(raw["excerpt"]["rendered"]),
        "category": primary,
        "tags": names,
    }


def merge(new, old):
    by_id = {p["id"]: p for p in old}
    added = 0
    for p in new:
        if p["id"] not in by_id:
            added += 1
        by_id[p["id"]] = p
    merged = sorted(by_id.values(), key=lambda p: p["date"], reverse=True)[:KEEP]
    return merged, added


def render(posts, generated_at):
    by_day = {}
    for p in posts:
        day = p["date"][:10]
        by_day.setdefault(day, []).append(p)

    cat_counts = Counter(p["category"] for p in posts if p["category"])
    cats = [c for c, _ in cat_counts.most_common(14)]

    def day_label(day):
        d = datetime.strptime(day, "%Y-%m-%d")
        wd = "一二三四五六日"[d.weekday()]
        return f"{d.month} 月 {d.day} 日（{wd}）"

    chips = '<button class="chip on" data-cat="">全部</button>' + "".join(
        f'<button class="chip" data-cat="{html.escape(c)}">{html.escape(c)}</button>' for c in cats
    )

    sections = []
    for day, items in by_day.items():
        rows = []
        for p in items:
            t = p["date"][11:16]
            rows.append(
                f'<li class="post" data-cat="{html.escape(p["category"])}">'
                f'<a href="{html.escape(p["link"])}" target="_blank" rel="noopener">'
                f'<span class="meta"><time>{t}</time>'
                + (f'<span class="cat">{html.escape(p["category"])}</span>' if p["category"] else "")
                + f'</span><span class="title">{html.escape(p["title"])}</span>'
                + (f'<span class="excerpt">{html.escape(p["excerpt"])}</span>' if p["excerpt"] else "")
                + "</a></li>"
            )
        sections.append(
            f'<section class="day" data-day="{day}"><h2>{day_label(day)}<small>{len(items)} 篇</small></h2>'
            f'<ul>{"".join(rows)}</ul></section>'
        )

    return TEMPLATE.replace("{{CHIPS}}", chips).replace("{{SECTIONS}}", "".join(sections)) \
        .replace("{{COUNT}}", str(len(posts))).replace("{{GENERATED}}", generated_at)


TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>動區每日</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{
  --paper:#f7f8fa; --ink:#15181d; --ink-2:#4f5663; --ink-3:#8a919e;
  --line:#e2e5ea; --accent:#1f4e79; --accent-soft:#e3ecf5; --hit:#fff;
  box-sizing:border-box;
  padding-top:env(safe-area-inset-top,0px); padding-bottom:env(safe-area-inset-bottom,0px);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#121417; --ink:#eef0f3; --ink-2:#aeb5c0; --ink-3:#737a86;
    --line:#262a31; --accent:#8fb8e3; --accent-soft:#1c2a3a; --hit:#181b20;
  }
}
*{box-sizing:inherit;margin:0}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
body{background:var(--paper);color:var(--ink);font-family:"Noto Sans TC",-apple-system,"PingFang TC","Microsoft JhengHei",sans-serif;
  font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:640px;margin:0 auto;padding:0 16px 48px}
header{padding:28px 0 12px}
header h1{font-size:28px;font-weight:700;letter-spacing:.01em;line-height:1.2}
header p{color:var(--ink-3);font-size:13px;margin-top:6px}
header p a{color:inherit}
.chips{position:sticky;top:env(safe-area-inset-top,0px);background:var(--paper);padding:10px 0 12px;
  display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;border-bottom:1px solid var(--line);z-index:2}
.chips::-webkit-scrollbar{display:none}
.chip{flex:0 0 auto;border:1px solid var(--line);background:var(--hit);color:var(--ink-2);border-radius:999px;
  padding:6px 13px;font:inherit;font-size:14px;cursor:pointer}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
.chip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.day{padding-top:22px}
.day h2{font-size:15px;font-weight:500;color:var(--ink-2);display:flex;justify-content:space-between;align-items:baseline;
  padding-bottom:8px;border-bottom:1px solid var(--line)}
.day h2 small{font-size:12px;color:var(--ink-3);font-weight:400}
.day ul{list-style:none;padding:0}
.post{border-bottom:1px solid var(--line)}
.post a{display:block;padding:14px 0;color:inherit;text-decoration:none}
.post a:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.meta{display:flex;gap:10px;align-items:center;font-size:12px;color:var(--ink-3);margin-bottom:4px}
.cat{color:var(--accent);background:var(--accent-soft);padding:1px 7px;border-radius:4px}
.title{display:block;font-size:17px;font-weight:500;line-height:1.4}
.excerpt{display:block;color:var(--ink-2);font-size:14px;margin-top:4px;line-height:1.5;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.day.hidden,.post.hidden{display:none}
.empty{color:var(--ink-3);padding:40px 0;text-align:center;display:none}
footer{color:var(--ink-3);font-size:12px;padding-top:32px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>動區每日</h1>
  <p>來源 <a href="https://www.blocktempo.com" target="_blank" rel="noopener">blocktempo.com</a>・共 {{COUNT}} 篇・更新於 {{GENERATED}}</p>
</header>
<nav class="chips" aria-label="分類篩選">{{CHIPS}}</nav>
{{SECTIONS}}
<p class="empty">這個分類目前沒有文章。</p>
<footer>每天台灣時間早上 7 點自動抓取；內容版權屬動區動趨。</footer>
</div>
<script>
(function(){
  var chips=document.querySelectorAll('.chip'),posts=document.querySelectorAll('.post'),
      days=document.querySelectorAll('.day'),empty=document.querySelector('.empty');
  var saved='';try{saved=localStorage.getItem('bt-cat')||''}catch(e){}
  function apply(cat){
    chips.forEach(function(c){c.classList.toggle('on',c.dataset.cat===cat)});
    var any=false;
    posts.forEach(function(p){var show=!cat||p.dataset.cat===cat;p.classList.toggle('hidden',!show);any=any||show});
    days.forEach(function(d){d.classList.toggle('hidden',!d.querySelector('.post:not(.hidden)'))});
    empty.style.display=any?'none':'block';
    try{localStorage.setItem('bt-cat',cat)}catch(e){}
  }
  chips.forEach(function(c){c.addEventListener('click',function(){apply(c.dataset.cat)})});
  if(saved&&document.querySelector('.chip[data-cat="'+saved.replace(/"/g,'\\\\"')+'"]'))apply(saved);
})();
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=1, help="抓幾頁（每頁 100 篇）")
    args = ap.parse_args()

    old = json.loads(DATA.read_text("utf-8")) if DATA.exists() else []
    cats = load_categories()
    new = [normalize(r, cats) for r in fetch_posts(args.pages)]
    merged, added = merge(new, old)

    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(merged, ensure_ascii=False, indent=1), "utf-8")

    now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(merged, now), "utf-8")
    print(f"抓到 {len(new)} 篇，新增 {added} 篇，資料庫共 {len(merged)} 篇 → {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"失敗：{e}", file=sys.stderr)
        sys.exit(1)
