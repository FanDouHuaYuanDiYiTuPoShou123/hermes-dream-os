"""
Hermes Dream OS — Scoring Module
7维度评分算法：融合 OpenClaw 核心 + Life OS 增强
"""

import math
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


# ========== 常量定义 ==========

DEFAULT_WEIGHTS = {
    "frequency": 0.20,      # 召回频率
    "relevance": 0.25,      # 检索质量
    "diversity": 0.12,      # 查询多样性
    "recency": 0.13,        # 时近性
    "consolidation": 0.08,  # 巩固度
    "insight_value": 0.15,  # 洞察价值（新增）
    "emotional_weight": 0.07,  # 情感权重（新增）
}

MIN_SCORE = 0.75
MIN_RECALL_COUNT = 3
MIN_UNIQUE_QUERIES = 2
RECENCY_HALF_LIFE_DAYS = 14
MAX_PROMOTIONS = 10
MAX_QUERY_HASHES = 32
MAX_RECALL_DAYS = 16
MAX_CONCEPT_TAGS = 8
DAYS_MS = 24 * 60 * 60 * 1000


# ========== 数据结构 ==========

@dataclass
class ScoredCandidate:
    key: str
    path: str
    start_line: int
    end_line: int
    source: str
    snippet: str
    type: str  # recall | insight | habit | goal | mood
    recall_count: int
    daily_count: int
    grounded_count: int
    signal_count: int
    avg_score: float
    max_score: float
    unique_queries: int
    recall_days: list
    concept_tags: list
    claim_hash: Optional[str]
    promoted_at: Optional[str]
    first_recalled_at: str
    last_recalled_at: str
    age_days: float
    score: float
    components: dict  # 各维度得分详情
    # 新增字段
    insight_confidence: float = 0.0
    emotional_context: str = "normal"
    related_goal_active: bool = False


# ========== 工具函数 ==========

def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """clamp 限制在 [min, max] 范围内"""
    return max(min_val, min(max_val, value))


def normalize_snippet(raw: str) -> str:
    """归一化片段文本"""
    if not raw:
        return ""
    return " ".join(raw.strip().split())


def calculate_recency(age_days: float, half_life_days: float = RECENCY_HALF_LIFE_DAYS) -> float:
    """
    计算时近性：指数衰减模型
    age_days: 记忆年龄（天）
    half_life_days: 半衰期（天）
    返回: 0-1 的分数，越新鲜分数越高
    """
    if not math.isfinite(age_days) or age_days < 0:
        return 1.0
    if not math.isfinite(half_life_days) or half_life_days <= 0:
        return 1.0
    lambda_val = math.log(2) / half_life_days
    return math.exp(-lambda_val * age_days)


def calculate_consolidation(recall_days: list) -> float:
    """
    计算巩固度：跨时间分布越好分数越高
    """
    if not recall_days:
        return 0.0

    if len(recall_days) == 1:
        return 0.2

    try:
        parsed = sorted([
            datetime.strptime(d, "%Y-%m-%d").timestamp()
            for d in recall_days if d
        ])
        if len(parsed) <= 1:
            return 0.2

        span_days = max(0, (parsed[-1] - parsed[0]) / DAYS_MS * 1000)

        # spacing: log 缩放
        spacing = clamp(math.log1p(len(parsed) - 1) / math.log1p(4))
        # span: 相对于 7 天的跨度
        span = clamp(span_days / 7)

        return clamp(0.55 * spacing + 0.45 * span)
    except (ValueError, TypeError):
        return 0.0


