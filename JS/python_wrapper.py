"""
Hermes Dream OS - Python Wrapper
=================================
Hermes Agent 的 Python 接口层，调用 JS 核心模块

用法:
    python python_wrapper.py <command> [args...]

Commands:
    briefing              - 晨间简报
    checkin <level> [prod] [note]  - 午间检查
    reflection            - 晚间反思
    consolidate           - 记忆整合
    win <description>     - 记录成就
    struggle <desc> [resolved] - 记录困境
    mood <score> [note] [triggers] - 记录情感
    energy <level> [context] [prod] - 记录精力
    insight <obs> <conf> [source] - 记录洞察
    habit <name> <done> [note] - 更新习惯
    goal <name> [progress] [deadline] - 更新目标
    night <phase>         - 夜间处理 (light/deep/rem)
    score                 - 测试评分函数
"""

import subprocess
import json
import sys
import os
from pathlib import Path

# JS 模块路径
JS_DIR = Path(__file__).parent / "src"
NODE_BIN = "node"


def run_js(module, function_name, *args):
    """通过 node 调用 JS 模块"""
    script = f"""
import {{ {function_name} }} from './{module}.js';
const result = {function_name}({', '.join(map(repr, args))});
console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        [NODE_BIN, "--input-type=module", "-e", script],
        cwd=str(JS_DIR),
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Output: {result.stdout}")
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == "briefing":
        result = run_js("day-mode", "dayMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), "briefing")

    elif cmd == "checkin":
        level = args[0] if len(args) > 0 else "medium"
        productivity = float(args[1]) if len(args) > 1 else None
        note = args[2] if len(args) > 2 else ""
        result = run_js("day-mode", "dayMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), "checkin", level, productivity, note)

    elif cmd == "reflection":
        result = run_js("day-mode", "dayMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), "reflection")

    elif cmd == "consolidate":
        result = run_js("day-mode", "dayMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), "consolidate")

    elif cmd == "win":
        result = run_js("day-mode", "dayMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), "win", args[0] if args else "")

    elif cmd == "struggle":
        desc = args[0] if args else ""
        resolved = args[1].lower() == "true" if len(args) > 1 else False
        result = run_js("day-mode", "dayMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), "struggle", desc, resolved)

    elif cmd == "night":
        phase = args[0] if args else "light"
        result = run_js("night-mode", "nightMode", os.environ.get("HERMES_WORKSPACE", "./workspace"), phase)

    elif cmd == "mood":
        score = float(args[0]) if args else 5
        note = args[1] if len(args) > 1 else ""
        triggers = args[2].split(",") if len(args) > 2 else []
        result = run_js("memory-hub", "MemoryHub", os.environ.get("HERMES_WORKSPACE", "./workspace"))
        if result:
            # MemoryHub 是构造函数，需要用不同方式
            pass

    elif cmd == "score":
        # 测试评分
        result = run_js("scoring", "rankCandidates", [
            {"key": "test", "recallCount": 5, "queryHashes": ["a", "b"], "recallDays": ["2026-05-20", "2026-05-21"]}
        ])
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return

    if result is not None:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
