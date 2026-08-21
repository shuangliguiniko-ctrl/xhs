# New XHS Research 标准 Skill 安装指南

压缩包根目录直接包含 `SKILL.md`。完整保留 `agents/`、`scripts/`、`references/` 和 `assets/`，并把目录命名为 `new-xhs-research`。

## 自动安装

Codex 全局安装：

```bash
python3 scripts/install_skill.py --codex --deps ui
```

OpenCode 项目级安装：

```bash
python3 scripts/install_skill.py --opencode-project /目标项目 --deps ui
```

OpenCode 全局安装：

```bash
python3 scripts/install_skill.py --opencode-global --deps ui
```

兼容 `.agents/skills` 的项目安装：

```bash
python3 scripts/install_skill.py --agents-project /目标项目 --deps ui
```

安装器不会静默覆盖同名 Skill。升级时加入 `--force`，原目录会先备份。仅复制文件可使用 `--deps none`。

网络或证书环境无法下载依赖时，可复用已验证的本地虚拟环境：

```bash
python3 scripts/install_skill.py --codex --deps ui --existing-venv /已有/.venv
```

安装器会先验证所选依赖档位，再在安装目录创建 `.venv` 符号链接；不会复制或修改原环境。

## 依赖档位

- Python 3.11–3.14。
- `--deps core`：清洗、统计、快速主题、证据、洞察和 HTML 报告。
- `--deps ui`：核心能力加 Streamlit 和 Plotly，推荐用于双模式完整安装。
- `--deps semantic`：核心能力加 BERTopic、句向量与聚类扩展；模型下载必须另行授权。

企业镜像可加入 `--index-url` 与 `--cert`。已有 Python 环境可加入 `--system-site-packages`。

## 手工安装目录

- Codex：`~/.codex/skills/new-xhs-research/`
- OpenCode 项目：`项目/.opencode/skills/new-xhs-research/`
- OpenCode 全局：`~/.config/opencode/skills/new-xhs-research/`
- Agent 兼容项目：`项目/.agents/skills/new-xhs-research/`

标准结构：

```text
new-xhs-research/
├── SKILL.md
├── INSTALL.md
├── agents/openai.yaml
├── scripts/
│   ├── launch.py
│   ├── install_skill.py
│   ├── verify_skill.py
│   └── runtime/
├── references/
│   └── skills/*/SKILL.md
└── assets/
    ├── config/
    ├── examples/
    └── templates/
```

## 验证

```bash
python3 scripts/verify_skill.py --skill-dir /安装位置/new-xhs-research --full
```

验证本机 MediaCrawler：

```bash
python3 scripts/verify_skill.py \
  --skill-dir /安装位置/new-xhs-research \
  --mediacrawler /本机/MediaCrawler \
  --full
```

运行能力诊断：

```bash
python3 scripts/launch.py diagnose
python3 scripts/launch.py ui
```

## 外部采集组件边界

BrowserAct 由独立 Skill 和 CLI 提供；首次操作前必须加载其 Core 规范。MediaCrawler 不在包内二次分发，必须自行获取并接受其许可证。工具存在不等于小红书登录态有效，实时采集仍需授权会话和平台可访问性。

安装包不包含 Cookie、Token、登录态、API Key、原始研究数据或生成报告。不得绕过验证码、访问控制、频率限制或平台规则。
