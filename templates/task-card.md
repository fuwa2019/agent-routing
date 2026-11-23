---
id: T1
tool: agy                    # codex | agy | claude
model: gemini-4-neon-xhigh   # 与 `python3 dispatch.py models` 列出的 id 一致
effort:                      # codex/claude 用：low|medium|high|xhigh|max；agy 的 Gemini 已在模型名里，可留空
mode: read                   # read（只读）| write（可改文件）
cwd: .                       # 相对任务卡所在目录，或绝对路径
worktree:                    # 可选：codex 写代码时的独立 worktree 路径（相对 cwd），不存在会自动创建
inputs: AGENTS.md, docs/     # 逗号分隔，相对 cwd
output: .agent-runs/out/T1.md  # 交付物路径（相对 cwd），保存最后一条消息
depends:                     # 可选：逗号分隔的前置任务卡路径；其 output 不存在则拒绝运行
timeout: 3600                # 秒
---

## 目标

一句话说清要什么。

## 具体要求

- 要覆盖哪些点
- 每条结论带 `file:line`

## 交付物格式

- 章节结构 / 表格列
