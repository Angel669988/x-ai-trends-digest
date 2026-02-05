#!/usr/bin/env python3
"""Fetch recent AI/LLM trends from X API v2, public account feeds, or RSS sources.

Usage:
  python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --keywords-file references/keywords.txt
  python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --mode accounts --accounts-file references/accounts.txt
  python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --mode feeds --feeds-file references/feeds.txt

Requires (keywords mode):
  - X_BEARER_TOKEN environment variable (X API v2 bearer token)
"""

import argparse
import json
import os
import re
import sys
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

API_URL = "https://api.x.com/2/tweets/search/recent"
NITTER_RSS = "https://nitter.net/{username}/rss"
NITTER_RSS_FALLBACK = "https://r.jina.ai/http://r.jina.ai/https://nitter.net/{username}/rss"


def _json_out(payload):
    json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def _load_keywords(path):
    keywords = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                keywords.append(line)
    except FileNotFoundError:
        return []
    return keywords


def _load_exclude_keywords(path):
    return [k.lower() for k in _load_keywords(path)]


def _load_accounts(path):
    accounts = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                accounts.append(raw)
    except FileNotFoundError:
        return []
    return accounts


def _load_feeds(path):
    feeds = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                if "|" in raw:
                    label, url = [part.strip() for part in raw.split("|", 1)]
                else:
                    label, url = "", raw
                feeds.append({"label": label, "url": url})
    except FileNotFoundError:
        return []
    return feeds


def _normalize_account(raw):
    return raw.strip().lstrip("@").replace(" ", "")


def _quote_keyword(keyword):
    cleaned = keyword.replace('"', "").strip()
    if not cleaned:
        return ""
    return f'"{cleaned}"'


def _build_query(keywords):
    quoted = [_quote_keyword(k) for k in keywords if k.strip()]
    quoted = [q for q in quoted if q]
    if not quoted:
        return ""
    clause = " OR ".join(quoted)
    return f"({clause}) -is:retweet -is:reply"


