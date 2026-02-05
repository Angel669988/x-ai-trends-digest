# x-ai-trends-digest (Public Skill)

**用途**  
每日抓取 AI/LLM 热点，并按产品经理视角输出结构化日报（支持 HTML 输出、微信草稿、PushPlus 推送）。

**主要能力**
- RSS/官方源优先（无需 X API）
- 结构化输出：内容概要 / AI PM关注点 / 如何设计 / 市场反馈 / 标签 / 评注
- 关键短语高亮支持（黄底）
- 可输出 HTML 适配移动端
- 支持微信草稿接口（需 AppID/AppSecret + 公众平台权限）
- 支持 PushPlus 推送（需 token）

**目录结构**
```
SKILL.md
agents/
references/
scripts/
```

## 如何安装 Skill

**方式 A（推荐）**  
将整个 `x-ai-trends-digest` 目录拷贝到你的 `$CODEX_HOME/skills/` 下：
```
$CODEX_HOME/skills/x-ai-trends-digest/
```

**方式 B（skill-installer）**  
如果你已配置 skill-installer，可直接从仓库安装（将下面地址替换为你的仓库地址）：
```
<REPO_URL>
```

## 快速开始
1) 拉取源（RSS/官方源）：
```
python3 scripts/fetch_x_trends.py --since-hours 24 --limit 10 --mode feeds --feeds-file references/feeds.txt
```

2) 按模板生成 HTML 并预览：  
输出到 `/tmp/wechat_article.html`

## 配置
- X API：`X_BEARER_TOKEN`
- 微信：`APPID / APPSECRET / thumb_media_id`
- PushPlus：`token`

## 注意事项
- 任何密钥不要写入仓库
- 微信草稿发布需要公众号认证与 IP 白名单
- PushPlus 若 DNS 异常可用 `--resolve` 直连
