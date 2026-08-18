#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2026 D-Robotics. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""
rdk-device-skills test sandbox.

Simulates how an agent runtime discovers, routes, and consumes the skills in
this repository, without needing a live LLM or RDK hardware:

  index     build & print the skill index from SKILL.md frontmatter
  route Q   route a user question to the best-matching skill (bigram scoring
            over frontmatter description/tags and the "When to use" section —
            a deterministic stand-in for LLM frontmatter-based discovery)
  validate  structural checks: frontmatter completeness, script/reference
            integrity, bash syntax
  test      full run: index + routing suite (from evals/tasks.yaml + built-in
            queries) + validation + docs-search functional check

Usage:
  python3 tools/sandbox.py index
  python3 tools/sandbox.py route "40PIN 引脚定义是什么"
  python3 tools/sandbox.py validate
  python3 tools/sandbox.py test
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(REPO, "skills")

REQUIRED_SECTIONS = [
    "## Purpose", "## When to use", "## Instructions", "## Safety",
]
REQUIRED_FRONTMATTER = ["name", "description", "version", "license"]
RETIRED_ROUTES = {
    "rdk-device",
    "rdk-doc-finder",
    "rdk-ros",
    "rdk-mipi-camera-bringup",
    "rdk-perf-investigator",
}
WORKSPACE_ROUTER_ROUTES = {
    "rdk-board-delegate": {"horizon-router": "OE Tool Chain (S)"},
    "rdk-board-knowledge": {
        "x5-router": "OE Tool Chain (X5)",
        "horizon-router": "OE Tool Chain (S)",
    },
    "rdk-embodied-lerobot": {
        "x5-router": "OE Tool Chain (X5)",
        "horizon-router": "OE Tool Chain (S)",
    },
    "rdk-hardware": {
        "x5-router": "OE Tool Chain (X5)",
        "horizon-router": "OE Tool Chain (S)",
    },
    "rdk-model-zoo": {
        "x5-router": "OE Tool Chain (X5)",
        "horizon-router": "OE Tool Chain (S)",
    },
}


# ── skill loading ────────────────────────────────────────────────────────────

def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    fm, key = {}, None
    for line in m.group(1).splitlines():
        kv = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        sub = re.match(r"^\s+(\w[\w-]*):\s*(.*)$", line)
        item = re.match(r"^\s+-\s+(.*)$", line)
        if kv:
            key = kv.group(1)
            fm[key] = kv.group(2).strip() or []
        elif sub and isinstance(fm.get("metadata"), dict):
            fm["metadata"][sub.group(1)] = sub.group(2).strip() or []
            key = "metadata." + sub.group(1)
        elif item and key:
            if key == "metadata":
                pass
            elif key.startswith("metadata."):
                mk = key.split(".", 1)[1]
                if isinstance(fm["metadata"].get(mk), list):
                    fm["metadata"][mk].append(item.group(1).strip())
            elif isinstance(fm.get(key), list):
                fm[key].append(item.group(1).strip())
        if kv and kv.group(1) == "metadata":
            fm["metadata"] = {}
            key = "metadata"
    return fm


def section(text, header):
    pat = re.compile(r"^## " + re.escape(header) + r"\s*$(.*?)(?=^## |\Z)",
                     re.S | re.M)
    m = pat.search(text)
    return m.group(1) if m else ""


def load_skills():
    skills = {}
    for name in sorted(os.listdir(SKILLS_DIR)):
        d = os.path.join(SKILLS_DIR, name)
        md = os.path.join(d, "SKILL.md")
        if not os.path.isfile(md):
            continue
        text = open(md, encoding="utf-8").read()
        fm = parse_frontmatter(text)
        tags = fm.get("metadata", {}).get("tags", []) if isinstance(fm.get("metadata"), dict) else []
        skills[name] = {
            "dir": d,
            "text": text,
            "frontmatter": fm,
            "tags": tags,
            "when_to_use": section(text, "When to use"),
            "description": fm.get("description", ""),
        }
    return skills


