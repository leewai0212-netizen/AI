#!/usr/bin/env python3
"""
Simple Douyin (TikTok China) comment crawler.

The script calls the public web comment API that powers https://www.douyin.com.
You must provide a valid ``aweme_id`` (video id) or a share URL. Supplying a
browser cookie taken from https://www.douyin.com/ greatly improves the success
rate because the endpoint often returns empty payloads for anonymous clients.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import pathlib
import re
import sys
import time
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, Iterator, List, Optional

import requests

COMMENT_API = "https://www.iesdouyin.com/web/api/v2/comment/list/"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.douyin.com/",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
AWEME_PATTERN = re.compile(r"(?:/video/|aweme_id=)(\d+)")


class DouyinAPIError(RuntimeError):
    """Custom error raised when the Douyin API fails."""


@dataclass
class Comment:
    cid: str
    text: str
    create_time: int
    digg_count: int
    reply_total: int
    aweme_id: str
    user_nickname: Optional[str]
    user_uid: Optional[str]
    user_short_id: Optional[str]


def extract_aweme_id(value: str, session: Optional[requests.Session] = None) -> str:
    """Return the aweme (video) id from a number or Douyin share URL."""

    candidate = (value or "").strip()
    if not candidate:
        raise ValueError("aweme_id or share URL is required.")

    if candidate.isdigit():
        return candidate

    match = AWEME_PATTERN.search(candidate)
    if match:
        return match.group(1)

    if not candidate.startswith(("http://", "https://")):
        raise ValueError(f"Unsupported aweme reference: {value}")

    # Follow short URLs such as https://v.douyin.com/xxxx/
    session = session or requests.Session()
    try:
        response = session.get(
            candidate,
            headers=DEFAULT_HEADERS,
            allow_redirects=True,
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:  # pragma: no cover - best effort
        raise ValueError(f"Unable to resolve share link: {exc}") from exc

    final_url = response.url or ""
    match = AWEME_PATTERN.search(final_url)
    if not match:
        raise ValueError(
            "The provided URL does not appear to contain a valid aweme_id."
        )
    return match.group(1)


class DouyinCommentCrawler:
    """Fetch comments for a single Douyin video using the web API."""

    def __init__(
        self,
        cookie: Optional[str] = None,
        delay: float = 0.8,
        timeout: int = 10,
        max_retries: int = 3,
    ) -> None:
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS.copy())
        if cookie:
            self.session.headers["Cookie"] = cookie.strip()
        self.delay = max(delay, 0.0)
        self.timeout = timeout
        self.max_retries = max_retries

    def fetch_comments(
        self, aweme_id: str, limit: Optional[int] = None, page_size: int = 20
    ) -> Iterator[Comment]:
        cursor = 0
        fetched = 0
        while True:
            payload = self._request_page(aweme_id, cursor, page_size)
            comments = payload.get("comments") or []

            if not comments and cursor == 0 and not payload.get("has_more"):
                raise DouyinAPIError(
                    "API returned no comments. Provide a browser cookie or "
                    "double-check the aweme_id."
                )

            for raw in comments:
                comment = self._normalize_comment(raw, aweme_id)
                fetched += 1
                yield comment
                if limit and fetched >= limit:
                    return

            if not payload.get("has_more"):
                return

            cursor = payload.get("cursor", cursor + page_size)
            time.sleep(self.delay)

    def _request_page(self, aweme_id: str, cursor: int, count: int) -> Dict:
        params = {
            "aweme_id": aweme_id,
            "cursor": cursor,
            "count": count,
            "item_type": 0,
            "insert_ids": "",
            "rcFT": "",
            "reply_limit": 3,
            "device_platform": "webapp",
            "aid": "6383",
        }

        attempt = 0
        while True:
            attempt += 1
            try:
                response = self.session.get(
                    COMMENT_API,
                    params=params,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
            except (requests.RequestException, ValueError) as exc:
                if attempt > self.max_retries:
                    raise DouyinAPIError(f"Request failed: {exc}") from exc
                backoff = min(self.delay * attempt, 5)
                logging.warning(
                    "Request error (%s). Retrying in %.1fs (attempt %s/%s)",
                    exc,
                    backoff,
                    attempt,
                    self.max_retries,
                )
                time.sleep(backoff)
                continue

            status = payload.get("status_code")
            if isinstance(status, dict):
                code = status.get("StatusCode")
                msg = status.get("StatusMsg", "")
            else:
                code = status
                msg = payload.get("status_msg", "")

            if code not in (None, 0):
                raise DouyinAPIError(f"API error {code}: {msg}")
            return payload

    @staticmethod
    def _normalize_comment(raw: Dict, aweme_id: str) -> Comment:
        user = raw.get("user") or {}

        return Comment(
            cid=str(raw.get("cid", "")),
            text=raw.get("text", ""),
            create_time=int(raw.get("create_time", 0)),
            digg_count=int(raw.get("digg_count", 0)),
            reply_total=int(raw.get("reply_comment_total", 0)),
            aweme_id=str(aweme_id),
            user_nickname=user.get("nickname"),
            user_uid=user.get("uid") or user.get("sec_uid"),
            user_short_id=user.get("short_id"),
        )


def save_comments(comments: Iterable[Comment], destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    suffix = destination.suffix.lower()

    rows = [asdict(comment) for comment in comments]
    if not rows:
        logging.warning("No comments to save, skipping file write.")
        return

    if suffix in {".json", ".jsonl"}:
        mode = "w"
        with destination.open(mode, encoding="utf-8") as fp:
            if suffix == ".jsonl":
                for row in rows:
                    fp.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                json.dump(rows, fp, ensure_ascii=False, indent=2)
        logging.info("Saved %s comments to %s", len(rows), destination)
        return

    headers = list(rows[0].keys())
    with destination.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    logging.info("Saved %s comments to %s", len(rows), destination)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch comments from a public Douyin video."
    )
    parser.add_argument(
        "--aweme-id",
        help="Numeric aweme (video) id. Optional if --share-url is provided.",
    )
    parser.add_argument(
        "--share-url",
        help="Full Douyin share link such as https://v.douyin.com/xxxx/.",
    )
    parser.add_argument(
        "--cookie",
        help="Raw Cookie header value copied from an authenticated Douyin tab.",
    )
    parser.add_argument(
        "--cookie-file",
        type=pathlib.Path,
        help="Optional text file that contains the Cookie header.",
    )
    parser.add_argument(
        "--max-comments",
        type=int,
        default=100,
        help="Stop after this many comments (default: 100, 0 means no limit).",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=20,
        help="How many comments to request per API call (default: 20).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.8,
        help="Seconds to wait between API calls (default: 0.8).",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        help="Optional path for saving results (.json, .jsonl, or .csv).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity.",
    )
    return parser


def load_cookie_from_file(path: pathlib.Path) -> str:
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Cookie file {path} is empty.")
    return content


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s %(message)s",
    )

    cookie_value = args.cookie or ""
    if args.cookie_file:
        cookie_value = load_cookie_from_file(args.cookie_file)

    session_for_share = requests.Session() if args.share_url and not args.aweme_id else None
    aweme_id = args.aweme_id or extract_aweme_id(args.share_url, session_for_share)

    crawler = DouyinCommentCrawler(
        cookie=cookie_value,
        delay=args.delay,
        timeout=10,
        max_retries=3,
    )

    limit = args.max_comments if args.max_comments > 0 else None
    comments = list(crawler.fetch_comments(aweme_id, limit=limit, page_size=args.page_size))

    if args.output:
        save_comments(comments, args.output)
    else:
        for item in comments:
            print(json.dumps(asdict(item), ensure_ascii=False))

    logging.info("Fetched %s comments for aweme %s", len(comments), aweme_id)
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        raise SystemExit(main())
    except DouyinAPIError as exc:
        logging.error("%s", exc)
        raise SystemExit(2) from exc
    except ValueError as exc:
        logging.error("%s", exc)
        raise SystemExit(2) from exc
