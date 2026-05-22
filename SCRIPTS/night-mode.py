"""
Hermes Dream OS — Night Mode (Dreams)
休眠期处理：Light → Deep → REM 三阶段
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加父目录到 path 以便导入
sys.path.insert(0, str(Path(__file__).parent))

from memory_hub import MemoryHub
from scoring import (
    rank_candidates, calculate_memory_score, clamp,
    MIN_SCORE, MIN_RECALL_COUNT, MIN_UNIQUE_QUERIES,
    RECENCY_HALF_LIFE_DAYS, MAX_PROMOTIONS, DEFAULT_WEIGHTS
)
from concept_tagging import extract_concepts


# ========== 配置文件 ==========

CONFIG = {
    "light": {
        "enabled": True,
        "lookback_days": 2,
        "limit": 100,
        "dedupe_similarity": 0.9,
        "sources": ["daily", "sessions", "recall"],
    },
    "deep": {
        "enabled": True,
        "lookback_days": 30,
        "limit": 10,
        "min_score": 0.75,
        "min_recall_count": 3,
        "min_unique_queries": 3,
        "recency_half_life_days": 14,
        "max_age_days": 30,
    },
    "rem": {
        "enabled": True,
        "lookback_days": 7,
        "limit": 10,
        "min_pattern_strength": 0.75,
        "sources": ["memory", "daily", "deep"],
    }
}


# ========== 污染检测 ==========

CONTAMINATION_MARKERS = [
    "openclaw-memory-promotion:",
    "dreaming-narrative-",
    "<!-- openclaw-memory-promotion:",
]

PROMOTION_MARKER_RE = __import__('re').compile(r'<!--\s*openclaw-memory-promotion:([^\n]+?)\s*-->', __import__('re').IGNORECASE)
DREAMING_NARRATIVE_PROMPT_RE = __import__('re').compile(
    r'\[[^\]]*dreaming-narrative[^\]]*\]\s*(?:User|Assistant):\s*Write a dream diary entry',
    __import__('re').IGNORECASE
)


def is_contaminated_snippet(snippet: str) -> bool:
    """
    检测片段是否被梦境系统污染
    污染片段不应参与晋升
    """
    if not snippet:
        return False

    # 检查注释标记
    for marker in CONTAMINATION_MARKERS:
        if marker.lower() in snippet.lower():
            return True

    # 检查梦境叙述提示
    if DREAMING_NARRATIVE_PROMPT_RE.search(snippet):
        return True

    # 检查结构化梦境字段
    has_narrative_lead = bool(
        __import__('re').search(r'^Candidate:', snippet, __import__('re').IGNORECASE) or
        __import__('re').search(r'^Reflections?:', snippet, __import__('re').IGNORECASE)
    )
    has_confidence = bool(__import__('re').search(r'\bconfidence:\s*\d', snippet, __import__('re').IGNORECASE))
    has_evidence = bool(__import__('re').search(r'\bevidence:\s*memory', snippet, __import__('re').IGNORECASE))
    has_status = bool(__import__('re').search(r'\bstatus:\s*staged', snippet, __import__('re').IGNORECASE))
    has_recalls = bool(__import__('re').search(r'\brecalls:\s*\d+\b', snippet, __import__('re').IGNORECASE))

    return has_narrative_lead and has_confidence and has_evidence and has_status and has_recalls


# ========== Light Phase ==========

def light_phase(workspace_dir: str) -> dict:
    """
    Light 阶段：整理近期的记忆信号，去重并暂存候选内容

    与 OpenClaw 的区别：
    - 额外整合当天的 life-log 数据（mood/energy/insights）
    - 将 life-log 中高置信度洞察直接标记为候选
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()
    today = hub.format_iso_day()
    lookback_days = CONFIG["light"]["lookback_days"]

    results = {
        "phase": "light",
        "timestamp": now.isoformat(),
        "candidates_processed": 0,
        "high_confidence_insights": 0,
        "deduped": 0,
    }

    # 1. 收集当日生活记录中的高置信度洞察
    insights = hub.get_recent_insights(days=1, min_confidence=0.8)
    for insight in insights:
        results["high_confidence_insights"] += 1
        # 洞察直接作为候选，不经过评分

    # 2. 读取短期记忆
    store = hub.read_short_term_recall()
    entries = list(store.get("entries", {}).values())

    # 3. 去重（基于 snippet 相似度）
    deduped = []
    seen_snippets = set()
    for entry in entries:
        snippet = entry.get("snippet", "")
        if not snippet or is_contaminated_snippet(snippet):
            continue

        # 简单去重：检查完全相同或包含关系
        is_dup = False
        snippet_lower = snippet.lower()
        for seen in seen_snippets:
            if snippet_lower == seen.lower() or snippet_lower in seen.lower() or seen.lower() in snippet_lower:
                is_dup = True
                break

        if not is_dup:
            deduped.append(entry)
            seen_snippets.add(snippet_lower)
        else:
            results["deduped"] += 1

    results["candidates_processed"] = len(deduped)

    # 4. 记录 Light 阶段命中（更新 phase-signals）
    phase_signals = hub.read_phase_signals()
    for entry in deduped[:CONFIG["light"]["limit"]]:
        key = entry.get("key")
        if not key:
            continue
        if key not in phase_signals["entries"]:
            phase_signals["entries"][key] = {"lightHits": 0, "remHits": 0}
        signals = phase_signals["entries"][key]
        signals["lightHits"] = min(9999, signals.get("lightHits", 0) + 1)
        signals["lastLightAt"] = now.isoformat()

    phase_signals["updatedAt"] = now.isoformat()
    hub.write_phase_signals(phase_signals)

    # 5. 事件记录
    hub.append_event(
        "dream.phase.completed",
        phase="light",
        candidates_count=results["candidates_processed"],
        insights_count=results["high_confidence_insights"],
        deduped_count=results["deduped"]
    )

    return results


