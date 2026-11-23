# 多 Agent 分工规则（Workspace 通用）

适用于 `~/Workspace` 下所有项目。各项目的 `AGENTS.md` / `CLAUDE.md` 优先于本文件：本文件管谁来干、用什么模型，项目文件管能干什么、不能干什么。

## 角色

| 工具 | 定位 | 交给它 | 不交给它 |
| --- | --- | --- | --- |
| **Claude Code**（Opus 5.5） | 调度者与收口人 | 澄清需求、拆任务、写接口契约和任务卡；守项目规则；整合和验证产出；中文文档、journal、提交 | 大段实现代码、整仓逐行阅读 |
| **Codex CLI**（GPT-6.x） | 执行者与审查者 | 在现有代码库里实现、重构、写测试、调试、跑最小验证；对抗式代码审查 | 长篇论文和资料阅读、决策文档 |
| **agy CLI**（Gemini 4） | 长上下文读者与交叉核对 | 一次读完整仓代码、多篇论文/PDF、长日志，产出代码地图；图片和扫描件理解；方案与实现的一致性核对 | 直接改代码 |

三条硬规则：

1. **一组文件同一时间只有一个写手**。改同一批文件的任务串行；只读任务可以并行。
2. **写的模型和审的模型不同**。Codex sol 写的代码由 Codex astra 或 Gemini 审；Gemini 出的地图由 Claude 抽查。
3. **Claude 收口**。其他 agent 的报告是线索，不是证据；Claude 看过 diff、跑过检查后才对用户说"完成"。

## 任务类型 → 模型

| 任务类型 | 工具 | 模型 | effort | 模式 |
| --- | --- | --- | --- | --- |
| 拆任务、接口契约、最终整合、中文汇报 | Claude（本会话） | Opus 5.5 | high | — |
| 中文写作、润色、课程报告、邮件草稿 | Claude | Opus 5.5（短稿用 Sonnet 5.5） | medium | — |
| 前端 / UI 设计 | Claude | Opus 5.5 + 设计类 skill | high | — |
| 现有代码库里实现、调试、写测试 | Codex | `gpt-6.2-sol` | high；跨模块或数值敏感用 xhigh | write + worktree |
| 对抗式代码审查 | Codex | `gpt-6.2-astra` | xhigh | read |
| 数学推导、算法设计 | Codex | `gpt-6.2-sol` | xhigh | read |
| 机械改动、批量重命名、跑脚本收集输出 | Codex | `gpt-6.1-terra` | medium | write |
| grep、盘点、核对路径等杂活 | Codex | `gpt-6-luna` | medium（low 档实测会不调工具直接放弃） | read |
| 整仓代码地图、多篇论文 / PDF、长日志 | agy | `gemini-4-neon-xhigh` | 已在模型名里 | read |
| 图片、截图、扫描件、论文图表 | agy | `gemini-4-neon-high` | 已在模型名里 | read |
| 方案 ↔ 实现一致性、事实交叉核验 | agy | `gemini-4-hydrogen-high` | 已在模型名里 | read |
| 批量轻量摘要、分类 | agy | `gemini-3.8-flash-low` / `-medium` | 已在模型名里 | read |

档位选择：先用表里的默认档；同一任务失败一次再升一档，不要一开始就全开 xhigh/max。`ultra` 只在用户明确要求时用。

## 标准流水线（写代码类任务）

```
T0 Claude 契约 → T1 Gemini 代码地图 → T2 Codex sol 实现(+单测) → ┬ T3 Codex astra 审查 ┐
                                                                  └ T4 Gemini 一致性核对 ┴→ T5 Claude 整合、验证、提交
```

- 阅读 / 调研类：Gemini 读 → Claude 写结论；关键事实再让另一家核一遍。
- 写作类：Claude 写 → Gemini Flash 或 Codex luna 只做事实和格式核对。
- 小任务（几次工具调用就能完成）不走流水线，Claude 直接做。

## 通用约束（调度脚本会自动拼进每个 prompt）

- 先读工作目录里的 `AGENTS.md` / `CLAUDE.md` 并遵守。
- read 模式不改任何文件；write 模式只改任务涉及的文件，不 commit、不切分支、不 push。
- 不显示或写出密码、Token、Cookie、私钥、`.env`。
- 不连远程服务器、不启动长时间计算、不安装依赖，除非任务卡写明。
- 用中文写结论；引用代码写 `file:line`；最后一条消息就是交付物。

## 用法

见 [README.md](README.md)。
