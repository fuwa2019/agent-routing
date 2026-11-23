# agent-routing：Claude Code 调度 Codex CLI 与 Gemini（agy）CLI

这个仓库是一套多 agent 分工方案：由 **Claude Code** 负责拆任务、写任务卡和最终收口；**Codex CLI** 负责在代码库里实现、调试和做对抗式审查；**agy（Gemini）CLI** 负责长上下文阅读、整仓代码地图和一致性核对。仓库里包括：

- 分工规则、任务类型到模型的对照表（[ROUTING.md](ROUTING.md)）
- 任务卡模板（[templates/task-card.md](templates/task-card.md)）
- 只用标准库的派发脚本，按任务卡调用 `codex exec` / `agy -p` / `claude -p`（[dispatch.py](dispatch.py)）
- 给 Claude Code 用的 skill（[skill/agent-routing/SKILL.md](skill/agent-routing/SKILL.md)）

## 依赖

- Python 3.9+（脚本只用标准库）
- 需要的 CLI，按要用到的装：
  - [Codex CLI](https://github.com/openai/codex)（命令 `codex`）
  - agy（Gemini）CLI（命令 `agy`）
  - Claude Code（命令 `claude`）
- Git（写代码类任务会用 `git worktree`）

## 安装

```bash
git clone https://github.com/fuwa2019/agent-routing.git ~/Workspace/_agents
```

把 skill 链到 Claude Code 的 skills 目录（mac / Linux）：

```bash
mkdir -p ~/.claude/skills
ln -s ~/Workspace/_agents/skill/agent-routing ~/.claude/skills/agent-routing
```

Windows PowerShell 用复制的方式：

```powershell
Copy-Item -Recurse "$HOME\Workspace\_agents\skill\agent-routing" "$HOME\.claude\skills\agent-routing"
```

## 用法示例

在 Claude Code 里说“把这件事分给几个 agent 做”，Claude 会按 skill 写任务卡、给你看分工表，确认后派发。也可以手动操作：

```bash
# 列出本机可用模型
python3 ~/Workspace/_agents/dispatch.py models

# 从模板生成任务卡
python3 ~/Workspace/_agents/dispatch.py new .agent-runs/cards/T1.md --id T1

# 空跑：只打印命令和 prompt，不真正调用
python3 ~/Workspace/_agents/dispatch.py run .agent-runs/cards/T1.md --dry-run

# 运行两张互不依赖、只读的卡
python3 ~/Workspace/_agents/dispatch.py run .agent-runs/cards/T1.md .agent-runs/cards/T2.md --parallel
```

任务卡的字段说明见 [templates/task-card.md](templates/task-card.md)。

## 关于模型 id

[ROUTING.md](ROUTING.md) 里的模型 id（如 `gpt-6.2-sol`、`gemini-4-neon-xhigh`）是作者本机的配置。使用者应先运行 `python3 dispatch.py models`，按它输出的 id 自行替换 ROUTING.md 和任务卡里的模型名。Codex 的模型目录可以通过环境变量 `CODEX_MODEL_CATALOG` 指定一个 json 文件，`models` 命令会读取它；未设置时回退到 codex 自带的说明。

## 约定

- 任务卡和产出放在项目的 `.agent-runs/` 下。脚本会把它写进该仓库本地的 `.git/info/exclude`，不进提交；需要留档的结论由 Claude 写进项目文档或 journal。
- 每次运行写一份 `.agent-runs/<时间>-<id>.json`（模型、effort、cwd、git HEAD、退出码、耗时）和对应的 stderr。
- `depends` 里前置卡的交付物不存在时拒绝运行；`--parallel` 最多允许一张 write 卡。
- Codex 写代码时填 `worktree`，脚本自动建 `agent/<id>` 分支的 worktree，主工作区不动；合并由 Claude 审过后做。
- agy 的 read 模式用 `--mode plan`，write 模式用 `--mode accept-edits`；Codex 对应 `read-only` / `workspace-write` 沙箱；Claude 对应 `plan` / `acceptEdits`。

## 验证记录

2026-11-23 mac 实测：
- `agy gemini-3.8-flash-low` 只读：通过
- `codex gpt-6.1-terra medium` 只读：通过
- Codex 写模式加自动 worktree：通过，主工作区未改，`.agent-runs/` 已加入 exclude
- `gpt-6-luna low`：没有调用工具，直接回复无法读取，所以杂活默认用 medium

## 许可

[MIT](LICENSE)
