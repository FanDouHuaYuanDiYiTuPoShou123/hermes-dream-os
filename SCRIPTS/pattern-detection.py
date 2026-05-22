"""
Hermes Dream OS — Pattern Detection
基于 Hermes Life OS 的模式检测规则
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from memory_hub import MemoryHub


# ========== 模式检测规则 ==========

RULES = {
    "mood_dip": {
        "name": "情绪低落",
        "condition": "3+ consecutive days below 6/10",
        "threshold": 3,
        "score_threshold": 6,
        "severity": "attention",
    },
    "energy_pattern": {
        "name": "精力模式",
        "condition": "same day of week consistently low/high",
        "min_samples": 4,
        "severity": "info",
    },
    "habit_streak_7": {
        "name": "习惯连续",
        "condition": "7 days completed",
        "threshold": 7,
        "severity": "celebrate",
    },
    "habit_streak_broken": {
        "name": "习惯中断",
        "condition": "streak broken",
        "grace_days": 2,
        "severity": "acknowledge",
    },
    "goal_stall": {
        "name": "目标停滞",
        "condition": "no progress in 7 days",
        "threshold_days": 7,
        "severity": "nudge",
    },
    "win_pattern": {
        "name": "成就模式",
        "condition": "same type of win 3+ times",
        "threshold": 3,
        "severity": "reinforce",
    },
    "memory_recency": {
        "name": "记忆新鲜度",
        "condition": "memory not accessed in 14 days",
        "threshold_days": 14,
        "severity": "promote",
    },
    "memory_frequency_spike": {
        "name": "记忆召回高峰",
        "condition": "same memory recalled 3+ times in 2 days",
        "recall_threshold": 3,
        "days_window": 2,
        "severity": "boost",
    },
}


# ========== Mood Dip Detection ==========

def detect_mood_dip(hub: MemoryHub, days: int = 7, score_threshold: int = 6) -> Optional[dict]:
    """
    检测情绪低落模式
    触发条件：连续 3+ 天情绪评分低于阈值
    """
    moods = hub.get_recent_moods(days=days)

    # 按日期分组
    by_date = {}
    for m in moods:
        date = m.get("date", "")
        if date not in by_date:
            by_date[date] = []
        by_date[date].append(m.get("score", 5))

    # 计算每天平均
    daily_avg = []
    for date, scores in by_date.items():
        daily_avg.append((date, sum(scores) / len(scores)))

    # 按日期排序
    daily_avg.sort(key=lambda x: x[0])

    # 检测连续低于阈值
    consecutive = 0
    start_date = None
    for date, avg in daily_avg:
        if avg < score_threshold:
            if consecutive == 0:
                start_date = date
            consecutive += 1
        else:
            if consecutive >= RULES["mood_dip"]["threshold"]:
                break
            consecutive = 0
            start_date = None

    if consecutive >= RULES["mood_dip"]["threshold"]:
        return {
            "rule": "mood_dip",
            "type": "pattern",
            "severity": "attention",
            "observation": f"连续 {consecutive} 天情绪偏低",
            "start_date": start_date,
            "recent_dates": [d for d, _ in daily_avg[-consecutive:]],
            "avg_score": sum(s for _, s in daily_avg[-consecutive:]) / consecutive,
            "threshold": score_threshold,
        }

    return None


# ========== Energy Pattern Detection ==========

def detect_energy_patterns(hub: MemoryHub, days: int = 28) -> list:
    """
    检测精力模式
    找出每周哪几天精力特别高或低
    """
    energy = hub.get_recent_energy(days=days)

    # 按星期几分组
    by_weekday = {i: [] for i in range(7)}
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    for e in energy:
        date_str = e.get("date", "")
        if not date_str:
            continue
        try:
            weekday = datetime.strptime(date_str, "%Y-%m-%d").weekday()
            productivity = e.get("productivity", 5)
            by_weekday[weekday].append(productivity)
        except ValueError:
            continue

    patterns = []
    for weekday, scores in by_weekday.items():
        if len(scores) >= RULES["energy_pattern"]["min_samples"]:
            avg = sum(scores) / len(scores)
            if avg >= 7:
                patterns.append({
                    "rule": "energy_pattern",
                    "type": "pattern",
                    "severity": "info",
                    "observation": f"{weekday_names[weekday]} 平均精力 {avg:.1f}/10（高效日）",
                    "weekday": weekday,
                    "avg_productivity": avg,
                    "sample_size": len(scores),
                })
            elif avg <= 4:
                patterns.append({
                    "rule": "energy_pattern",
                    "type": "pattern",
                    "severity": "info",
                    "observation": f"{weekday_names[weekday]} 平均精力 {avg:.1f}/10（低谷日）",
                    "weekday": weekday,
                    "avg_productivity": avg,
                    "sample_size": len(scores),
                })

    return patterns


# ========== Habit Streak Detection ==========

def detect_habit_streaks(hub: MemoryHub) -> list:
    """
    检测习惯连续和中断
    """
    habits = hub.read_habits()
    patterns = []

    for name, data in habits.items():
        streak = data.get("streak", 0)
        last_done = data.get("last_done")

        if streak >= RULES["habit_streak_7"]["threshold"]:
            patterns.append({
                "rule": "habit_streak_7",
                "type": "achievement",
                "severity": "celebrate",
                "habit": name,
                "observation": f"'{name}' 已连续 {streak} 天",
                "streak": streak,
            })

        # 检查是否中断
        if last_done:
            try:
                last_date = datetime.strptime(last_done, "%Y-%m-%d")
                days_since = (datetime.now() - last_date).days
                grace = RULES["habit_streak_broken"]["grace_days"]

                if streak == 0 and days_since > grace:
                    patterns.append({
                        "rule": "habit_streak_broken",
                        "type": "break",
                        "severity": "acknowledge",
                        "habit": name,
                        "observation": f"'{name}' 已中断 {days_since} 天",
                        "days_since": days_since,
                    })
            except ValueError:
                pass

    return patterns


# ========== Goal Stall Detection ==========

def detect_goal_stalls(hub: MemoryHub, threshold_days: int = 7) -> list:
    """
    检测目标停滞
    """
    goals = hub.read_goals()
    patterns = []

    for name, goal in goals.items():
        if goal.get("progress", 0) >= 1.0:
            continue  # 已完成的目标跳过

        last_updated = goal.get("lastUpdated", "")
        if not last_updated:
            continue

        try:
            last_date = datetime.strptime(last_updated, "%Y-%m-%d")
            days_since = (datetime.now() - last_date).days

            if days_since > threshold_days:
                patterns.append({
                    "rule": "goal_stall",
                    "type": "warning",
                    "severity": "nudge",
                    "goal": name,
                    "observation": f"'{name}' 已 {days_since} 天无进展（当前 {goal.get('progress', 0)*100:.0f}%）",
                    "days_since": days_since,
                    "progress": goal.get("progress", 0),
                    "deadline": goal.get("deadline", "无"),
                })
        except ValueError:
            pass

    return patterns


# ========== Win Pattern Detection ==========

def detect_win_patterns(hub: MemoryHub, days: int = 30, threshold: int = 3) -> list:
    """
    检测同类成就重复出现
    """
    wins = hub.read_jsonl(hub.wins_path)
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    recent_wins = [w for w in wins if w.get("date", "") >= cutoff]

    # 按类别分组
    by_category = {}
    for w in recent_wins:
        cat = w.get("category", "general")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(w)

    patterns = []
    for cat, cat_wins in by_category.items():
        if len(cat_wins) >= threshold:
            patterns.append({
                "rule": "win_pattern",
                "type": "pattern",
                "severity": "reinforce",
                "observation": f"'{cat}' 类成就已达成 {len(cat_wins)} 次",
                "category": cat,
                "count": len(cat_wins),
                "wins": [w.get("description", "")[:50] for w in cat_wins[-3:]],
            })

    return patterns


# ========== Memory Recency Detection ==========

def detect_stale_memories(hub: MemoryHub, threshold_days: int = 14) -> list:
    """
    检测长期未访问的记忆
    """
    store = hub.read_short_term_recall()
    now = datetime.now()
    patterns = []

    for key, entry in store.get("entries", {}).items():
        last_recalled = entry.get("lastRecalledAt", "")
        if not last_recalled or entry.get("promotedAt"):
            continue

        try:
            last_date = datetime.fromisoformat(last_recalled)
            days_since = (now - last_date).days

            if days_since > threshold_days:
                patterns.append({
                    "rule": "memory_recency",
                    "type": "suggestion",
                    "severity": "promote",
                    "observation": f"记忆 '{entry.get('snippet', '')[:40]}...' 已 {days_since} 天未访问",
                    "key": key,
                    "days_since": days_since,
                    "path": entry.get("path", ""),
                })
        except ValueError:
            continue

    return patterns[:10]  # 最多返回 10 个


# ========== 主检测函数 ==========

def detect_all_patterns(workspace_dir: str) -> dict:
    """
    运行所有模式检测
    """
    hub = MemoryHub(workspace_dir)

    results = {
        "timestamp": datetime.now().isoformat(),
        "patterns": [],
        "by_severity": {
            "attention": [],
            "celebrate": [],
            "nudge": [],
            "reinforce": [],
            "promote": [],
            "info": [],
        }
    }

    # 运行各项检测
    detectors = [
        ("mood_dip", detect_mood_dip),
        ("energy_patterns", detect_energy_patterns),
        ("habit_streaks", detect_habit_streaks),
        ("goal_stalls", detect_goal_stalls),
        ("win_patterns", detect_win_patterns),
        ("stale_memories", detect_stale_memories),
    ]

    for rule_name, detector in detectors:
        try:
            if rule_name == "energy_patterns":
                patterns = detector(hub)
            else:
                patterns = detector(hub)

            if patterns:
                if isinstance(patterns, list):
                    results["patterns"].extend(patterns)
                else:
                    results["patterns"].append(patterns)

                # 按严重性分类
                for p in (patterns if isinstance(patterns, list) else [patterns]):
                    severity = p.get("severity", "info")
                    if severity in results["by_severity"]:
                        results["by_severity"][severity].append(p)

        except Exception as e:
            results["patterns"].append({
                "rule": rule_name,
                "type": "error",
                "error": str(e)
            })

    # 按严重性排序
    severity_order = ["attention", "celebrate", "nudge", "reinforce", "promote", "info"]
    results["patterns"].sort(key=lambda x: severity_order.index(x.get("severity", "info")))

    return results


# ========== CLI 入口 ==========

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: pattern-detection.py <workspace_dir>")
        sys.exit(1)

    workspace_dir = sys.argv[1]
    result = detect_all_patterns(workspace_dir)

    print(f"检测时间: {result['timestamp']}")
    print(f"发现 {len(result['patterns'])} 个模式")
    print()

    for pattern in result["patterns"]:
        severity_emoji = {
            "attention": "⚠️",
            "celebrate": "🎉",
            "nudge": "📌",
            "reinforce": "💪",
            "promote": "📈",
            "info": "ℹ️",
        }.get(pattern.get("severity", "info"), "📝")

        print(f"{severity_emoji} [{pattern.get('rule', 'unknown')}] {pattern.get('observation', '')}")
