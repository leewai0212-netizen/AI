#!/usr/bin/env python3
"""Simple Douyin (TikTok China) comment scraper.

The public web API is heavily rate-limited and protected by anti-bot
strategies. This script focuses on ergonomics: provide your own browser
cookies, optionally a custom msToken, and scrape comments in small
batches with polite delays.
"""
from __future__ import annotations

import argparse
import csv
import dataclasses
import logging
import random
import re
import sys
import time
from pathlib import Path
from typing import Iterator

import requests

COMMENT_API = "https://www.douyin.com/aweme/v1/web/comment/list/"
SHARE_URL_RE = re.compile(r"video/(\d+)")
DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Safari/537.36"
)


@dataclasses.dataclass
class Comment:
    comment_id: str
    aweme_id: str
    user_id: str
    nickname: str
    text: str
    digg_count: int
    create_time: int


class DouyinCommentClient:
    def __init__(self, cookie: str, user_agent: str = DEFAULT_UA, *, proxy: str | None = None) -> None:
        if not cookie:
            raise ValueError("A valid Douyin cookie string is required.")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Referer": "https://www.douyin.com/",
                "Cookie": cookie,
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
        )
        if proxy:
            self.session.proxies.update({
                "http": proxy,
                "https": proxy,
            })

    def resolve_aweme_id(self, share_url: str) -> str:
        """Follow the share link and extract the aweme_id."""
        logging.debug("Resolving share URL %s", share_url)
        resp = self.session.get(share_url, allow_redirects=True, timeout=15)
        resp.raise_for_status()
        final_url = resp.url
        match = SHARE_URL_RE.search(final_url)
        if not match:
            raise ValueError(f"无法从链接中提取aweme_id，请确认分享链接是否正确: {final_url}")
        return match.group(1)

    def iter_comments(
        self,
        aweme_id: str,
        *,
        page_size: int = 20,
        max_pages: int | None = None,
        pause_range: tuple[float, float] = (1.0, 3.0),
    ) -> Iterator[Comment]:
        cursor = 0
        pages = 0
        while True:
            params = {
                "aweme_id": aweme_id,
                "cursor": cursor,
                "count": page_size,
                "item_type": 0,
                "os_api": 1,
                "device_platform": "webapp",
                "channel": "channel_pc_web",
                "aid": "6383",
                "locale": "zh-CN",
                "app_name": "douyin_web",
                "version_code": "170400",
                "web_version": "100200",
                "sign_source": "pc",
                "cookie_enabled": "true",
                "screen_width": 1920,
                "screen_height": 1080,
            }
            logging.debug("Requesting cursor=%s", cursor)
            resp = self.session.get(COMMENT_API, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            comments = data.get("comments") or []
            for raw in comments:
                user = raw.get("user") or {}
                yield Comment(
                    comment_id=str(raw.get("cid", "")),
                    aweme_id=str(aweme_id),
                    user_id=str(user.get("uid", "")),
                    nickname=str(user.get("nickname", "")),
                    text=str(raw.get("text", "")),
                    digg_count=int(raw.get("digg_count", 0)),
                    create_time=int(raw.get("create_time", 0)),
                )
            has_more = data.get("has_more")
            cursor = data.get("cursor", cursor)
            pages += 1
            if not has_more:
                logging.info("No more comments. Received %s pages", pages)
                break
            if max_pages is not None and pages >= max_pages:
                logging.info("Reached max_pages=%s", max_pages)
                break
            sleep_time = random.uniform(*pause_range)
            logging.debug("Sleeping %.2fs to stay polite", sleep_time)
            time.sleep(sleep_time)


def write_csv(rows: Iterator[Comment], output_file: Path) -> int:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["comment_id", "aweme_id", "user_id", "nickname", "text", "digg_count", "create_time"])
        count = 0
        for c in rows:
            writer.writerow([c.comment_id, c.aweme_id, c.user_id, c.nickname, c.text, c.digg_count, c.create_time])
            count += 1
    return count


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape Douyin comments from a share URL.")
    parser.add_argument("share_url", help="Douyin share URL, e.g. https://v.douyin.com/xxxx/")
    parser.add_argument("cookie", help="Cookie string captured from web.douyin.com requests")
    parser.add_argument("-o", "--output", default="douyin_comments.csv", help="Where to store the CSV result")
    parser.add_argument("--proxy", help="Optional HTTP/HTTPS proxy, e.g. http://127.0.0.1:7890")
    parser.add_argument("--page-size", type=int, default=20, help="Number of comments per request (<=50 is safer)")
    parser.add_argument("--max-pages", type=int, help="Stop after N pages")
    parser.add_argument(
        "--pause-range",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        default=(1.0, 3.0),
        help="Random sleep range between requests (seconds)",
    )
    parser.add_argument("--log-level", default="INFO", help="Python logging level")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    client = DouyinCommentClient(cookie=args.cookie, proxy=args.proxy)
    try:
        aweme_id = client.resolve_aweme_id(args.share_url)
    except Exception as exc:  # pragma: no cover - CLI UX
        logging.error("无法解析分享链接: %s", exc)
        return 1
    logging.info("Resolved aweme_id=%s", aweme_id)

    rows = client.iter_comments(
        aweme_id,
        page_size=args.page_size,
        max_pages=args.max_pages,
        pause_range=tuple(args.pause_range),
    )
    written = write_csv(rows, Path(args.output))
    logging.info("Done. Wrote %s comments to %s", written, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