def retired_route_problems(skills):
    problems = []
    for name, skill in skills.items():
        for route in RETIRED_ROUTES:
            pattern = rf"(?<![a-z0-9-]){re.escape(route)}(?![a-z0-9-])"
            if re.search(pattern, skill["text"], re.I):
                problems.append(f"{name}: references retired route '{route}'")
    return problems


def workspace_router_route_problems(skills):
    problems = []
    for name, routes in WORKSPACE_ROUTER_ROUTES.items():
        skill = skills.get(name)
        if skill is None:
            continue
        description = skill.get("description", "")
        text = skill.get("text", "")
        if "availability-gated" not in description:
            problems.append(f"{name}: workspace router metadata is not availability-gated")
        if "## Workspace router availability gate" not in text:
            problems.append(f"{name}: missing workspace router availability gate")
        for router, pack in routes.items():
            availability_check = (
                f"check whether `{router}` is available in the current session"
            )
            if availability_check not in text:
                problems.append(f"{name}: missing availability check for '{router}'")
            if pack not in text:
                problems.append(f"{name}: missing install fallback for '{router}'")
            atomic_fallback = (
                f"{availability_check}. If unavailable, do not hand off: "
                f"use `rdk-pack-installer` to install `{pack}`"
            )
            if atomic_fallback not in text:
                problems.append(f"{name}: missing atomic fallback for '{router}'")
        for marker in ("`rdk-pack-installer`", "restart", "retry"):
            if marker.casefold() not in text.casefold():
                problems.append(f"{name}: workspace router gate missing '{marker}'")
    return problems


# ── routing (deterministic stand-in for LLM discovery) ──────────────────────

def grams(query):
    """ASCII words + Chinese character bigrams."""
    words = [w.lower() for w in re.findall(r"[A-Za-z0-9_.]{2,}", query)]
    han = re.findall(r"[\u4e00-\u9fff]", query)
    bigrams = ["".join(han[i:i + 2]) for i in range(len(han) - 1)]
    return words, bigrams


def negative_scope(when_text):
    """Text after the '不要' boundary paragraph counts against a skill."""
    m = re.search(r"\*\*不要\*\*(.*)", when_text, re.S)
    return m.group(1) if m else ""


# Below this top-1 score the router reports "none": the question does not
# belong to any skill (mirrors an LLM simply not activating a skill).
ROUTE_THRESHOLD = 8.0


def route(query, skills):
    words, bigrams = grams(query)
    scores = {}
    for name, s in skills.items():
        hi = (s["description"] + " " + " ".join(s["tags"])).lower()
        mid = s["when_to_use"]
        lo = s["text"]
        neg = negative_scope(mid)
        score = 0.0
        for w in words:
            if w in hi:
                score += 6
            if w in mid.lower():
                score += 4
            elif w in lo.lower():
                score += 1
            if w in neg.lower():
                score -= 2
        for b in bigrams:
            if b in hi:
                score += 5
            if b in mid:
                score += 3
            elif b in lo:
                score += 0.5
            if b in neg:
                score -= 1.5
        scores[name] = round(score, 1)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    return ranked


# ── validation ───────────────────────────────────────────────────────────────