def calculate_phase_signal_boost(
    light_hits: int,
    rem_hits: int,
    last_light_at: Optional[str],
    last_rem_at: Optional[str],
    now_ms: float
) -> float:
    """
    计算阶段信号加成：
    Light/REM 阶段会给它们处理过的内容额外的分数加成
    """
    LIGHT_BOOST_MAX = 0.06
    REM_BOOST_MAX = 0.09
    HALF_LIFE_DAYS = 14
    HALF_LIFE_MS = HALF_LIFE_DAYS * DAYS_MS

    # 强度：log 缩放
    light_strength = clamp(math.log1p(max(0, light_hits)) / math.log1p(6))
    rem_strength = clamp(math.log1p(max(0, rem_hits)) / math.log1p(6))

    # 时近性
    if last_light_at:
        try:
            light_age_ms = now_ms - datetime.fromisoformat(last_light_at).timestamp() * 1000
            light_recency = math.exp(-math.log(2) / HALF_LIFE_MS * light_age_ms)
        except (ValueError, OSError):
            light_recency = 0.0
    else:
        light_recency = 0.0

    if last_rem_at:
        try:
            rem_age_ms = now_ms - datetime.fromisoformat(last_rem_at).timestamp() * 1000
            rem_recency = math.exp(-math.log(2) / HALF_LIFE_MS * rem_age_ms)
        except (ValueError, OSError):
            rem_recency = 0.0
    else:
        rem_recency = 0.0

    boost = LIGHT_BOOST_MAX * light_strength * light_recency + REM_BOOST_MAX * rem_strength * rem_recency
    return clamp(boost)


# ========== 主评分函数 ==========

