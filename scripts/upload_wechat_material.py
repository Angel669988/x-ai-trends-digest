#!/usr/bin/env python3
"""Upload permanent material to WeChat Official Account.

Usage:
  python3 scripts/upload_wechat_material.py \
    --app-id APPID \
    --app-secret APPSECRET \
    --type thumb \
    --file /path/to/cover.jpg

Returns JSON with media_id and url (if provided by WeChat).
"""

import argparse
import json
import mimetypes
import os
import random
import string
import urllib.parse
import urllib.request

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"


def _request_json(url, method="GET", payload=None, headers=None):
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _get_access_token(app_id, app_secret):
    qs = urllib.parse.urlencode(
        {"grant_type": "client_credential", "appid": app_id, "secret": app_secret}
    )
    url = f"{TOKEN_URL}?{qs}"
    data = _request_json(url)
    if "access_token" not in data:
        raise RuntimeError(f"Failed to get access_token: {data}")
    return data["access_token"]


def _multipart_form(file_field, file_path, extra_fields=None):
    boundary = "----WebKitFormBoundary" + "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(16)
    )
    crlf = "\r\n"
    parts = []

    if extra_fields:
        for key, value in extra_fields.items():
            parts.append(f"--{boundary}")
            parts.append(f'Content-Disposition: form-data; name="{key}"')
            parts.append("")
            parts.append(value)

    filename = os.path.basename(file_path)
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    parts.append(f"--{boundary}")
    parts.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"'
    )
    parts.append(f"Content-Type: {mime}")
    parts.append("")

    body_pre = crlf.join(parts).encode("utf-8") + crlf.encode("utf-8")
    with open(file_path, "rb") as f:
        file_bytes = f.read()
    body_post = (crlf + f"--{boundary}--" + crlf).encode("utf-8")

    body = body_pre + file_bytes + body_post
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _upload_material(access_token, media_type, file_path):
    qs = urllib.parse.urlencode({"access_token": access_token, "type": media_type})
    url = f"{UPLOAD_URL}?{qs}"
    body, content_type = _multipart_form("media", file_path)
    headers = {"Content-Type": content_type}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read().decode("utf-8")
    return json.loads(data)


def main():
    parser = argparse.ArgumentParser(description="Upload WeChat permanent material")
    parser.add_argument("--app-id", required=True)
    parser.add_argument("--app-secret", required=True)
    parser.add_argument("--type", default="thumb", choices=["image", "voice", "video", "thumb"])
    parser.add_argument("--file", required=True)
    args = parser.parse_args()

    if not os.path.isfile(args.file):
        print(json.dumps({"error": "file not found"}, ensure_ascii=False))
        return 2

    token = _get_access_token(args.app_id, args.app_secret)
    result = _upload_material(token, args.type, args.file)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