def validate(skills):
    problems = []
    ok = []
    for name, s in skills.items():
        fm = s["frontmatter"]
        # 1. frontmatter completeness + name/dir match
        for key in REQUIRED_FRONTMATTER:
            if not fm.get(key):
                problems.append(f"{name}: frontmatter missing '{key}'")
        if fm.get("name") != name:
            problems.append(f"{name}: frontmatter name '{fm.get('name')}' != dir")
        # 1b. AMD-style hard limits (amd/skills CI parity):
        #     name lowercase-hyphen <=64; description <=1024 chars; body <=500 lines
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", name):
            problems.append(f"{name}: name must be lowercase-with-hyphens, <=64 chars")
        desc = fm.get("description", "")
        if len(desc) > 1024:
            problems.append(f"{name}: description too long ({len(desc)} > 1024 chars)")
        body_lines = len(s["text"].split("---\n", 2)[-1].splitlines())
        if body_lines > 500:
            problems.append(f"{name}: SKILL.md body too long ({body_lines} > 500 lines)")
        # 2. required sections
        for sec in REQUIRED_SECTIONS:
            if sec + "\n" not in s["text"] and not re.search(
                    r"^" + re.escape(sec) + r"\s*$", s["text"], re.M):
                problems.append(f"{name}: missing section '{sec}'")
        # 3. companion files
        for fname in ("skill-card.md",):
            if not os.path.isfile(os.path.join(s["dir"], fname)):
                problems.append(f"{name}: missing {fname}")
        if not os.path.isfile(os.path.join(s["dir"], "evals", "tasks.yaml")):
            problems.append(f"{name}: missing evals/tasks.yaml")
        # 4. every scripts/* referenced in SKILL.md exists; every file present
        #    in scripts/ passes bash -n and is executable
        for ref in set(re.findall(r"scripts/([\w./-]+\.sh)", s["text"])):
            p = os.path.join(s["dir"], "scripts", ref)
            if not os.path.isfile(p):
                problems.append(f"{name}: SKILL.md references scripts/{ref} but file missing")
        sdir = os.path.join(s["dir"], "scripts")
        if os.path.isdir(sdir):
            for f in os.listdir(sdir):
                if not f.endswith(".sh"):
                    continue
                p = os.path.join(sdir, f)
                r = subprocess.run(["bash", "-n", p], capture_output=True)
                if r.returncode != 0:
                    problems.append(f"{name}: bash -n failed for scripts/{f}: "
                                    f"{r.stderr.decode().strip()}")
                if not os.access(p, os.X_OK):
                    problems.append(f"{name}: scripts/{f} not executable")
        # 5. references/ files mentioned in SKILL.md exist
        for ref in set(re.findall(r"references/([\w./-]+\.md)", s["text"])):
            if not os.path.isfile(os.path.join(s["dir"], "references", ref)):
                problems.append(f"{name}: SKILL.md references references/{ref} but file missing")
        ok.append(name)
    problems.extend(retired_route_problems(skills))
    problems.extend(workspace_router_route_problems(skills))
    return ok, problems


# ── routing test suite ───────────────────────────────────────────────────────

BUILTIN_CASES = [
    # 硬件诊断
    ("这块板子是什么型号？内存多大？", {"rdk-diagnostic"}),
    ("帮我看看板子现在的温度和 BPU 占用", {"rdk-diagnostic"}),
    # 内存管理
    ("RDK 内存不够了，还能腾出来多少？", {"rdk-memory-audit"}),
    ("drop_caches 到底有没有用？释放了多少？", {"rdk-memory-audit"}),
    # 摄像头配置
    ("MIPI 摄像头接上了怎么验证能不能用？", {"rdk-camera-setup"}),
    ("i2cdetect 扫不到摄像头地址", {"rdk-camera-setup"}),
    # 模型部署
    ("我想在 RDK 上跑 YOLO 检测模型，从哪开始？", {"rdk-model-deploy"}),
    ("这个 bin 模型怎么在 Python 里调用？", {"rdk-model-deploy"}),
    # 性能优化
    ("帮我测一下模型的推理延迟和帧率", {"rdk-model-benchmark"}),
    ("把 CPU 锁到最高频率跑性能模式", {"rdk-system-config"}),
    # 服务管理（诊断先报告再交接属合法路径）
    ("哪些正在运行的服务可以关掉？", {"rdk-headless-mode", "rdk-diagnostic"}),
    # 外设
    ("怎么用 GPIO 点亮一个 LED？", {"rdk-gpio-40pin"}),
    ("40PIN 的引脚定义是什么？", {"rdk-gpio-40pin", "rdk-docs-reference"}),
    # ROS
    ("tros 怎么安装，怎么确认装好了？", {"rdk-tros-setup"}),
    # 端到端视觉链路
    ("怎么让摄像头实时推理跑模型，网页看画面？", {"rdk-vision-pipeline"}),
    # 网络与远程访问
    ("ssh 连不上开发板了，网络不通怎么排查？", {"rdk-network-remote"}),
    # 系统运维
    ("apt update 失败，报 Could not resolve，软件源怎么换？", {"rdk-system-maintain"}),
    # 日志取证
    ("板子突然自动重启了，帮我看看日志里有什么线索。", {"rdk-log-forensics"}),
    # 知识检索
    ("官方 FAQ 里有没有讲过这个报错？", {"rdk-docs-reference"}),
    # 超出范围：非 RDK 问题不应激活任何技能
    ("怎么在树莓派上装 Windows 系统", {"none"}),
    ("帮我写一首关于春天的诗", {"none"}),
]

