# agents/ — sub-agents for RDK workflows

本目录存放 Claude Code 子代理（sub-agents）：拥有独立 system prompt 与受限工具集的
长任务专家，负责编排 `skills/` 下的一个或多个技能。

> 技能是可移植的，子代理是 Claude Code 专属的。`skills/` 下的技能无需修改即可在
> Cursor、Copilot、Codex、Qoder、Claude Code 中使用；`agents/` 下的子代理只在支持
> Claude Code 子代理格式的运行时中加载。其他 Agent 仍可直接调用底层技能——只是
> 没有编排层。

如果只有时间写其中之一，请写技能。只有当编排复杂到小模型无法自行走对调用顺序时，
才增加子代理。

## On-disk shape

```
agents/
└── rdk-<role>.md          # 每个子代理一个文件
```

每个文件是带 YAML frontmatter 的 markdown 文档：

```
---
name: rdk-perf-investigator
description: Diagnose RDK performance issues end to end.
tools: Bash, Read, Grep, Glob
---

# System prompt body...
```

| Frontmatter 字段 | 用途 |
| --- | --- |
| name | 子代理标识符，必须与文件名一致，使用 `rdk-<role>`（kebab-case） |
| description | 一行触发描述，父 Agent 据此决定何时委派 |
| tools | 允许调用的工具逗号分隔清单，保持最小化 |

## Available sub-agents

| Agent | Purpose |
| --- | --- |
| rdk-perf-investigator.md | 端到端 RDK 性能问题排查：诊断 + 内存审计 + 模型基准，输出结构化结论。 |
| rdk-vision-investigator.md | 端到端视觉链路排查：摄像头 → BPU 推理 → 显示/Web 的断点定位，输出结构化结论。 |
| rdk-setup-orchestrator.md | 新板开箱 Day-1 编排：身份基线 → 网络 → 系统健康 → tros 就绪，输出就绪度报告。 |

## Authoring guidelines

- system prompt 保持简短（约 80 行以内）；小模型对短 prompt 的遵循度更好。
- 永远委派给 `skills/` 下的技能，不要在代理体内重新实现逻辑——代理只是胶水。
- `tools` 字段列出代理需要的所有工具；未列出的无法使用。
- 输出结构化交接（JSON 或编号结论），便于父 Agent 采取行动。
- 默认只读行为；只有在明确的确认步骤之后才调用变更类辅助脚本（`--apply` 等）。

## Other agent runtimes

- Cursor / Copilot / Codex / Qoder：可直接加载 SKILL.md 的运行时无需子代理文件，
  技能正文本身就按"可被逐步驱动"编写。
- Claude Code：将 agents/ 复制或软链到 `~/.claude/agents/`（install.sh 的 claude
  目标会自动完成）。