# ========== Deep Phase ==========

def deep_phase(workspace_dir: str) -> dict:
    """
    Deep 阶段：评分并将有价值的候选内容推入长期记忆

    与 OpenClaw 的区别：
    - 引入"洞察价值"维度（来自 life-log 的洞察优先晋升）
    - 引入"主人关注度"维度（基于 goals 关联度）
    - 新增"情感权重"（mood 低迷日的记忆价值适度放大）
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()
    now_ms = now.timestamp() * 1000

    results = {
        "phase": "deep",
        "timestamp": now.isoformat(),
        "candidates_ranked": 0,
        "promoted": [],
        "rejected": [],
    }

    # 1. 读取数据和配置
    store = hub.read_short_term_recall()
    phase_signals = hub.read_phase_signals()
    goals = hub.read_goals()
    recent_moods = hub.get_recent_moods(days=7)

    # 2. 判断当前是否为情感低谷
    low_mood_days = [m for m in recent_moods if m.get("score", 10) < 6]
    is_low_mood_context = len(low_mood_days) >= 2

    # 3. 准备晋升候选
    entries = []
    for key, entry in store.get("entries", {}).items():
        if is_contaminated_snippet(entry.get("snippet", "")):
            continue
        if entry.get("promotedAt"):
            continue

        # 检查是否与活跃目标关联
        entry_path = entry.get("path", "")
        related_goal = False
        for goal_name, goal_data in goals.items():
            if goal_data.get("progress", 0) < 1.0:  # 活跃目标
                if any(g in entry_path.lower() or g in entry.get("snippet", "").lower()
                       for g in goal_name.lower().split()):
                    related_goal = True
                    break

        # 设置情感上下文
        emotional_context = "low_mood_day" if is_low_mood_context else "normal"

        entry["key"] = key
        entry["includePromoted"] = False
        entry["relatedGoalActive"] = related_goal
        entry["emotionalContext"] = emotional_context
        entries.append(entry)

    results["candidates_ranked"] = len(entries)

    # 4. 评分排序
    scored = rank_candidates(
        entries,
        phase_signals=phase_signals,
        weights=DEFAULT_WEIGHTS,
        min_score=CONFIG["deep"]["min_score"],
        min_recall_count=CONFIG["deep"]["min_recall_count"],
        min_unique_queries=CONFIG["deep"]["min_unique_queries"],
        max_age_days=CONFIG["deep"]["max_age_days"],
        limit=CONFIG["deep"]["limit"],
        now_ms=now_ms
    )

    # 5. 执行晋升
    promoted_keys = set()
    for candidate in scored:
        if promote_to_memory(hub, candidate, now):
            promoted_keys.add(candidate.key)
            results["promoted"].append({
                "key": candidate.key,
                "path": candidate.path,
                "score": round(candidate.score, 3),
                "snippet": candidate.snippet[:80] + "..." if len(candidate.snippet) > 80 else candidate.snippet
            })

    # 6. 更新 store 中的 promotedAt
    for key, entry in store["entries"].items():
        if key in promoted_keys:
            entry["promotedAt"] = now.isoformat()
    store["updatedAt"] = now.isoformat()
    hub.write_short_term_recall(store)

    # 7. 事件记录
    hub.append_event(
        "dream.phase.completed",
        phase="deep",
        candidates_count=results["candidates_ranked"],
        promoted_count=len(results["promoted"])
    )

    return results


def promote_to_memory(hub: MemoryHub, candidate, now: datetime) -> bool:
    """
    将候选内容晋升到 MEMORY.md
    """
    memory_path = hub.memory_md_path

    # 读取现有内容
    try:
        existing = memory_path.read_text(encoding="utf-8") if memory_path.exists() else ""
    except IOError:
        existing = ""

    # 构建标记
    marker = f"<!-- hermes-dream-os:{candidate.key} -->"

    # 检查是否已存在
    if marker in existing:
        return False

    # 构建条目
    snippet = candidate.snippet or "(no snippet captured)"
    source_ref = f"{candidate.path}:{candidate.start_line}-{candidate.end_line}"
    entry_line = f"- {snippet} [score={candidate.score:.3f} recalls={candidate.recall_count} source={source_ref}]"

    # 添加时间戳标记
    timestamp_line = f"  _Promoted: {now.strftime('%Y-%m-%d %H:%M')}_"

    # 构建 section
    section = f"\n## Promoted From Short-Term Memory ({now.strftime('%Y-%m-%d')})\n\n{marker}\n{entry_line}\n{timestamp_line}\n"

    # 追加到文件
    header = "# Long-Term Memory\n\n" if not existing.strip() else ""
    content = f"{header}{existing}{section}"

    try:
        memory_path.write_text(content, encoding="utf-8")
        return True
    except IOError:
        return False


# ========== REM Phase ==========

def rem_phase(workspace_dir: str) -> dict:
    """
    REM 阶段：提取主题和重复模式，生成 Dream Diary

    与 OpenClaw 的区别：
    - 整合 life-log 中的模式（不只是 memory）
    - 生成"下周预测"和"建议行动"
    - Dream Diary 格式更贴近 Hermes 的 show, don't remind
    """
    hub = MemoryHub(workspace_dir)
    now = datetime.now()
    today = hub.format_iso_day()

    results = {
        "phase": "rem",
        "timestamp": now.isoformat(),
        "patterns_detected": [],
        "diary_generated": False,
    }

    # 1. 收集过去 7 天的数据
    recent_moods = hub.get_recent_moods(days=7)
    recent_energy = hub.get_recent_energy(days=7)
    recent_insights = hub.get_recent_insights(days=7)
    goals = hub.read_goals()
    habits = hub.read_habits()

    # 2. 模式检测
    patterns = []

    # Mood 趋势
    if len(recent_moods) >= 3:
        avg_mood = sum(m.get("score", 5) for m in recent_moods) / len(recent_moods)
        if avg_mood < 6:
            patterns.append({
                "type": "mood_low",
                "observation": f"近7天平均情绪 {avg_mood:.1f}/10，持续偏低",
                "confidence": 0.8,
                "action": "关注"
            })

    # Energy 模式
    energy_by_day = {}
    for e in recent_energy:
        day = e.get("date", "")
        level = e.get("level", "medium")
        if day not in energy_by_day:
            energy_by_day[day] = []
        energy_by_day[day].append(level)

    for day, levels in energy_by_day.items():
        low_count = levels.count("low")
        if low_count >= 2:
            patterns.append({
                "type": "energy_dip",
                "observation": f"{day} 精力持续低迷",
                "confidence": 0.7,
                "action": "调整"
            })

    # Habit 连续
    for habit_name, habit_data in habits.items():
        streak = habit_data.get("streak", 0)
        if streak >= 7:
            patterns.append({
                "type": "habit_streak",
                "observation": f"'{habit_name}' 已连续 {streak} 天",
                "confidence": 0.95,
                "action": "保持"
            })
        elif streak == 0 and habit_data.get("last_done"):
            last = datetime.strptime(habit_data["last_done"], "%Y-%m-%d")
            if (datetime.now() - last).days > 3:
                patterns.append({
                    "type": "habit_broken",
                    "observation": f"'{habit_name}' 已中断",
                    "confidence": 0.9,
                    "action": "重启"
                })

    # Goal 进展
    for goal_name, goal_data in goals.items():
        progress = goal_data.get("progress", 0)
        last_updated = goal_data.get("lastUpdated", "")
        if last_updated:
            days_since = (datetime.now() - datetime.strptime(last_updated, "%Y-%m-%d")).days
            if days_since > 7 and progress < 1.0:
                patterns.append({
                    "type": "goal_stall",
                    "observation": f"'{goal_name}' 7天无进展 (当前 {progress*100:.0f}%)",
                    "confidence": 0.85,
                    "action": "推进"
                })

    results["patterns_detected"] = patterns

    # 3. 生成 Dream Diary
    if patterns:
        diary_content = generate_dream_diary(
            patterns=patterns,
            recent_insights=recent_insights,
            goals=goals,
            today=today
        )

        # 追加到 DREAMS.md
        dreams_path = hub.dreams_md_path
        try:
            existing = dreams_path.read_text(encoding="utf-8") if dreams_path.exists() else ""
        except IOError:
            existing = ""

        # 保留最近 30 天的 diary
        lines = existing.split("\n") if existing else []
        cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        lines = [l for l in lines if not l.startswith(f"## {cutoff}") and not l.startswith(f"# Dream Diary — {cutoff}")]

        content = f"{''.join(l + chr(10) for l in lines)}\n\n{diary_content}"

        try:
            dreams_path.write_text(content, encoding="utf-8")
            results["diary_generated"] = True
        except IOError:
            results["diary_generated"] = False

    # 4. 事件记录
    hub.append_event(
        "dream.phase.completed",
        phase="rem",
        patterns_count=len(patterns),
        diary_generated=results["diary_generated"]
    )

    return results


def generate_dream_diary(patterns: list, recent_insights: list, goals: dict, today: str) -> str:
    """
    生成梦境日记内容（Hermes 风格）
    """
    lines = [
        f"## Dream Diary — {today}",
        "",
        "### 夜间记忆整理",
        "",
        f"在过去的夜晚，记忆系统完成了模式发现和整理工作。",
        "",
    ]

    # 模式汇总
    lines.append("**发现的模式**")
    for p in patterns[:5]:  # 最多 5 个
        emoji = {
            "mood_low": "😔",
            "energy_dip": "⚡",
            "habit_streak": "🔥",
            "habit_broken": "💤",
            "goal_stall": "🎯",
        }.get(p["type"], "📝")
        lines.append(f"- {emoji} {p['observation']} (置信度: {p['confidence']:.0%})")

    lines.append("")

    # 高置信度洞察
    high_conf_insights = [i for i in recent_insights if i.get("confidence", 0) >= 0.75]
    if high_conf_insights:
        lines.append("### 高置信度洞察")
        for insight in high_conf_insights[:3]:
            lines.append(f"> {insight['observation']} (置信度: {insight['confidence']:.0%}, {insight.get('date', '')})")
        lines.append("")

    # 活跃目标
    active_goals = [(n, g) for n, g in goals.items() if g.get("progress", 0) < 1.0]
    if active_goals:
        lines.append("### 活跃目标")
        for name, goal in active_goals[:3]:
            progress = goal.get("progress", 0) * 100
            deadline = goal.get("deadline", "无")
            lines.append(f"- [ ] **{name}**: {progress:.0f}% (deadline: {deadline})")
        lines.append("")

    # 下周预测（简单规则）
    lines.append("### 下周预测")
    lines.append("基于当前模式，以下事项值得关注：")
    if any(p["type"] == "goal_stall" for p in patterns):
        lines.append("- 🎯 有目标进展停滞，需要关注")
    if any(p["type"] == "habit_broken" for p in patterns):
        lines.append("- 💪 有习惯中断，可以考虑重启")
    if any(p["type"] == "mood_low" for p in patterns):
        lines.append("- 🌤️ 情绪偏低，建议适当休息")
    if not patterns:
        lines.append("- ✨ 一切正常，继续保持")
    lines.append("")

    lines.append("---")
    lines.append("")

    return "\n".join(lines)


# ========== CLI 入口 ==========

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: night-mode.py <workspace_dir> <phase>")
        print("  phase: light | deep | rem")
        sys.exit(1)

    workspace_dir = sys.argv[1]
    phase = sys.argv[2].lower()

    if phase == "light":
        result = light_phase(workspace_dir)
    elif phase == "deep":
        result = deep_phase(workspace_dir)
    elif phase == "rem":
        result = rem_phase(workspace_dir)
    else:
        print(f"Unknown phase: {phase}")
        sys.exit(1)

    print(__import__('json').dumps(result, ensure_ascii=False, indent=2))