# Legitimate handoffs are NOT hardcoded: skill A routing a question that was
# expected at skill B is acceptable iff A's SKILL.md explicitly mentions B
# (declared handoff / consult relationship). The SKILL.md files stay the
# single source of truth for inter-skill topology.
def declared_handoff(skills, got, expected):
    if got not in skills or expected == got:
        return False
    return expected in skills[got]["text"]


def load_eval_cases(skills):
    """Routing cases from evals/tasks.yaml.

    security-dimension cases are skipped here: they evaluate refusal/behavior
    of a live agent, not frontmatter-based skill discovery.
    """
    cases = []
    for name, s in skills.items():
        path = os.path.join(s["dir"], "evals", "tasks.yaml")
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        for block in re.split(r"\n(?=- id:)", text):
            pm = re.search(r'prompt:\s*"(.+?)"', block)
            sm = re.search(r"skill:\s*([\w-]+)", block)
            dm = re.search(r"dimension:\s*([\w-]+)", block)
            if dm and dm.group(1) == "security":
                continue
            if pm and sm and sm.group(1) != "none":
                cases.append((pm.group(1), sm.group(1), name))
    return cases


def case_pass(skills, expected, got):
    if isinstance(expected, set):
        return got in expected
    return got == expected or declared_handoff(skills, got, expected)


def run_routing_suite(skills):
    results = []
    for query, expected in BUILTIN_CASES:
        ranked = route(query, skills)
        top, score = ranked[0]
        got = top if score >= ROUTE_THRESHOLD else "none"
        results.append({
            "query": query, "expected": "|".join(sorted(expected)), "got": got,
            "score": score, "pass": case_pass(skills, expected, got), "source": "builtin",
        })
    for query, expected, origin in load_eval_cases(skills):
        ranked = route(query, skills)
        top, score = ranked[0]
        got = top if score >= ROUTE_THRESHOLD else "none"
        results.append({
            "query": query, "expected": expected, "got": got,
            "score": score, "pass": case_pass(skills, expected, got),
            "source": f"evals:{origin}",
        })
    return results


# ── docs search functional check ─────────────────────────────────────────────

def docs_search_check():
    script = os.path.join(SKILLS_DIR, "rdk-docs-reference", "scripts", "search_docs.sh")
    checks = []
    r = subprocess.run(["bash", script, "--query", "40PIN", "--limit", "5"],
                       capture_output=True, text=True)
    hits = [l for l in r.stdout.splitlines() if ":" in l]
    checks.append(("search '40PIN' returns hits", r.returncode == 0 and len(hits) > 0))
    r2 = subprocess.run(["bash", script, "--query", "hrut_somstatus",
                         "--query", "ratio", "--limit", "5"],
                        capture_output=True, text=True)
    checks.append(("multi-keyword intersection works",
                   r2.returncode == 0 and "no-match" not in r2.stdout and r2.stdout.strip() != ""))
    r3 = subprocess.run(["bash", script, "--toc", "--repo", "s"],
                        capture_output=True, text=True)
    checks.append(("--toc lists rdk_s_doc files",
                   r3.returncode == 0 and "rdk_s_doc" in r3.stdout))
    r4 = subprocess.run(["bash", script, "--query", "不存在的关键词XYZQWE"],
                        capture_output=True, text=True)
    checks.append(("no-match reported honestly", "no-match" in r4.stdout))

    # Run the real script against an isolated official-doc fixture. This guards
    # the TROS handoff contract without depending on a local tros_doc clone.
    with tempfile.TemporaryDirectory() as tmp:
        tros_docs = os.path.join(tmp, "tros_doc", "docs")
        os.makedirs(tros_docs)
        fixture = os.path.join(tros_docs, "ros-node.md")
        with open(fixture, "w", encoding="utf-8") as f:
            f.write("TROS_FIXTURE node development reference\n")
        bash_script, docs_root = script, tmp
        if os.name == "nt":
            def wsl_path(path):
                drive, tail = os.path.splitdrive(path)
                return f"/mnt/{drive[0].lower()}{tail.replace(os.sep, '/')}"
            bash_script = wsl_path(script)
            docs_root = wsl_path(tmp)
        def run_fixture(repo):
            command = (
                f"RDK_DOCS_ROOT={shlex.quote(docs_root)} "
                f"bash {shlex.quote(bash_script)} --repo {repo} --query TROS_FIXTURE"
            )
            return subprocess.run(["bash", "-c", command],
                                  capture_output=True, text=True)
        r5 = run_fixture("tros")
        checks.append(("--repo tros searches tros_doc fixture",
                       r5.returncode == 0 and "tros_doc/docs/ros-node.md" in r5.stdout))
        r6 = run_fixture("all")
        checks.append(("--repo all includes tros_doc fixture",
                       r6.returncode == 0 and "tros_doc/docs/ros-node.md" in r6.stdout))
    return checks