def calculate_memory_score(
    entry: dict,
    phase_signals: dict = None,
    weights: dict = None,
    now_ms: float = None
) -> tuple[float, dict]:
    """
    计算记忆条目的晋升分数

    返回: (score, components_dict)
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if now_ms is None:
        now_ms = datetime.now().timestamp() * 1000

    # 提取基础数据
    recall_count = max(0, int(entry.get("recallCount", 0)))
    daily_count = max(0, int(entry.get("dailyCount", 0)))
    grounded_count = max(0, int(entry.get("groundedCount", 0)))
    total_score = max(0, float(entry.get("totalScore", 0)))
    max_score_val = max(0, min(1, float(entry.get("maxScore", 0))))

    signal_count = recall_count + daily_count + grounded_count
    if signal_count <= 0:
        return 0.0, {}

    # 1. frequency（频率）
    frequency = clamp(math.log1p(signal_count) / math.log1p(10))

    # 2. relevance（相关性）
    avg_score = clamp(total_score / max(1, signal_count))
    relevance = avg_score

    # 3. diversity（多样性）
    query_hashes = entry.get("queryHashes", [])
    recall_days = entry.get("recallDays", [])
    context_diversity = max(len(query_hashes), len(recall_days))
    diversity = clamp(context_diversity / 5)

    # 4. recency（时近性）
    last_recalled_at = entry.get("lastRecalledAt", "")
    if last_recalled_at:
        try:
            last_ms = datetime.fromisoformat(last_recalled_at).timestamp() * 1000
            age_days = max(0, (now_ms - last_ms) / DAYS_MS)
        except (ValueError, OSError):
            age_days = 0
    else:
        age_days = 0
    recency = calculate_recency(age_days)

    # 5. consolidation（巩固度）
    consolidation = max(
        calculate_consolidation(recall_days),
        clamp(grounded_count / 3)
    )

    # 6. insight_value（洞察价值）- 新增
    # 来自 life-log 的洞察条目有更高价值
    entry_type = entry.get("type", "recall")
    if entry_type == "insight":
        insight_confidence = entry.get("insightConfidence", 0.5)
        insight_value = max(insight_confidence, avg_score)
    else:
        insight_value = 0.5

    # 7. emotional_weight（情感权重）- 新增
    emotional_context = entry.get("emotionalContext", "normal")
    if emotional_context == "low_mood_day":
        emotional_weight = 1.1
    elif emotional_context == "high_mood_day":
        emotional_weight = 1.0
    else:
        emotional_weight = 1.0

    # 计算阶段信号加成
    phase_boost = 0.0
    if phase_signals and entry.get("key"):
        signals = phase_signals.get("entries", {}).get(entry["key"], {})
        phase_boost = calculate_phase_signal_boost(
            signals.get("lightHits", 0),
            signals.get("remHits", 0),
            signals.get("lastLightAt"),
            signals.get("lastRemAt"),
            now_ms
        )

    # 最终分数
    score = (
        weights["frequency"] * frequency +
        weights["relevance"] * relevance +
        weights["diversity"] * diversity +
        weights["recency"] * recency +
        weights["consolidation"] * consolidation +
        weights["insight_value"] * insight_value * emotional_weight +
        phase_boost
    )

    components = {
        "frequency": frequency,
        "relevance": relevance,
        "diversity": diversity,
        "recency": recency,
        "consolidation": consolidation,
        "insight_value": insight_value,
        "emotional_weight": emotional_weight,
        "phase_boost": phase_boost,
        "total": clamp(score)
    }

    return clamp(score), components


def rank_candidates(
    entries: list,
    phase_signals: dict = None,
    weights: dict = None,
    min_score: float = MIN_SCORE,
    min_recall_count: int = MIN_RECALL_COUNT,
    min_unique_queries: int = MIN_UNIQUE_QUERIES,
    max_age_days: int = -1,
    limit: int = MAX_PROMOTIONS,
    now_ms: float = None
) -> list[ScoredCandidate]:
    """
    对候选记忆条目进行评分和排序

    过滤条件：
    - signal_count >= min_recall_count
    - context_diversity >= min_unique_queries
    - age_days <= max_age_days (if max_age_days >= 0)
    - score >= min_score
    """
    if now_ms is None:
        now_ms = datetime.now().timestamp() * 1000
    if weights is None:
        weights = DEFAULT_WEIGHTS

    scored = []

    for entry in entries:
        # 基础过滤
        recall_count = max(0, int(entry.get("recallCount", 0)))
        daily_count = max(0, int(entry.get("dailyCount", 0)))
        grounded_count = max(0, int(entry.get("groundedCount", 0)))
        signal_count = recall_count + daily_count + grounded_count

        if signal_count < min_recall_count:
            continue

        # 多样性过滤
        query_hashes = entry.get("queryHashes", [])
        recall_days = entry.get("recallDays", [])
        context_diversity = max(len(query_hashes), len(recall_days))
        if context_diversity < min_unique_queries:
            continue

        # 年龄过滤
        last_recalled_at = entry.get("lastRecalledAt", "")
        if last_recalled_at:
            try:
                last_ms = datetime.fromisoformat(last_recalled_at).timestamp() * 1000
                age_days = max(0, (now_ms - last_ms) / DAYS_MS)
            except (ValueError, OSError):
                age_days = 0
        else:
            age_days = 0

        if max_age_days >= 0 and age_days > max_age_days:
            continue

        # 跳过已晋升的（除非明确包含）
        if not entry.get("includePromoted") and entry.get("promotedAt"):
            continue

        # 计算分数
        score, components = calculate_memory_score(
            entry, phase_signals, weights, now_ms
        )

        if score < min_score:
            continue

        # 构建候选对象
        candidate = ScoredCandidate(
            key=entry.get("key", ""),
            path=entry.get("path", ""),
            start_line=int(entry.get("startLine", 0)),
            end_line=int(entry.get("endLine", 0)),
            source=entry.get("source", "memory"),
            snippet=entry.get("snippet", ""),
            type=entry.get("type", "recall"),
            recall_count=recall_count,
            daily_count=daily_count,
            grounded_count=grounded_count,
            signal_count=signal_count,
            avg_score=components.get("relevance", 0),
            max_score=clamp(float(entry.get("maxScore", 0))),
            unique_queries=len(query_hashes),
            recall_days=recall_days,
            concept_tags=entry.get("conceptTags", [])[:MAX_CONCEPT_TAGS],
            claim_hash=entry.get("claimHash"),
            promoted_at=entry.get("promotedAt"),
            first_recalled_at=entry.get("firstRecalledAt", ""),
            last_recalled_at=last_recalled_at,
            age_days=age_days,
            score=score,
            components=components,
            insight_confidence=entry.get("insightConfidence", 0.0),
            emotional_context=entry.get("emotionalContext", "normal"),
            related_goal_active=entry.get("relatedGoalActive", False)
        )
        scored.append(candidate)

    # 排序：分数 > 召回次数 > 路径字母序
    scored.sort(key=lambda x: (-x.score, -x.recall_count, x.path))

    return scored[:limit]


def normalize_weights(weights: dict) -> dict:
    """
    归一化权重，确保所有权重之和为 1
    """
    merged = {**DEFAULT_WEIGHTS, **weights}
    total = sum(merged.values())
    if total <= 0:
        return DEFAULT_WEIGHTS
    return {k: v / total for k, v in merged.items()}
