"""
Hermes Dream OS - Python CLI Wrapper
=====================================
通过 subprocess 调用 JS 模块

用法:
    python py_dream.py briefing
    python py_dream.py checkin high 8
    python py_dream.py win "完成项目X"
    python py_dream.py night deep
"""

import subprocess
import json
import sys
import os
from pathlib import Path

# JS 模块入口
JS_CLI = Path(__file__).parent / "src" / "cli.js"


def run(args, cwd=None):
    """执行 node cli.js"""
    result = subprocess.run(
        ["node", str(JS_CLI), *args],
        cwd=cwd or str(Path(__file__).parent),
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stdout)
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    args = sys.argv[2:]
    workspace = os.environ.get("DREAM_OS_WORKSPACE", "")

    if cmd == "briefing":
        result = run(["day-mode", workspace, "briefing"])
    elif cmd == "checkin":
        result = run(["day-mode", workspace, "checkin", *args])
    elif cmd == "reflection":
        result = run(["day-mode", workspace, "reflection"])
    elif cmd == "consolidate":
        result = run(["day-mode", workspace, "consolidate"])
    elif cmd == "win":
        result = run(["day-mode", workspace, "win", *args])
    elif cmd == "struggle":
        result = run(["day-mode", workspace, "struggle", *args])
    elif cmd == "night":
        phase = args[0] if args else "light"
        result = run(["night-mode", workspace, phase])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
