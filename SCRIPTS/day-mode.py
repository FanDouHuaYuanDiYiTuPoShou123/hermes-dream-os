"""
Hermes Dream OS — Day Mode (Life OS)
活跃期处理：Morning Briefing / Midday Check-in / Evening Reflection / Memory Consolidation
"""

import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from memory_hub import MemoryHub


# ========== Morning Briefing ==========

def morning_briefing(workspace_dir: str) -> dict:
    """
    07:00 - 晨间简报
    基于 Hermes Life OS 的 show, don't remind 原则

    输出：
    - 能量预测
    - 今日优先级
    - 一个洞察
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    weekday = now.strftime("%A")

    result = {
        "type": "morning_briefing",
        "timestamp": now.isoformat(),
        "sections": {}
    }

    # 1. 能量预测（基于历史数据）
    recent_energy = hub.get_recent_energy(days=14)
    weekday_energy = [e for e in recent_energy if e.get("date", "") and datetime.strptime(e["date"], "%Y-%m-%d").strftime("%A") == weekday]

    if weekday_energy:
        avg_productivity = sum(e.get("productivity", 5) for e in weekday_energy) / len(weekday_energy)
        if avg_productivity >= 7:
            energy_level = "高效"
        elif avg_productivity >= 5:
            energy_level = "平稳"
        else:
            energy_level = "需要调整"
    else:
        energy_level = "未知（数据不足）"

    result["sections"]["energy_forecast"] = {
        "weekday": weekday,
        "predicted": energy_level,
        "sample_size": len(weekday_energy)
    }

    # 2. 今日目标
    goals = hub.read_goals()
    active_goals = []
    for name, goal in goals.items():
        if goal.get("progress", 0) < 1.0:
            active_goals.append({
                "name": name,
                "progress": goal.get("progress", 0),
                "deadline": goal.get("deadline", "无")
            })

    # 按进度排序，最需要的先
    active_goals.sort(key=lambda x: x["progress"])

    result["sections"]["today_goals"] = {
        "active": active_goals[:3],
        "total": len(active_goals)
    }

    # 3. 一个洞察
    insights = hub.get_recent_insights(days=14, min_confidence=0.7)
    top_insight = insights[0] if insights else None

    if top_insight:
        result["sections"]["insight"] = {
            "text": top_insight["observation"],
            "confidence": top_insight["confidence"],
            "date": top_insight.get("date", "")
        }
    else:
        result["sections"]["insight"] = {
            "text": "暂无高置信度洞察",
            "confidence": 0
        }

    # 4. 今日习惯提醒
    habits = hub.read_habits()
    habit_reminders = []
    for name, data in habits.items():
        if data.get("last_done") != today:
            habit_reminders.append({
                "name": name,
                "streak": data.get("streak", 0),
                "last_done": data.get("last_done", "从未")
            })

    result["sections"]["habit_reminders"] = habit_reminders[:3]

    # 5. 事件记录
    hub.append_event(
        "life.briefing.morning",
        weekday=weekday,
        energy_level=energy_level,
        goals_count=len(active_goals)
    )

    return result


def format_briefing_text(result: dict, user_name: str = "主人") -> str:
    """
    将简报结果格式化为文本（Hermes 风格）
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    weekday = now.strftime("%A")

    sections = result.get("sections", {})

    lines = [
        f"早上好，{user_name}。{date_str}，{weekday}。",
        "",
    ]

    # 能量预测
    energy = sections.get("energy_forecast", {})
    predicted = energy.get("predicted", "未知")
    lines.append(f"**能量预测**")
    lines.append(f"{weekday} 对你来说通常是 {predicted} 的一天。")
    lines.append("")

    # 洞察
    insight = sections.get("insight", {})
    if insight.get("confidence", 0) > 0:
        lines.append("**一个洞察**")
        lines.append(f"> {insight['text']}")
        lines.append("")

    # 今日目标
    goals = sections.get("today_goals", {})
    active = goals.get("active", [])
    if active:
        lines.append("**今日目标**")
        for g in active[:3]:
            progress = g.get("progress", 0) * 100
            lines.append(f"-> {g['name']} ({progress:.0f}%)")
        lines.append("")

    # 习惯提醒
    reminders = sections.get("habit_reminders", [])
    if reminders:
        lines.append("**习惯提醒**")
        for h in reminders:
            lines.append(f"- {h['name']} (已连续 {h['streak']} 天)")
        lines.append("")

    return "\n".join(lines)


# ========== Midday Check-in ==========

def midday_checkin(workspace_dir: str, energy_level: str = None, productivity: int = None, note: str = "") -> dict:
    """
    12:00 - 午间检查

    参数：
    - energy_level: low | medium | high
    - productivity: 1-10
    - note: 可选备注
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()

    result = {
        "type": "midday_checkin",
        "timestamp": now.isoformat(),
        "recorded": False
    }

    if energy_level or productivity:
        if energy_level:
            hub.record_energy(level=energy_level, context=note, productivity=productivity)
            result["recorded"] = True
            result["energy_level"] = energy_level

        if productivity:
            result["productivity"] = productivity

        hub.append_event(
            "life.checkin.midday",
            energy_level=energy_level,
            productivity=productivity,
            note=note
        )

    return result


# ========== Evening Reflection ==========

def evening_reflection(workspace_dir: str) -> dict:
    """
    18:00 - 晚间反思

    展示：完成事项 / 未完成 / 模式观察
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    result = {
        "type": "evening_reflection",
        "timestamp": now.isoformat(),
        "sections": {}
    }

    # 1. 今日成就
    wins = hub.read_jsonl(hub.wins_path)
    today_wins = [w for w in wins if w.get("date") == today]
    result["sections"]["wins"] = today_wins

    # 2. 今日困境
    struggles = hub.read_jsonl(hub.struggles_path)
    today_struggles = [s for s in struggles if s.get("date") == today]
    result["sections"]["struggles"] = today_struggles

    # 3. 今日洞察
    insights = hub.get_recent_insights(days=1)
    today_insights = [i for i in insights if i.get("date") == today]
    result["sections"]["insights"] = today_insights

    # 4. 情感记录
    moods = hub.get_recent_moods(days=1)
    today_moods = [m for m in moods if m.get("date") == today]
    if today_moods:
        result["sections"]["mood"] = today_moods[0]
    else:
        # 提示记录
        result["sections"]["mood_prompt"] = True

    # 事件记录
    hub.append_event(
        "life.reflection.evening",
        wins_count=len(today_wins),
        struggles_count=len(today_struggles),
        insights_count=len(today_insights)
    )

    return result


