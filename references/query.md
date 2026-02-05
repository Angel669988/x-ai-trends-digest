# Data Source Patterns

## 1) 关键词模式（需要X API）
- 关键词组合：("AI" OR "LLM" OR "大模型" OR ...)
- 过滤：`-is:retweet -is:reply`
- 时间窗口：`start_time` = UTC now - `--since-hours`

## 2) 账号模式（无需X API，但依赖RSS镜像可用性）
- 从 `accounts.txt` 读取账号列表
- 通过公开RSS抓取（优先 nitter RSS，失败时走 jina.ai 的镜像）
- 仅按时间排序，不含互动数据

## 3) RSS/Atom 源模式（无需X API）
- 从 `feeds.txt` 读取RSS/Atom源
- 支持 `youtube:@handle` 形式（自动解析 YouTube 频道 RSS）
- 聚合多源内容，按时间排序

你可以通过编辑 `accounts.txt` 或 `feeds.txt` 来调整监控对象。
