#!/usr/bin/env python3
"""Generate a WeChat cover image (thumb) suitable for upload.

Default size: 900x383 (2.35:1). Output JPG <= 64KB by default.

Usage:
  python3 scripts/generate_wechat_cover.py \
    --title "2026-02-04 AI热点日报" \
    --out /tmp/cover.jpg
"""

import argparse
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def main():
    parser = argparse.ArgumentParser(description="Generate WeChat cover image")
    parser.add_argument("--title", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--height", type=int, default=383)
    parser.add_argument("--quality", type=int, default=80)
    args = parser.parse_args()

    title = args.title or f"{datetime.now().strftime('%Y-%m-%d')} AI热点日报"

    img = Image.new("RGB", (args.width, args.height), "white")
    draw = ImageDraw.Draw(img)

    font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    title_font = ImageFont.truetype(font_path, 42)
    subtitle_font = ImageFont.truetype(font_path, 26)

    draw.rectangle([(0, 0), (args.width, args.height)], fill=(245, 247, 250))
    draw.rectangle([(40, 40), (args.width - 40, args.height - 40)], fill=(255, 255, 255))

    x = 70
    y = 90
    draw.text((x, y), title, fill=(20, 20, 20), font=title_font)
    y += title_font.size + 20
    draw.text((x, y), "大模型/AI 热点速览", fill=(90, 90, 90), font=subtitle_font)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=args.quality, optimize=True)


if __name__ == "__main__":
    main()
