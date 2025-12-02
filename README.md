# Douyin Comment Crawler

一个使用 Python 调用抖音 Web 评论接口的小工具。你可以通过提供 `aweme_id`
（视频 ID）或分享链接来批量抓取评论，并将结果保存为 JSON/JSONL/CSV 文件。

## 环境准备

```bash
python3 -m venv .venv                 # 可选
source .venv/bin/activate             # 可选
python3 -m pip install -r requirements.txt
```

## 快速使用

```bash
python3 douyin_comment_crawler.py \
  --share-url "https://v.douyin.com/xxxx/" \
  --cookie "$(cat cookie.txt)" \
  --max-comments 200 \
  --output data/comments.jsonl
```

- `--aweme-id`：若你已经知道视频 ID，可直接指定。
- `--share-url`：传入任意抖音分享链接，脚本会自动解析 ID。
- `--cookie` / `--cookie-file`：强烈建议携带浏览器中抓到的 Cookie（含 `ttwid`
  `msToken` 等字段），否则接口可能返回空结果。
- `--output`：指定导出文件，支持 `.json`、`.jsonl`、`.csv`。

