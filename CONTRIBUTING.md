<!-- SPDX-License-Identifier: Apache-2.0 AND CC-BY-4.0 -->
<!-- Copyright (c) 2026 D-Robotics. All rights reserved. -->

# 贡献指南

本仓库是 D-Robotics RDK Device Skills Pack 的源头仓库，维护 14 个设备侧操作型 Skill。中央目录仓库（Hub）位于 [D-Robotics/rdk-skills](https://github.com/D-Robotics/rdk-skills)，通过同步流水线镜像本仓库的 Skill 内容。

## 提交前检查

1. **DCO 签名**（强制）：

   ```bash
   git commit -s -m "Add rdk-diagnostic skill"
   ```

2. **Skill 结构合规**（L1 准入门槛）：
   - `SKILL.md` 存在，带 YAML frontmatter
   - frontmatter 四必填：`name` / `description` / `version` / `license`
   - `name` 小写连字符 ≤64 字符，与目录名一致
   - `description` ≤1024 字符
   - `SKILL.md` 正文 ≤500 行

3. **L2 治理**（新增 Skill 强制）：
   - `skill-card.md` 存在
   - `evals/` 目录有任务文件
   - 四必备章节：`## Purpose` / `## When to use` / `## Instructions` / `## Safety`

4. **本地校验**：

   ```bash
   make validate    # 结构校验
   make test        # 全链路沙箱
   make lint        # bash 语法检查
   ```

## Skill 目录结构

```
skills/<skill-name>/
├── SKILL.md          # 入口：YAML frontmatter + Agent 指令
├── skill-card.md     # 治理卡片
├── evals/            # 评测任务（tasks.yaml）
├── scripts/          # 辅助脚本（默认只读，写操作需 --apply）
├── references/       # 参考材料，标注官方文档出处
└── assets/           # 模板、配置（可选）
```

## 设计原则

1. **官方文档是唯一事实来源**——不编造设备事实
2. **观测/行动分离**——诊断只读，写操作需显式 flag + 用户确认
3. **不编造数据**——不可得的信号报告 `null`/`false`，不猜
4. **Skill 自包含**——可独立安装
5. **description 是路由信号**——承载完整触发面与负向触发

完整规范见 [组织规范](../D-Robotics_Skills_组织规范.md)。
