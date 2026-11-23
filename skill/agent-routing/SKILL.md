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
- 白名单按命令前缀匹配，不是沙箱：deny 里补了 `rg --pre`、`git diff --output`、`--ext-diff`、`--textconv`、`git -c` 和常见凭据路径，但按参数匹配并不完备。读卡里不要放敏感目录；根本办法是把 read 模式的 agy 放进只读沙箱。
- 派发新会话或子 agent 时，effort 要显式指定并核对实际生效值；遇到“effort 不能超过当前窗口”的提示，不要想当然，以实际报错为准。
- 每张 agy 卡的正文第一条都要写：“只用读文件的工具读取 inputs 里的文件（图片直接读取查看），不要执行 shell 命令、不要列目录。”inputs 逐个列文件，不列目录。2026-11-23 实验三的核对卡漏了这句，第一次运行 73 秒就被拒了，没有任何产出，dispatch 却打印“失败 exit=0”。
- agy 无头模式也会拒绝读取 cwd 之外的文件：stderr 显示 `"read_file" permission ... auto-denied`。inputs 里不要写 `../` 路径，要读的文件（包括截图）先复制到卡的 cwd 下，例如 `.agent-runs/shots/`。
- 只看截图、扫描件的核对卡用 `gemini-4-neon-high`，不要用 Flash。

## 课程作业、非 git 目录、本地数据库（2026-11-23 数据库实验三的教训）

- 非 git 目录也能派卡：dispatch 会给 codex 自动加 `--skip-git-repo-check`。这时不要填 `worktree`，write 卡只允许新建或修改卡里点名的文件；收口时没有 `git diff`，由 Claude 直接读文件、自己编译运行来验收。
- Codex 的 `workspace-write` 沙箱连不上 Docker socket（colima），连本机容器数据库的验证可能做不了或只做了一部分。凡是要连本地数据库的卡，都以 Claude 收口时亲自跑的结果为准，Codex 报告里的“验证通过”只当线索。
- 卡里写清楚要模仿哪个现有文件的写法（例如“连接配置照 `../实验二/FinanceApp.java` 写成常量”）。不写的话，Codex 会按自己的习惯改成从环境变量读密码，和课程示例、往次实验的写法对不上，收口时还得再改。
- 测试库口令也不写进卡正文。写“连接信息见 `<项目里的说明文件>`”，并把那个文件列进 inputs。
- 课程作业同时遵守 `coursework-project-assistant`：agent 产出的代码和文字，Claude 要按老师手册的口径收口（术语、文件名、截图说明）；报告由 Claude 写，agy 只做“是否覆盖模板每一项、事实是否和代码及截图一致”的核对。
