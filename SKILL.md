---
name: x-ai-trends-digest
description: Fetch and summarize AI/LLM热点 into a PM-focused daily digest from X API, account RSS mirrors, or RSS/Atom sources. Use when you need to collect AI大模型热点, run the bundled fetch script in keyword/account/feed mode, format results into Chinese with the required labeled lines (内容概要/AI PM关注点/如何设计/市场反馈/标签/评注), or publish to WeChat Official Account via draft/add and freepublish/submit (requires AppID/AppSecret and thumb_media_id).
---

# X AI Trends Digest

## Overview
Enable a daily AI/LLM热点 brief by calling the bundled script, summarizing results, and optionally publishing as a WeChat Official Account article.

## Workflow

### 1. Choose data source
- **RSS/Atom 源模式（推荐）**：从 `references/feeds.txt` 读取源列表，稳定且无需 API。
- **账号模式**：从 `references/accounts.txt` 读取账号列表（依赖RSS镜像可用）。
- **关键词模式**：从 `references/keywords.txt` 读取关键词（需要 X API v2）。

### 2. Verify credentials (keyword mode only)
- If using keyword mode, check that `X_BEARER_TOKEN` is set.
- If missing, stop and respond with a short actionable message requesting the bearer token.

### 3. Fetch recent posts
- RSS/Atom 源模式（推荐）：
  `python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --mode feeds --feeds-file references/feeds.txt`
- 账号模式：
  `python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --mode accounts --accounts-file references/accounts.txt`
- 关键词模式：
  `python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --keywords-file references/keywords.txt`
- If the script output includes an `error`, surface a short actionable message and stop.

### 4. Summarize into the PM digest (new layout)
Use the daily-layout style with a bold title line and lettered lines. For each item:

**Title line (bold, with link):**
`1. 【重要】【产品视角】<a href="原文链接">标题</a>`

**No extra source line:**
- 不要另起一行写“原文：链接”，原文链接只放在标题上。


**Body lines (each on its own line, follow the standard template):**
Use `references/标准需求输入模版.md` as the canonical layout, including:
`a) 内容概要：` (两条分点)
`b) AI PM关注点：` (两条分点)
`c) 如何设计：` (两条分点)
`d) 市场反馈：` (两条分点，数字化指标优先)
`e) 标签：` (一条分点，仅保留大模型相关标签)
`f) 评注：` (两条分点，顶级AI PM视角)

**Keypoint highlighting (no extra line):**
- 在“内容概要 / AI PM关注点 / 如何设计 / 评注”中，选择 2–4 个关键短语，用黄色划线高亮。
- 高亮格式：`<span style="background-color:#FFF2CC;">关键短语</span>`

Keep output in Chinese. If fewer than 10 items are available, output only the available items.
Aim for ~100字 in a/b/c and f)评注 each, while keeping readable mobile length.

**Example: auto-generate using the standard template**
1) Load the template: `references/标准需求输入模版.md`
2) Fetch sources (feeds mode recommended):
   `python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --mode feeds --feeds-file references/feeds.txt`
3) For each item, fill the template sections (a–f) with:
   - Two bullets for 内容概要 / AI PM关注点 / 如何设计 / 市场反馈
   - One bullet for 标签
   - Two bullets for 评注 (top AI PM perspective)
4) Apply highlight markup: `<span style="background-color:#FFF2CC;">关键短语</span>`
5) Render HTML to `/tmp/wechat_article.html` and open it for review.

**Default rules (if not specified):**
- **重要性**：官方大厂发布/合作/新功能/模型/基准 → `【重要】`；其余为 `【关注】`。
- **视角**：按关键词选择其一（优先级从上到下）：
  1) 产品视角：`发布/功能/应用/合作/生态/体验`
  2) 市场视角：`融资/商业/增长/客户/市场`
  3) 技术视角：默认（模型/架构/训练/推理/系统/工程等）
  4) 工具视角：`API/SDK/插件/开源库/框架/工具`
  5) 研究视角：`arXiv/benchmark/评测/论文/研究`

### 5. Publish to WeChat Official Account (optional)
1) Generate cover image (optional):
`python3 scripts/generate_wechat_cover.py --title "YYYY-MM-DD AI热点日报" --out /tmp/cover.jpg`

2) Upload cover to get `thumb_media_id`:
`python3 scripts/upload_wechat_material.py --app-id APPID --app-secret APPSECRET --type thumb --file /tmp/cover.jpg`

3) Publish article:
`python3 scripts/publish_wechat_article.py --app-id APPID --app-secret APPSECRET --title "YYYY-MM-DD AI热点日报" --html-file /path/to/content.html --thumb-media-id MEDIA_ID`

Draft-only (no publish):
`python3 scripts/publish_wechat_article.py --app-id APPID --app-secret APPSECRET --title "YYYY-MM-DD AI热点日报" --html-file /path/to/content.html --thumb-media-id MEDIA_ID --draft-only`

See `references/wechat_publish.md` for API details.

## Output rules
- **关键词模式**：保持脚本的互动排序。
- **账号模式**：保持脚本的时间排序（近期优先）。
- **RSS/Atom 源模式**：权重排序（Karpathy > 官方公司源 > 其他 > 论文），同权重按时间排序。
- Keep each item concise (<=100字 per line where possible).
- Titles should be bold with hyperlinks in HTML output.

## Resources
- `scripts/fetch_x_trends.py`: Fetches recent posts, ranks and outputs JSON.
- `scripts/publish_wechat_article.py`: Publishes HTML content via draft/add and freepublish/submit.
- `scripts/upload_wechat_material.py`: Uploads permanent material to get thumb_media_id.
- `scripts/generate_wechat_cover.py`: Generates a default cover image.
- `references/keywords.txt`: Default keyword list (editable).
- `references/accounts.txt`: Account list (editable; use exact handles).
- `references/feeds.txt`: RSS/Atom source list (editable; supports `youtube:@handle`).
- `references/exclude_keywords.txt`: Exclude keywords (title match).
- `references/标准需求输入模版.md`: Canonical input/output template for this skill.
- `references/wechat_publish.md`: WeChat API notes (from user-provided docs).
- `references/wechat_thumb_media_id.txt`: Store permanent thumb_media_id.
