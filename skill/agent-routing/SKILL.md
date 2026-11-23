---
name: agent-routing
description: 把任务拆给 Claude、Codex CLI、agy（Gemini）多个 agent 并行或串行完成。用户说“分给几个 agent / 让 codex 或 gemini 做 / 多模型分工 / 安排 agent”时使用，或任务明显包含整仓长文阅读 + 代码实现 + 独立审查多个阶段时使用。适用于 ~/Workspace 下所有项目。
---

# 多 Agent 调度

规则全文在 `~/Workspace/_agents/ROUTING.md`，开始前先读它，再读当前项目的 `AGENTS.md` / `CLAUDE.md`。项目规则优先，比如远端服务器授权、禁止事项、汇报口径。

## 步骤

1. **判断要不要拆。** 几次工具调用就能完成的事直接做，不派 agent。
2. **拆任务。** 按 ROUTING.md 的“任务类型 → 模型”表给每个子任务定 tool、model、effort、mode。写代码类任务按标准流水线：契约 → 代码地图 → 实现 → 审查 + 一致性核对 → 收口。契约和收口由你自己做，不写成卡。
3. **写任务卡。** 放到项目的 `.agent-runs/cards/<id>.md`，可以用 `python3 ~/Workspace/_agents/dispatch.py new <路径> --id <id>` 生成。每张卡必须写明：
   - `inputs`：具体文件或目录，不写“相关文件”
   - `output`：一个文件路径，正文写清交付物的章节和表格结构
   - `depends`：前置卡
   - 正文：目标、要求、验收标准。要可以独立执行，不能依赖本对话的上下文
4. **空跑并给用户看分工。** 运行 `dispatch.py run <卡...> --dry-run`，确认命令和 prompt 正确。然后给用户一张表：编号、工具、模型/effort、模式、输入、输出、依赖。第一次派发前等用户确认；用户已经明确说“直接跑”时可以不等。
5. **派发。** 运行时间可能超过 2 分钟的用 Bash 后台运行，不轮询，等完成通知。
   - 有依赖关系的卡按顺序传给同一个 `run`
   - 互不依赖、只读的卡用 `--parallel`
   - 同一组文件同一时间只派一个写手
6. **验收。** 读每张卡的交付物和 `.agent-runs/*.json`，确认退出码为 0、交付物存在。对 write 卡看 worktree 的 `git diff`，自己跑项目要求的检查。agent 的报告只当线索，你确认过才算数。
7. **收口。** 在 worktree 分支上审过之后再合并，提交按项目约定进行。按项目规则写 journal、更新 handoff。向用户汇报时写清每张卡的结论、哪些通过了你的验证、哪些没有。

## 注意

- 失败先看对应的 `.agent-runs/*.stderr.txt`，再检查 json 日志里的 `output_exists`。同一张卡失败一次后，先改 prompt 或升一档模型，不要原样重试。
- 不要把凭据、`.env`、私人数据写进任务卡。
- `ultra`、`max` 档和 Codex 的 `gpt-6.2-*` xhigh 成本高，只用于表里标明的场景。

## agy 的权限坑（无头模式）

- agy 在 `-p` 无头模式下默认权限策略是 `request-review`。不在白名单里的 shell 命令无法弹窗确认，会被自动拒绝，整次运行没有输出：退出码是 0，但交付物不存在，stderr 里有 `auto-denied`。
- `dispatch.py` 给 read 卡自动挂上会话级白名单（`--settings templates/agy-readonly-settings.json`）。不改用户的全局 agy 设置，也不用 `--dangerously-skip-permissions`。
- 写 agy 任务卡时，要在卡里注明只能用白名单里的命令（cd、pwd、ls、cat、head、tail、wc、grep、shasum、sha256sum、git status、git rev-parse），避免 `find`、`sed`、`python`、`$(...)` 和反引号，这些会触发精确匹配然后被拒。`rg` 和 `git diff/log/show` 被明确拒绝：它们带 `--pre`、`--output`、`--ext-diff`、`--textconv` 等参数能执行外部程序或写文件，而白名单只按命令前缀匹配，拦不住参数。看历史或 diff 的活交给 Codex 只读卡或由 Claude 自己做。新增命令前先确认它没有能执行命令或写文件的参数，再加进 `templates/agy-readonly-settings.json`；白名单只管命令名、不管路径，cwd 之外的文件仍可被读到。
- agy 卡失败时先看 `.agent-runs/*.stderr.txt`，再检查 `output_exists`。
- agy 的 write 模式（`accept-edits`）在无头状态下跑 shell 命令同样会被拒；write 卡只适合不需要 shell 命令的改动。
