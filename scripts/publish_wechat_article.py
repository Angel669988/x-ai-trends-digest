#!/usr/bin/env python3
"""Publish a WeChat Official Account article via draft/add + freepublish/submit.

Requires:
  - AppID / AppSecret
  - thumb_media_id (permanent media id for cover)
  - HTML content (already formatted)

Usage:
  python3 scripts/publish_wechat_article.py \
    --app-id APPID \
    --app-secret APPSECRET \
    --title "2026-02-04 AI热点日报" \
    --html-file /path/to/content.html \
    --thumb-media-id MEDIA_ID

Use --draft-only to create a draft without publishing.
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from html import unescape
import re
import subprocess

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
PUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"


def _request_json(url, method="GET", payload=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
        return json.loads(body)
    except Exception:
        return _request_json_curl(url, method=method, payload=payload)


def _request_json_curl(url, method="GET", payload=None):
    cmd = ["curl", "-sS", "--fail", "--max-time", "20", "-X", method]
    resolve_ips = os.environ.get("WECHAT_API_HOST_IPS", "").strip()
    if resolve_ips:
        for ip in [p.strip() for p in resolve_ips.split(",") if p.strip()]:
            cmd += ["--resolve", f"api.weixin.qq.com:443:{ip}"]
    if payload is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(payload, ensure_ascii=False)]
    cmd.append(url)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl failed with code {result.returncode}")
    return json.loads(result.stdout)


def _get_access_token(app_id, app_secret):
    qs = urllib.parse.urlencode(
        {
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        }
    )
    url = f"{TOKEN_URL}?{qs}"
    data = _request_json(url)
    if "access_token" not in data:
        raise RuntimeError(f"Failed to get access_token: {data}")
    return data["access_token"]


def _strip_tags(html):
    text = re.sub(r"<[^>]+>", "", html)
    return unescape(text).strip()


def _build_digest(html, max_len=80):
    text = _strip_tags(html)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _draft_add(access_token, title, html, thumb_media_id, author=None, source_url=None):
    payload = {
        "articles": [
            {
                "article_type": "news",
                "title": title,
                "author": author or "",
                "digest": _build_digest(html, max_len=80),
                "content": html,
                "content_source_url": source_url or "",
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }
    url = f"{DRAFT_ADD_URL}?access_token={access_token}"
    return _request_json(url, method="POST", payload=payload)


def _publish(access_token, media_id):
    payload = {"media_id": media_id}
    url = f"{PUBLISH_URL}?access_token={access_token}"
    return _request_json(url, method="POST", payload=payload)


def main():
    parser = argparse.ArgumentParser(description="Publish WeChat OA article")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--app-secret", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--html-file", required=True)
    parser.add_argument("--thumb-media-id", required=True)
    parser.add_argument("--author", default="")
    parser.add_argument("--source-url", default="")
    parser.add_argument("--draft-only", action="store_true")
    args = parser.parse_args()

    try:
        html = open(args.html_file, "r", encoding="utf-8").read().strip()
    except FileNotFoundError:
        print(json.dumps({"error": "html file not found"}, ensure_ascii=False))
        return 2

    token = _get_access_token(args.app_id, args.app_secret)
    draft = _draft_add(
        token,
        args.title,
        html,
        args.thumb_media_id,
        author=args.author,
        source_url=args.source_url,
    )
    if "media_id" not in draft:
        print(json.dumps({"error": "draft_add failed", "details": draft}, ensure_ascii=False))
        return 3

    if args.draft_only:
        print(json.dumps({"draft": draft, "publish": None}, ensure_ascii=False, indent=2))
        return 0

    publish = _publish(token, draft["media_id"])
    print(json.dumps({"draft": draft, "publish": publish}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
