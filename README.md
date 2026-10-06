# 動區每日

每天自動抓取 [動區動趨 BlockTempo](https://www.blocktempo.com) 最新文章，整理成手機可讀的一頁。

## 一次性設定（GitHub 上做，大約 5 分鐘）

1. 在 GitHub 建一個新 repo，例如 `blocktempo-daily`，把這個資料夾的所有檔案上傳。
2. 進 repo 的 **Settings → Pages**，Source 選 **Deploy from a branch**，Branch 選 `main`，資料夾選 `/docs`，存檔。
3. 進 **Actions** 分頁，點「每日抓取動區」，按 **Run workflow** 跑第一次。
4. 大約一分鐘後，打開 `https://itrunsitruns.github.io/blocktempo-daily/` 就能看。把它加到手機主畫面。

之後每天台灣時間早上 7 點會自動更新。資料會累積（最多保留 600 篇），不只看當天。

## 在自己電腦跑（不需要 GitHub）

```
python3 fetch_blocktempo.py
```
會產生 `docs/index.html`，直接用瀏覽器開。只用 Python 標準函式庫，不用安裝任何東西。

想一次抓更多歷史：`python3 fetch_blocktempo.py --pages 3`

## 檔案

- `fetch_blocktempo.py` — 抓取 + 產生網頁
- `data/posts.json` — 累積的文章資料庫
- `docs/index.html` — 產出的網頁
- `.github/workflows/daily.yml` — 每日排程
