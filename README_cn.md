# RDK Device Skills

[English](./README.md) | **简体中文**

[![License](https://img.shields.io/badge/license-Apache--2.0%20%2F%20CC--BY--4.0-blue.svg)](./LICENSE)

`rdk-device-skills` 是 **D-Robotics RDK 开发者套件**的官方 Agent Skills 目录。每个技能将 Agent 可读的操作指令、小型辅助脚本与精选参考资料打包在一起，使 AI 编码智能体能够在运行中的 RDK 设备上完成诊断、配置与开发——所有内容以 D-Robotics 官方文档为依据，而非依赖模型记忆。

本仓库为**设备侧（device-side）**仓库：技能在 RDK 上运行、检查 RDK 状态，或提供 Agent 应在 RDK 上执行的命令。烧录前的系统镜像定制不在本仓库范围内。

## 技能目录

| 技能 | 说明 |
| --- | --- |
| `rdk-diagnostic` | 只读设备健康快照：板卡身份、内存、BPU 负载、温度、存储、服务、内核错误计数与 Top 进程；支持趋势采样。 |
| `rdk-memory-audit` | 度量 DRAM 与 CMA/ION 占用，并以前后对比数据验证内存回收效果。 |
| `rdk-headless-mode` | 安全、可回退地关闭桌面与非必要服务，释放内存与 CPU。 |
| `rdk-camera-setup` | 通过 I²C 探测与官方示例完成 MIPI/USB 摄像头的检测、接入与出图验证。 |
| `rdk-vision-pipeline` | 跑通摄像头 → BPU 推理 → HDMI/Web 展示的端到端链路，并定位断在哪一环。 |
| `rdk-model-deploy` | 部署定点模型（X 系列 `.bin` / S 系列 `.hbm`），基于 Model Zoo 与官方 API。 |
| `rdk-model-benchmark` | 使用官方板端评测工具产出结构化的延迟/帧率基准指标，支持预置模型基准模式。 |
| `rdk-docs-reference` | 官方文档全文检索；以带出处的引用回答任意 RDK 知识问题。 |
| `rdk-system-config` | CPU 性能模式、温控参数与开机自启动配置。 |
| `rdk-network-remote` | 网络连通性与远程访问（SSH / 串口 / VNC）诊断，内置官方默认 IP 与波特率对照。 |
| `rdk-system-maintain` | 修复 apt 软件源、系统升级指引、TF 卡文件系统扩容与磁盘清理。 |
| `rdk-log-forensics` | 只读崩溃/日志取证：内核错误、失败服务、coredump 与异常重启证据。 |
| `rdk-gpio-40pin` | 40PIN 接口使用——GPIO、I²C、SPI、UART、PWM——基于预置的 `Hobot.GPIO` 库。 |
| `rdk-tros-setup` | TogetheROS.Bot（tros.b）的安装校验、环境配置、示例与 NodeHub 应用运行。 |

## 支持的硬件

| 板卡 | SoC | BPU | 算力 |
| --- | --- | --- | --- |
| RDK X3 / X3 Module | Sunrise 3 | Bernoulli | 5 TOPS |
| RDK X5 / X5 Module | Sunrise 5 | Bayes-e | 10 TOPS |
| RDK Ultra | Journey 5 | Bayes | 96 TOPS |
| RDK S100 / S100P | S100 / S100P | Nash-e | 80 / 128 TOPS |
| RDK S600 | S600 | Nash-p（4× Nash core） | 最高 560 TOPS |

板卡参数以官方文档仓库（[rdk_x_doc](https://github.com/D-Robotics/rdk_x_doc)、[rdk_s_doc](https://github.com/D-Robotics/rdk_s_doc)）为准；X 系列模型格式为 `.bin`，S 系列为 `.hbm`。

## 安装

在 RDK 设备上克隆本仓库：

```bash
git clone https://github.com/D-Robotics/rdk-device-skills.git
cd rdk-device-skills
```

将技能安装到各 Agent 的技能目录：

```bash
./install.sh
```

默认情况下，`install.sh` 会将技能软链接到受支持 Agent 运行时的用户级技能根目录：

- `~/.claude/skills`
- `~/.codex/skills`
- `~/.agents/skills`
- `~/.cursor/skills`
- `~/.qoder/skills`

也可以选择特定目标，或使用复制而非软链接：

```bash
./install.sh --targets claude,cursor
./install.sh --targets cursor-project --project /path/to/project
./install.sh --copy
./install.sh --force
```

安装完成后请重启 Agent 会话，使新技能条目生效。如果你的 Agent 读取其他技能目录，请将 `skills/` 目录复制或同步至对应位置。每个技能必须保持为完整目录，包含其 `SKILL.md`、`scripts/` 与 `references/` 内容。

## 使用方式

每个技能位于 `skills/<skill-name>/` 下，以 `SKILL.md` 为入口。Agent 运行时根据 frontmatter 中的 description 发现技能，并遵循所选技能内的指令执行。

部分技能在 `scripts/` 下附带辅助脚本，用户通常无需直接调用：当技能需要设备实时数据时，由 Agent 调用对应脚本，并以脚本输出作为唯一事实来源。脚本绝不编造数据——主机无法提供的字段报告为 `null`/`false`，检索无结果时明确输出 `no-match`。

## 仓库结构

```
rdk-device-skills/
├── README.md / README_cn.md
├── LICENSE
├── Makefile               # 开发 / CI 任务统一入口
├── install.sh
├── agents/                # 可选的编排型子代理
├── tools/                 # 验证沙箱与维护脚本
└── skills/
    ├── rdk-diagnostic/
    ├── rdk-memory-audit/
    ├── rdk-headless-mode/
    ├── rdk-camera-setup/
    ├── rdk-vision-pipeline/
    ├── rdk-model-deploy/
    ├── rdk-model-benchmark/
    ├── rdk-docs-reference/
    ├── rdk-system-config/
    ├── rdk-network-remote/
    ├── rdk-system-maintain/
    ├── rdk-log-forensics/
    ├── rdk-gpio-40pin/
    └── rdk-tros-setup/
```

单个技能的标准结构：

```
skills/<skill-name>/
├── SKILL.md          # 入口：YAML frontmatter + Agent 指令
├── skill-card.md     # 治理卡片：Owner、License、用例、已知风险
├── scripts/          # 辅助脚本（bash）；默认只读，
│                     # 变更类动作以显式参数门控
├── references/       # 标注官方文档出处的精选参考资料
└── evals/            # 评测任务定义（五维评测框架）
```

## 信息来源与可追溯性

本目录中的所有命令、路径与板卡参数均来源于 D-Robotics 官方文档仓库；每个参考文件都标注了其派生的具体文档路径。`rdk-docs-reference` 技能还会对这些仓库的本地克隆做实时全文检索，可随时刷新：

```bash
make docs-update
```

## 开发与验证

```bash
make test           # 全链路沙箱：索引 + 路由套件 + 结构校验 + 文档检索检查
make validate       # 仅结构校验（frontmatter/章节/脚本/引用完整性）
make route Q="..."  # 单条问题路由调试
make lint           # 全部脚本 bash 语法检查
make docs-update    # 克隆/刷新官方文档数据源
```

验证沙箱（`tools/sandbox.py`）对每个技能强制执行：

- frontmatter 完整性；`name` 为小写连字符（≤ 64 字符）且与目录名一致；`description` ≤ 1024 字符；正文 ≤ 500 行；
- 必备章节、`skill-card.md` 与 `evals/tasks.yaml` 的存在性；
- 所有被引用脚本与参考文件的存在性及语法有效性；
- 确定性路由回归套件，其中包含必须路由为"无技能匹配"的超范围问题。

## 设计原则

1. **官方文档是唯一事实来源。** 技能引用并标注出处，不即兴编写设备事实。
2. **观测与行动分离。** 诊断类技能严格只读并交接给行动类技能；变更动作需显式参数（如 `--apply`）与用户确认。
3. **不编造。** 不可得的信号报告为 `null`/`false` 并说明原因；无法回答的问题回答"未覆盖"，绝不猜测。
4. **技能自包含。** 每个技能目录可独立安装；共享的平台检测器在缺失时优雅降级。
5. **Description 即路由信号。** frontmatter description 承载完整触发面与负触发——因为只有 description 常驻 Agent 上下文。

## 参与贡献

欢迎贡献。提交 Pull Request 前请：

1. 遵循上述技能结构；一个技能只做一件界定清晰的事。
2. 所有设备事实以官方文档为依据，并在 `references/` 中记录出处。
3. 运行 `make test` 并确保沙箱全部通过。

## 许可证

本仓库采用双许可：文档部分适用 **CC-BY-4.0**，源码部分适用 **Apache-2.0**。详见 [LICENSE](./LICENSE)。
