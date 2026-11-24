---
id: T1
tool: agy
model: gemini-4-neon-xhigh
effort:
mode: read
cwd: .
inputs: .agent-runs/plan/request.md, AGENTS.md  # request.md 放用户原话；agy 只能列 cwd 内的文件
output: .agent-runs/out/T1.md
depends:
timeout: 3600
---

## 背景

（只写用户原话和做决定必需的背景：现状、约束、已经定死的事。**不写 Claude 自己的方案、草稿、倾向或候选项**，否则就不是独立的第二份了。）

## 目标

针对 `request.md` 里的需求，独立出一份完整方案。

## 具体要求

- 先说结论：推荐怎么做，一句话。
- 列出关键取舍，每个取舍写选了什么、放弃了什么、为什么。
- 风险和没想清楚的地方单列，不要藏在正文里。
- 涉及现有代码的判断写 `file:line`；没读到证据、靠推测的，句尾标【推测】。

## 交付物格式

1. 结论（一句话）
2. 方案（分步骤）
3. 关键取舍（表：取舍点 | 选择 | 放弃的 | 理由）
4. 风险与待决事项
5. 标了【推测】的判断清单