# ── entrypoints ──────────────────────────────────────────────────────────────

def cmd_index(skills):
    idx = [{
        "name": n,
        "version": s["frontmatter"].get("version"),
        "tags": s["tags"],
        "description": s["description"],
    } for n, s in skills.items()]
    print(json.dumps(idx, ensure_ascii=False, indent=2))


def cmd_route(skills, query):
    ranked = route(query, skills)
    top, score = ranked[0]
    routed = top if score >= ROUTE_THRESHOLD else "none"
    out = {
        "query": query,
        "routed_to": routed,
        "candidates": [{"skill": n, "score": sc} for n, sc in ranked[:3]],
    }
    if routed == "none":
        out["note"] = ("no skill above threshold; for RDK knowledge questions "
                       "fall back to rdk-docs-reference, otherwise answer "
                       "without skills")
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_validate(skills):
    ok, problems = validate(skills)
    print(f"skills checked: {len(ok)}")
    if problems:
        print(f"PROBLEMS ({len(problems)}):")
        for p in problems:
            print(f"  ✗ {p}")
        return 1
    print("all structural checks passed ✓")
    return 0


def cmd_test(skills):
    rc = 0
    print("=" * 62)
    print("[1/4] skill index")
    print("=" * 62)
    for n, s in skills.items():
        print(f"  ✓ {n} v{s['frontmatter'].get('version')} tags={','.join(s['tags'])}")
    print(f"  → {len(skills)} skills indexed")

    print("=" * 62)
    print("[2/4] routing suite (question → skill)")
    print("=" * 62)
    results = run_routing_suite(skills)
    passed = [r for r in results if r["pass"]]
    for r in results:
        mark = "✓" if r["pass"] else "✗"
        note = "" if r["pass"] else f"  (expected {r['expected']}, got {r['got']})"
        print(f"  {mark} [{r['source']}] {r['query']} → {r['got']}{note}")
    print(f"  → routing accuracy: {len(passed)}/{len(results)}")
    if len(passed) != len(results):
        rc = 1

    print("=" * 62)
    print("[3/4] structural validation")
    print("=" * 62)
    ok, problems = validate(skills)
    if problems:
        for p in problems:
            print(f"  ✗ {p}")
        rc = 1
    print(f"  → {len(ok)} skills, {len(problems)} problems")

    print("=" * 62)
    print("[4/4] docs search functional check")
    print("=" * 62)
    for label, good in docs_search_check():
        print(f"  {'✓' if good else '✗'} {label}")
        if not good:
            rc = 1

    print("=" * 62)
    print("RESULT:", "PASS" if rc == 0 else "FAIL")
    return rc


def main():
    skills = load_skills()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd == "index":
        cmd_index(skills)
    elif cmd == "route":
        if len(sys.argv) < 3:
            print("usage: sandbox.py route \"<question>\"", file=sys.stderr)
            sys.exit(1)
        cmd_route(skills, sys.argv[2])
    elif cmd == "validate":
        sys.exit(cmd_validate(skills))
    elif cmd == "test":
        sys.exit(cmd_test(skills))
    else:
        print(__doc__, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
