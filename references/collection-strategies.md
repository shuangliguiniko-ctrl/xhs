# 双模式与采集决策

## 操作模式

| 模式 | 负责交互 | 后续入口 | 适用情况 |
|---|---|---|---|
| AI | 当前 AI 会话 | `diagnose` 后逐段确认并执行 CLI | 需要解释、动态判断、BrowserAct 协同或定制研究 |
| UI | Streamlit 页面 | `diagnose` 后运行 `ui` | 需要表单、文件上传、可视化预览与单页操作 |

第一问只确认模式。AI 模式继续会话式五步流程；UI 模式只在环境通过后启动页面，避免双重询问。

## 采集入口判定

| 条件 | BrowserAct | MediaCrawler | Hybrid | Import |
|---|---:|---:|---:|---:|
| 页面需要登录或动态交互 | 首选 | 可用但依赖登录 | 可用 | 不适用 |
| 多关键词批量与评论 | 有限 | 首选 | 首选 | 取决于文件 |
| 页面级事实核验 | 首选 | 需抽检 | 首选 | 仅验证文件 |
| 无实时访问权限 | 不可用 | 不可用 | 不可用 | 首选 |
| 可复现实验 | 保存复合 JSONL | 保存原始 JSONL | 保存两源与合并审计 | 保存文件哈希 |

## BrowserAct 数据契约

保存 JSON 或 JSONL；每行包含 `keyword`、`collected_at`、`note` 和可选 `comments`。`note` 至少包含 `note_id` 以及 `title` 或 `content`。评论至少包含 `content`，优先保留 `comment_id`。删除 Cookie、Token、签名参数与作者直接标识。

## Hybrid 合并规则

1. 分别保留 BrowserAct 与 MediaCrawler 的原始文件。
2. 先按 `source_platform + content_id + record_type` 合并。
3. 缺少 ID 时仅使用内容哈希生成稳定 ID，不使用作者名。
4. 冲突字段优先保留非空值；记录 `source_adapters`。
5. 分别报告两源原始数、重叠数、合并后数和失败数。

## 就绪状态

- BrowserAct：CLI 存在只代表工具可调用；实时采集还需可用浏览器、当前授权会话与平台可访问性。
- MediaCrawler：`main.py` 与解释器存在只代表代码就绪；实时采集还需许可证接受、有效登录态和平台可访问性。
- Hybrid：BrowserAct 持久化输入就绪，且 MediaCrawler 实时或持久化输入就绪。
- Import：文件存在、扩展名受支持、编码和结构可读取。