def format_reflection_text(result: dict, user_name: str = "主人") -> str:
    """
    将反思结果格式化为文本
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")

    sections = result.get("sections", {})

    lines = [
        f"晚上好，{user_name}。{date_str} 即将结束。",
        "",
    ]

    # 成就
    wins = sections.get("wins", [])
    if wins:
        lines.append("**今日成就**")
        for w in wins:
            lines.append(f"- 🎉 {w.get('description', '')}")
        lines.append("")

    # 困境
    struggles = sections.get("struggles", [])
    unresolved = [s for s in struggles if not s.get("resolved")]
    if unresolved:
        lines.append("**待解决**")
        for s in unresolved:
            lines.append(f"- 🤔 {s.get('description', '')}")
        lines.append("")

    # 洞察
    insights = sections.get("insights", [])
    if insights:
        lines.append("**今日洞察**")
        for i in insights:
            conf = i.get("confidence", 0)
            lines.append(f"- 💡 {i.get('observation', '')} (置信度: {conf:.0%})")
        lines.append("")

    # 情感提示
    if sections.get("mood_prompt"):
        lines.append("**情感记录**")
        lines.append("今天的心情如何？（1-10 分）")
        lines.append("")

    return "\n".join(lines)


# ========== Memory Consolidation ==========

def memory_consolidation(workspace_dir: str) -> dict:
    """
    23:00 - 记忆整合

    存储今日模式，更新习惯连续
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    result = {
        "type": "memory_consolidation",
        "timestamp": now.isoformat(),
        "processed": []
    }

    # 1. 模式发现 - 基于今日数据
    moods = hub.get_recent_moods(days=1)
    today_moods = [m for m in moods if m.get("date") == today]

    if today_moods:
        avg_score = sum(m.get("score", 5) for m in today_moods) / len(today_moods)
        # 如果连续 3 天低于 6，生成洞察
        recent_moods = hub.get_recent_moods(days=3)
        if len(recent_moods) >= 3 and all(m.get("score", 5) < 6 for m in recent_moods):
            hub.record_insight(
                observation=f"连续 3 天情绪偏低（平均 {avg_score:.1f}/10），可能需要调整生活节奏",
                confidence=0.75,
                source="mood",
                pattern_based=True
            )
            result["processed"].append("mood_pattern_insight")

    # 2. 事件记录
    hub.append_event(
        "life.consolidation",
        date=today,
        patterns_count=len(result["processed"])
    )

    return result


# ========== Record Win ==========

def record_win(workspace_dir: str, description: str, category: str = "general") -> dict:
    """记录一个成就"""
    hub = MemoryHub(workspace_dir)
    result = hub.record_win(description=description, category=category)

    hub.append_event(
        "life.win.recorded",
        description=description,
        category=category
    )

    return result


# ========== Record Struggle ==========

def record_struggle(workspace_dir: str, description: str, resolved: bool = False) -> dict:
    """记录一个困境"""
    hub = MemoryHub(workspace_dir)
    result = hub.record_struggle(description=description, resolved=resolved)

    hub.append_event(
        "life.struggle.recorded",
        description=description,
        resolved=resolved
    )

    return result


# ========== CLI 入口 ==========

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: day-mode.py <workspace_dir> <action> [args...]")
        print("  Actions:")
        print("    briefing                    - Morning briefing")
        print("    checkin <level> [prod]      - Midday check-in (level: low|medium|high, prod: 1-10)")
        print("    reflection                  - Evening reflection")
        print("    consolidate                 - Memory consolidation")
        print("    win <description>           - Record a win")
        print("    struggle <description>      - Record a struggle")
        sys.exit(1)

    workspace_dir = sys.argv[1]
    action = sys.argv[2].lower()

    if action == "briefing":
        result = morning_briefing(workspace_dir)
        print(format_briefing_text(result))

    elif action == "checkin":
        level = sys.argv[3] if len(sys.argv) > 3 else None
        prod = int(sys.argv[4]) if len(sys.argv) > 4 else None
        note = sys.argv[5] if len(sys.argv) > 5 else ""
        result = midday_checkin(workspace_dir, level, prod, note)
        print(__import__('json').dumps(result, ensure_ascii=False, indent=2))

    elif action == "reflection":
        result = evening_reflection(workspace_dir)
        print(format_reflection_text(result))

    elif action == "consolidate":
        result = memory_consolidation(workspace_dir)
        print(__import__('json').dumps(result, ensure_ascii=False, indent=2))

    elif action == "win":
        if len(sys.argv) < 4:
            print("Error: win requires <description>")
            sys.exit(1)
        description = sys.argv[3]
        result = record_win(workspace_dir, description)
        print(f"Win recorded: {description}")

    elif action == "struggle":
        if len(sys.argv) < 4:
            print("Error: struggle requires <description>")
            sys.exit(1)
        description = sys.argv[3]
        result = record_struggle(workspace_dir, description)
        print(f"Struggle recorded: {description}")

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