def _start_time_iso(since_hours):
    start = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    return start.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fetch_url(url, timeout=8):
    request = urllib.request.Request(url, headers={"User-Agent": "x-ai-trends-digest/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except Exception:
        return _fetch_url_curl(url, timeout=timeout)


def _fetch_url_curl(url, timeout=8):
    result = subprocess.run(
        ["curl", "-L", "-sS", "--fail", "--max-time", str(timeout), url],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"curl failed with code {result.returncode}")
    return result.stdout


def _fetch_recent(query, start_time, bearer_token, max_results):
    params = {
        "query": query,
        "max_results": str(max_results),
        "tweet.fields": "created_at,public_metrics,lang",
        "expansions": "author_id",
        "user.fields": "username,name",
        "start_time": start_time,
    }
    url = f"{API_URL}?{urllib.parse.urlencode(params)}"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "x-ai-trends-digest/1.0",
    }
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def _build_items(payload):
    users = {u.get("id"): u for u in payload.get("includes", {}).get("users", [])}
    items = []
    for tweet in payload.get("data", []) or []:
        metrics = tweet.get("public_metrics") or {}
        engagement = (
            metrics.get("like_count", 0)
            + metrics.get("retweet_count", 0)
            + metrics.get("reply_count", 0)
            + metrics.get("quote_count", 0)
        )
        author_id = tweet.get("author_id")
        user = users.get(author_id, {})
        username = user.get("username")
        url = (
            f"https://x.com/{username}/status/{tweet.get('id')}"
            if username
            else f"https://x.com/i/web/status/{tweet.get('id')}"
        )
        items.append(
            {
                "id": tweet.get("id"),
                "text": tweet.get("text"),
                "author": user.get("name") or username or "unknown",
                "username": username,
                "url": url,
                "created_at": tweet.get("created_at"),
                "metrics": metrics,
                "engagement_score": engagement,
            }
        )
    items.sort(key=lambda i: (i["engagement_score"], i.get("created_at") or ""), reverse=True)
    return items


def _strip_tag(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _iter_children(parent, name):
    for child in list(parent):
        if _strip_tag(child.tag) == name:
            yield child


def _child_text(parent, name):
    for child in _iter_children(parent, name):
        if child.text:
            return child.text.strip()
    return ""


def _parse_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        iso = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def _parse_rss_items(xml_text, source_label):
    items = []
    root = ElementTree.fromstring(xml_text)
    channel = None
    for child in _iter_children(root, "channel"):
        channel = child
        break
    if channel is None:
        return items
    for item in _iter_children(channel, "item"):
        title = _child_text(item, "title")
        link = _child_text(item, "link")
        pub_date = _child_text(item, "pubDate")
        created_at = _parse_date(pub_date)
        items.append(
            {
                "id": link or title,
                "text": title,
                "author": source_label,
                "username": None,
                "url": link,
                "created_at": created_at,
                "metrics": {},
                "engagement_score": 0,
                "source": source_label,
            }
        )
    return items


def _parse_atom_items(xml_text, source_label):
    items = []
    root = ElementTree.fromstring(xml_text)
    for entry in _iter_children(root, "entry"):
        title = _child_text(entry, "title")
        link = ""
        for link_node in _iter_children(entry, "link"):
            rel = link_node.attrib.get("rel", "alternate")
            href = link_node.attrib.get("href") or ""
            if rel == "alternate" and href:
                link = href
                break
            if not link and href:
                link = href
        updated = _child_text(entry, "updated")
        published = _child_text(entry, "published")
        created_at = _parse_date(updated or published)
        items.append(
            {
                "id": link or title,
                "text": title,
                "author": source_label,
                "username": None,
                "url": link,
                "created_at": created_at,
                "metrics": {},
                "engagement_score": 0,
                "source": source_label,
            }
        )
    return items


def _parse_feed(xml_text, source_label):
    root = ElementTree.fromstring(xml_text)
    tag = _strip_tag(root.tag)
    if tag == "rss" or any(_strip_tag(c.tag) == "channel" for c in list(root)):
        return _parse_rss_items(xml_text, source_label)
    if tag == "feed":
        return _parse_atom_items(xml_text, source_label)
    return []


def _fetch_account_feed(username, timeout):
    url = NITTER_RSS.format(username=username)
    try:
        body = _fetch_url(url, timeout=timeout)
        return _parse_rss_items(body, username)
    except Exception:
        fallback = NITTER_RSS_FALLBACK.format(username=username)
        body = _fetch_url(fallback, timeout=timeout)
        return _parse_rss_items(body, username)


def _resolve_youtube_feed(url, timeout):
    target = url.strip()
    if target.startswith("youtube:"):
        target = target.split(":", 1)[1].strip()
    if target.startswith("yt:"):
        target = target.split(":", 1)[1].strip()
    if target.startswith("http"):
        if "youtube.com/feeds/videos.xml" in target:
            return target
        if "youtube.com/@" in target:
            target = target.split("youtube.com/", 1)[1].strip()
    if target.startswith("@"):
        handle_url = f"https://www.youtube.com/{target}"
        html = _fetch_url(handle_url, timeout=timeout)
        match = re.search(r'"channelId":"(UC[^"]+)"', html)
        if not match:
            match = re.search(r'"browseId":"(UC[^"]+)"', html)
        if not match:
            mirror_url = f"https://r.jina.ai/http://r.jina.ai/{handle_url}"
            html = _fetch_url(mirror_url, timeout=timeout)
            match = re.search(r'"channelId":"(UC[^"]+)"', html) or re.search(
                r'"browseId":"(UC[^"]+)"', html
            )
        if not match:
            raise ValueError("Unable to resolve YouTube channel id from handle.")
        channel_id = match.group(1)
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    if target.startswith("UC"):
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={target}"
    raise ValueError("Unsupported YouTube feed format.")


def _fetch_feed(feed, timeout):
    label = feed.get("label") or feed.get("url")
    url = feed.get("url")
    if url and (url.startswith("youtube:") or url.startswith("yt:") or "youtube.com/@" in url):
        url = _resolve_youtube_feed(url, timeout=timeout)
    body = _fetch_url(url, timeout=timeout)
    return _parse_feed(body, label), label


def _filter_since(items, since_hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    filtered = []
    for item in items:
        created_at = item.get("created_at")
        if not created_at:
            continue
        try:
            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            continue
        if created_dt >= cutoff:
            filtered.append(item)
    return filtered


def _dedupe(items):
    seen = set()
    deduped = []
    for item in items:
        key = item.get("url") or item.get("id") or item.get("text")
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _filter_excluded(items, exclude_keywords):
    if not exclude_keywords:
        return items
    filtered = []
    for item in items:
        text = (item.get("text") or "").lower()
        if any(k in text for k in exclude_keywords):
            continue
        filtered.append(item)
    return filtered


def _source_weight(item):
    source = (item.get("source") or item.get("author") or "").lower()
    if "karpathy" in source:
        return 3
    official_keywords = (
        "openai",
        "anthropic",
        "deepmind",
        "google",
        "microsoft",
        "cohere",
        "hugging face",
    )
    if any(key in source for key in official_keywords):
        return 2
    if "arxiv" in source:
        return 0
    return 1


def main():
    parser = argparse.ArgumentParser(description="Fetch recent AI/LLM trends")
    parser.add_argument("--since-hours", type=int, default=24, help="Lookback window in hours")
    parser.add_argument("--limit", type=int, default=10, help="Number of items to return")
    parser.add_argument(
        "--keywords-file",
        default="references/keywords.txt",
        help="Path to keyword list file",
    )
    parser.add_argument(
        "--accounts-file",
        default="references/accounts.txt",
        help="Path to account list file",
    )
    parser.add_argument(
        "--feeds-file",
        default="references/feeds.txt",
        help="Path to RSS/Atom feed list file",
    )
    parser.add_argument(
        "--exclude-keywords-file",
        default="references/exclude_keywords.txt",
        help="Path to exclude keyword list file",
    )
    parser.add_argument(
        "--feed-timeout",
        type=int,
        default=8,
        help="Per-feed fetch timeout in seconds (RSS/Atom or account RSS)",
    )
    parser.add_argument(
        "--max-feeds",
        type=int,
        default=0,
        help="Optional limit on number of feeds to fetch (0 = no limit)",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "keywords", "accounts", "feeds"],
        default="auto",
        help="Fetch mode: keywords (X API), accounts (public RSS), feeds (RSS/Atom), or auto",
    )
    args = parser.parse_args()

    mode = args.mode
    token = os.environ.get("X_BEARER_TOKEN")

    if mode in ("auto", "keywords") and token:
        keywords = _load_keywords(args.keywords_file)
        query = _build_query(keywords)
        if not query:
            _json_out(
                {
                    "error": "Keyword list is empty. Add keywords to references/keywords.txt.",
                }
            )
            return 2

        start_time = _start_time_iso(args.since_hours)
        max_results = max(50, args.limit * 5)
        max_results = min(100, max_results)

        try:
            payload = _fetch_recent(query, start_time, token, max_results)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            _json_out(
                {
                    "error": f"X API request failed with status {exc.code}.",
                    "details": body,
                }
            )
            return 3
        except urllib.error.URLError as exc:
            _json_out({"error": f"Network error contacting X API: {exc.reason}."})
            return 3
        except TimeoutError:
            _json_out({"error": "Timed out contacting X API."})
            return 3

        if payload.get("errors"):
            _json_out({"error": "X API returned errors.", "details": payload.get("errors")})
            return 3

        items = _build_items(payload)
        limited = items[: max(args.limit, 0)]

        output = {
            "mode": "keywords",
            "query": query,
            "start_time": start_time,
            "limit": args.limit,
            "fetched": len(items),
            "items": limited,
        }
        if not limited:
            output["notice"] = "No results returned for this time window."

        _json_out(output)
        return 0

    if mode == "accounts":
        accounts = _load_accounts(args.accounts_file)
        if not accounts:
            _json_out(
                {
                    "error": "Account list is empty. Add handles to references/accounts.txt.",
                }
            )
            return 2

        normalized = [_normalize_account(a) for a in accounts]
        normalized = [a for a in normalized if a]
        if not normalized:
            _json_out(
                {
                    "error": "Account list contains no valid handles.",
                }
            )
            return 2

        items = []
        errors = []
        for handle in normalized:
            try:
                items.extend(_fetch_account_feed(handle, timeout=args.feed_timeout))
            except Exception as exc:
                errors.append({"account": handle, "error": str(exc)})

        exclude_keywords = _load_exclude_keywords(args.exclude_keywords_file)
        items = _filter_excluded(items, exclude_keywords)
        items = _filter_since(items, args.since_hours)
        items = _dedupe(items)
        items.sort(key=lambda i: (i.get("created_at") or ""), reverse=True)
        limited = items[: max(args.limit, 0)]

        output = {
            "mode": "accounts",
            "accounts": normalized,
            "limit": args.limit,
            "fetched": len(items),
            "items": limited,
        }
        if errors:
            output["errors"] = errors
        if not limited:
            output["notice"] = "No results returned for this time window."

        _json_out(output)
        return 0

    feeds = _load_feeds(args.feeds_file)
    if not feeds:
        _json_out(
            {
                "error": "Feed list is empty. Add RSS/Atom feeds to references/feeds.txt.",
            }
        )
        return 2

    items = []
    errors = []
    used_labels = []
    if args.max_feeds and args.max_feeds > 0:
        feeds = feeds[: args.max_feeds]
    for feed in feeds:
        url = feed.get("url")
        if not url:
            continue
        try:
            feed_items, label = _fetch_feed(feed, timeout=args.feed_timeout)
            used_labels.append(label)
            items.extend(feed_items)
        except Exception as exc:
            errors.append({"feed": url, "error": str(exc)})

    exclude_keywords = _load_exclude_keywords(args.exclude_keywords_file)
    items = _filter_excluded(items, exclude_keywords)
    items = _filter_since(items, args.since_hours)
    items = _dedupe(items)
    items.sort(
        key=lambda i: (_source_weight(i), i.get("created_at") or ""),
        reverse=True,
    )
    limited = items[: max(args.limit, 0)]

    output = {
        "mode": "feeds",
        "feeds": used_labels,
        "limit": args.limit,
        "fetched": len(items),
        "items": limited,
    }
    if errors:
        output["errors"] = errors
    if not limited:
        output["notice"] = "No results returned for this time window."

    _json_out(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
