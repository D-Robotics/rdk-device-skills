# RDK Device Skills

**English** | [简体中文](./README_cn.md)

[![License](https://img.shields.io/badge/license-Apache--2.0%20%2F%20CC--BY--4.0-blue.svg)](./LICENSE)

`rdk-device-skills` is the official catalog of Agent Skills for **D-Robotics RDK developer kits**. Each skill packages agent-readable instructions, small helper scripts, and curated references that enable AI coding agents to diagnose, configure, and develop on a live RDK device — grounded in the official D-Robotics documentation rather than model memory.

This is a **device-side** repository: skills run on the RDK, inspect the RDK, or provide commands that an agent should execute on the RDK. System-image customization prior to flashing is out of scope.

## Skill Catalog

| Skill | Description |
| --- | --- |
| `rdk-diagnostic` | Read-only device health snapshot: board identity, memory, BPU load, thermal, storage, services, kernel error count, and top processes; optional trend recording. |
| `rdk-memory-audit` | Measure DRAM and CMA/ION usage and verify memory reclamation with before/after data. |
| `rdk-headless-mode` | Safely and reversibly disable the desktop and non-essential services to free memory and CPU. |
| `rdk-camera-setup` | Detect, connect, and verify MIPI/USB cameras using I²C probing and official samples. |
| `rdk-vision-pipeline` | Bring up the end-to-end camera → BPU inference → HDMI/Web display pipeline and locate the broken stage. |
| `rdk-model-deploy` | Deploy quantized models (`.bin` for X series, `.hbm` for S series) via Model Zoo and official APIs. |
| `rdk-model-benchmark` | Produce structured latency/FPS benchmarks with the official on-board evaluation tool, including a preinstalled-model baseline mode. |
| `rdk-docs-reference` | Full-text search over the official documentation; answers any RDK knowledge question with sourced citations. |
| `rdk-system-config` | CPU performance mode, thermal trip points, and boot auto-start configuration. |
| `rdk-network-remote` | Diagnose network connectivity and remote access (SSH / serial / VNC), with official static-IP and baud-rate defaults. |
| `rdk-system-maintain` | Repair apt sources, guide system upgrades, expand the TF-card filesystem, and clean up disk space. |
| `rdk-log-forensics` | Read-only crash/log forensics: kernel errors, failed services, coredumps, and abnormal-reboot evidence. |
| `rdk-gpio-40pin` | 40-pin header usage — GPIO, I²C, SPI, UART, and PWM — with the preinstalled `Hobot.GPIO` library. |
| `rdk-tros-setup` | Install, verify, and troubleshoot TogetheROS.Bot (tros.b), run its package examples and NodeHub apps. |

## Supported Hardware

| Board | SoC | BPU | Compute |
| --- | --- | --- | --- |
| RDK X3 / X3 Module | Sunrise 3 | Bernoulli | 5 TOPS |
| RDK X5 / X5 Module | Sunrise 5 | Bayes-e | 10 TOPS |
| RDK Ultra | Journey 5 | Bayes | 96 TOPS |
| RDK S100 / S100P | S100 / S100P | Nash-e | 80 / 128 TOPS |
| RDK S600 | S600 | Nash-p (4× Nash core) | up to 560 TOPS |

Board parameters follow the official documentation repositories ([rdk_x_doc](https://github.com/D-Robotics/rdk_x_doc), [rdk_s_doc](https://github.com/D-Robotics/rdk_s_doc)). Model format is `.bin` on the X series and `.hbm` on the S series.

## Installation

Clone the repository on the RDK device:

```bash
git clone https://github.com/D-Robotics/rdk-device-skills.git
cd rdk-device-skills
```

Install the skills into the agent skill directories:

```bash
./install.sh
```

By default, `install.sh` symlinks the skills into the user-level skill roots of the supported agent runtimes:

- `~/.claude/skills`
- `~/.codex/skills`
- `~/.agents/skills`
- `~/.cursor/skills`
- `~/.qoder/skills`

Select specific targets, or copy instead of symlinking:

```bash
./install.sh --targets claude,cursor
./install.sh --targets cursor-project --project /path/to/project
./install.sh --copy
./install.sh --force
```

Restart the agent session after installation so that new skill entries are picked up. If your agent reads a different skill directory, copy or sync the `skills/` directory into that location. Keep each skill as a complete directory containing its `SKILL.md`, `scripts/`, and `references/` content.

## Usage

Each skill lives under `skills/<skill-name>/` and starts with a `SKILL.md` file. Agent runtimes discover skills from their frontmatter descriptions and follow the instructions in the selected skill.

Some skills include helper scripts under `scripts/`. Users normally do not call these scripts directly: when a skill requires live device data, the agent invokes the relevant helper and treats its output as the single source of truth. Scripts never fabricate data — fields the host cannot provide are reported as `null`/`false`, and searches with no results report `no-match` explicitly.

## Repository Layout

```
rdk-device-skills/
├── README.md / README_cn.md
├── LICENSE
├── Makefile               # single entry point for dev / CI tasks
├── install.sh
├── agents/                # optional orchestration sub-agents
├── tools/                 # validation sandbox and maintenance scripts
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

Standard anatomy of a skill:

```
skills/<skill-name>/
├── SKILL.md          # entry point: YAML frontmatter + agent instructions
├── skill-card.md     # governance card: owner, license, use case, known risks
├── scripts/          # helper scripts (bash); read-only by default,
│                     # mutating actions gated behind explicit flags
├── references/       # curated reference material with documentation provenance
└── evals/            # evaluation task definitions (five-dimension rubric)
```

## Information Sources and Traceability

All commands, paths, and board parameters in this catalog are sourced from the official D-Robotics documentation repositories. Every reference file records the exact document path it derives from. The `rdk-docs-reference` skill additionally performs live full-text search over local clones of these repositories; refresh them at any time:

```bash
make docs-update
```

## Development and Validation

```bash
make test         # full sandbox: index + routing suite + structural checks + docs search
make validate     # structural checks only (frontmatter, sections, scripts, references)
make route Q="..."  # debug routing for a single question
make lint         # bash syntax check for every script
make docs-update  # clone/refresh the official documentation sources
```

The validation sandbox (`tools/sandbox.py`) enforces, for every skill:

- frontmatter completeness; `name` in lowercase-with-hyphens (≤ 64 chars) matching the directory; `description` ≤ 1024 chars; body ≤ 500 lines;
- presence of required sections, `skill-card.md`, and `evals/tasks.yaml`;
- existence and syntactic validity of every referenced script and reference file;
- a deterministic routing regression suite, including out-of-scope queries that must route to no skill.

## Design Principles

1. **Official documentation is the single source of truth.** Skills quote and cite it; they do not improvise device facts.
2. **Observe/act separation.** Diagnostic skills are strictly read-only and hand off to action skills; mutating actions require explicit flags (e.g. `--apply`) and user confirmation.
3. **No fabrication.** Unavailable signals are reported as `null`/`false` with an explanation; unanswerable questions are answered with "not covered", never with guesses.
4. **Self-contained skills.** Each skill directory is independently installable; the shared platform detector degrades gracefully when absent.
5. **Description as the routing signal.** Frontmatter descriptions carry the full trigger surface and negative triggers, since only descriptions are always resident in agent context.

## Contributing

Contributions are welcome. Before opening a pull request:

1. Follow the skill anatomy above; one well-scoped task per skill.
2. Ground every device fact in the official documentation and record provenance in `references/`.
3. Run `make test` and ensure the full sandbox passes.

## License

This repository is dual-licensed: documentation under **CC-BY-4.0** and source code under **Apache-2.0**. See [LICENSE](./LICENSE) for details.
