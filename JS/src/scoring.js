/**
 * Hermes Dream OS - Scoring Module (JavaScript)
 * 7维度评分算法
 */

// ========== 常量定义 ==========

export const DEFAULT_WEIGHTS = {
  frequency: 0.20,        // 召回频率
  relevance: 0.25,        // 检索质量
  diversity: 0.12,        // 查询多样性
  recency: 0.13,          // 时近性
  consolidation: 0.08,    // 巩固度
  insight_value: 0.15,    // 洞察价值（新增）
  emotional_weight: 0.07,   // 情感权重（新增）
};

export const MIN_SCORE = 0.75;
export const MIN_RECALL_COUNT = 3;
export const MIN_UNIQUE_QUERIES = 2;
export const RECENCY_HALF_LIFE_DAYS = 14;
export const MAX_PROMOTIONS = 10;
export const MAX_QUERY_HASHES = 32;
export const MAX_RECALL_DAYS = 16;
export const MAX_CONCEPT_TAGS = 8;
export const DAYS_MS = 24 * 60 * 60 * 1000;

// ========== 工具函数 ==========

/**
 * clamp 限制在 [min, max] 范围内
 */
export function clamp(value, minVal = 0.0, maxVal = 1.0) {
  return Math.max(minVal, Math.min(maxVal, value));
}

/**
 * 归一化片段文本
 */
export function normalizeSnippet(raw) {
  if (!raw) return '';
  return raw.trim().split(/\s+/).join(' ');
}

/**
 * 计算时近性：指数衰减模型
 * @param {number} ageDays - 记忆年龄（天）
 * @param {number} halfLifeDays - 半衰期（天）
 * @returns {number} 0-1 的分数，越新鲜分数越高
 */
export function calculateRecency(ageDays, halfLifeDays = RECENCY_HALF_LIFE_DAYS) {
  if (!Number.isFinite(ageDays) || ageDays < 0) return 1.0;
  if (!Number.isFinite(halfLifeDays) || halfLifeDays <= 0) return 1.0;
  const lambdaVal = Math.log(2) / halfLifeDays;
  return Math.exp(-lambdaVal * ageDays);
}

/**
 * 计算巩固度：跨时间分布越好分数越高
 * @param {string[]} recallDays - 召回日期数组 ['2026-05-20', '2026-05-22']
 */
export function calculateConsolidation(recallDays) {
  if (!recallDays || recallDays.length === 0) return 0.0;

  if (recallDays.length === 1) return 0.2;

  try {
    const parsed = recallDays
      .filter(d => d)
      .map(d => new Date(d).getTime())
      .sort((a, b) => a - b);

    if (parsed.length <= 1) return 0.2;

    const spanDays = Math.max(0, (parsed[parsed.length - 1] - parsed[0]) / DAYS_MS);

    // spacing: log 缩放
    const spacing = clamp(Math.log1p(parsed.length - 1) / Math.log1p(4));
    // span: 相对于 7 天的跨度
    const span = clamp(spanDays / 7);

    return clamp(0.55 * spacing + 0.45 * span);
  } catch (e) {
    return 0.0;
  }
}

/**
 * 计算阶段信号加成
 * @param {number} lightHits - Light 阶段命中数
 * @param {number} remHits - REM 阶段命中数
 * @param {string|null} lastLightAt - 上次 Light 时间 ISO 字符串
 * @param {string|null} lastRemAt - 上次 REM 时间 ISO 字符串
 * @param {number} nowMs - 当前时间戳（毫秒）
 */
export function calculatePhaseSignalBoost(lightHits, remHits, lastLightAt, lastRemAt, nowMs) {
  const LIGHT_BOOST_MAX = 0.06;
  const REM_BOOST_MAX = 0.09;
  const HALF_LIFE_MS = RECENCY_HALF_LIFE_DAYS * DAYS_MS;

  // 强度：log 缩放
  const lightStrength = clamp(Math.log1p(Math.max(0, lightHits)) / Math.log1p(6));
  const remStrength = clamp(Math.log1p(Math.max(0, remHits)) / Math.log1p(6));

  // 时近性
  const lightRecency = lastLightAt
    ? Math.exp(-Math.log(2) / HALF_LIFE_MS * (nowMs - new Date(lastLightAt).getTime()))
    : 0.0;
  const remRecency = lastRemAt
    ? Math.exp(-Math.log(2) / HALF_LIFE_MS * (nowMs - new Date(lastRemAt).getTime()))
    : 0.0;

  const boost = LIGHT_BOOST_MAX * lightStrength * lightRecency + REM_BOOST_MAX * remStrength * remRecency;
  return clamp(boost);
}

/**
 * 计算记忆条目的晋升分数
 * @param {Object} entry - 记忆条目
 * @param {Object|null} phaseSignals - 阶段信号
 * @param {Object|null} weights - 权重配置
 * @param {number|null} nowMs - 当前时间戳
 * @returns {{score: number, components: Object}}
 */
export function calculateMemoryScore(entry, phaseSignals = null, weights = null, nowMs = null) {
  if (!weights) weights = DEFAULT_WEIGHTS;
  if (!nowMs) nowMs = Date.now();

  // 提取基础数据
  const recallCount = Math.max(0, parseInt(entry.recallCount || entry.recall_count || 0));
  const dailyCount = Math.max(0, parseInt(entry.dailyCount || entry.daily_count || 0));
  const groundedCount = Math.max(0, parseInt(entry.groundedCount || entry.grounded_count || 0));
  const totalScore = Math.max(0, parseFloat(entry.totalScore || entry.total_score || 0));
  const maxScoreVal = Math.max(0, Math.min(1, parseFloat(entry.maxScore || entry.max_score || 0)));

  const signalCount = recallCount + dailyCount + groundedCount;
  if (signalCount <= 0) return { score: 0.0, components: {} };

  // 1. frequency（频率）
  const frequency = clamp(Math.log1p(signalCount) / Math.log1p(10));

  // 2. relevance（相关性）
  const avgScore = clamp(totalScore / Math.max(1, signalCount));
  const relevance = avgScore;

  // 3. diversity（多样性）
  const queryHashes = entry.queryHashes || entry.query_hashes || [];
  const recallDays = entry.recallDays || entry.recall_days || [];
  const contextDiversity = Math.max(queryHashes.length, recallDays.length);
  const diversity = clamp(contextDiversity / 5);

  // 4. recency（时近性）
  const lastRecalledAt = entry.lastRecalledAt || entry.last_recalled_at || '';
  const ageDays = lastRecalledAt
    ? Math.max(0, (nowMs - new Date(lastRecalledAt).getTime()) / DAYS_MS)
    : 0;
  const recency = calculateRecency(ageDays);

  // 5. consolidation（巩固度）
  const consolidation = Math.max(
    calculateConsolidation(recallDays),
    clamp(groundedCount / 3)
  );

  // 6. insight_value（洞察价值）- 新增
  const entryType = entry.type || 'recall';
  let insightValue = 0.5;
  if (entryType === 'insight') {
    const insightConfidence = parseFloat(entry.insightConfidence || entry.insight_confidence || 0.5);
    insightValue = Math.max(insightConfidence, avgScore);
  }

  // 7. emotional_weight（情感权重）- 新增
  const emotionalContext = entry.emotionalContext || entry.emotional_context || 'normal';
  let emotionalWeight = 1.0;
  if (emotionalContext === 'low_mood_day') {
    emotionalWeight = 1.1;
  } else if (emotionalContext === 'high_mood_day') {
    emotionalWeight = 1.0;
  }

  // 计算阶段信号加成
  let phaseBoost = 0.0;
  if (phaseSignals && entry.key) {
    const signals = (phaseSignals.entries || {})[entry.key] || {};
    phaseBoost = calculatePhaseSignalBoost(
      signals.lightHits || 0,
      signals.remHits || 0,
      signals.lastLightAt || null,
      signals.lastRemAt || null,
      nowMs
    );
  }

  // 最终分数
  const score = (
    weights.frequency * frequency +
    weights.relevance * relevance +
    weights.diversity * diversity +
    weights.recency * recency +
    weights.consolidation * consolidation +
    weights.insight_value * insightValue * emotionalWeight +
    phaseBoost
  );

  const components = {
    frequency,
    relevance,
    diversity,
    recency,
    consolidation,
    insight_value: insightValue,
    emotional_weight: emotionalWeight,
    phase_boost: phaseBoost,
    total: clamp(score)
  };

  return { score: clamp(score), components };
}

/**
 * 对候选记忆条目进行评分和排序
 * @param {Object[]} entries - 记忆条目数组
 * @param {Object|null} phaseSignals - 阶段信号
 * @param {Object|null} weights - 权重配置
 * @param {Object} options - 选项 {minScore, minRecallCount, minUniqueQueries, maxAgeDays, limit}
 * @param {number|null} nowMs - 当前时间戳
 * @returns {Object[]} 排序后的候选数组
 */
export function rankCandidates(entries, phaseSignals = null, weights = null, options = {}, nowMs = null) {
  if (!nowMs) nowMs = Date.now();
  if (!weights) weights = DEFAULT_WEIGHTS;

  const {
    minScore = MIN_SCORE,
    minRecallCount = MIN_RECALL_COUNT,
    minUniqueQueries = MIN_UNIQUE_QUERIES,
    maxAgeDays = -1,
    limit = MAX_PROMOTIONS
  } = options;

  const scored = [];

  for (const entry of entries) {
    // 基础过滤
    const recallCount = Math.max(0, parseInt(entry.recallCount || entry.recall_count || 0));
    const dailyCount = Math.max(0, parseInt(entry.dailyCount || entry.daily_count || 0));
    const groundedCount = Math.max(0, parseInt(entry.groundedCount || entry.grounded_count || 0));
    const signalCount = recallCount + dailyCount + groundedCount;

    if (signalCount < minRecallCount) continue;

    // 多样性过滤
    const queryHashes = entry.queryHashes || entry.query_hashes || [];
    const recallDays = entry.recallDays || entry.recall_days || [];
    const contextDiversity = Math.max(queryHashes.length, recallDays.length);
    if (contextDiversity < minUniqueQueries) continue;

    // 年龄过滤
    const lastRecalledAt = entry.lastRecalledAt || entry.last_recalled_at || '';
    const ageDays = lastRecalledAt
      ? Math.max(0, (nowMs - new Date(lastRecalledAt).getTime()) / DAYS_MS)
      : 0;
    if (maxAgeDays >= 0 && ageDays > maxAgeDays) continue;

    // 跳过已晋升的（除非明确包含）
    if (!entry.includePromoted && entry.promotedAt) continue;

    // 计算分数
    const { score, components } = calculateMemoryScore(entry, phaseSignals, weights, nowMs);
    if (score < minScore) continue;

    // 构建候选对象
    const candidate = {
      key: entry.key || '',
      path: entry.path || '',
      startLine: parseInt(entry.startLine || entry.start_line || 0),
      endLine: parseInt(entry.endLine || entry.end_line || 0),
      source: entry.source || 'memory',
      snippet: entry.snippet || '',
      type: entry.type || 'recall',
      recallCount,
      dailyCount,
      groundedCount,
      signalCount,
      avgScore: components.relevance || 0,
      maxScore: clamp(parseFloat(entry.maxScore || entry.max_score || 0)),
      uniqueQueries: queryHashes.length,
      recallDays,
      conceptTags: (entry.conceptTags || entry.concept_tags || []).slice(0, MAX_CONCEPT_TAGS),
      claimHash: entry.claimHash || entry.claim_hash || null,
      promotedAt: entry.promotedAt || null,
      firstRecalledAt: entry.firstRecalledAt || entry.first_recalled_at || '',
      lastRecalledAt,
      ageDays,
      score,
      components,
      insightConfidence: parseFloat(entry.insightConfidence || entry.insight_confidence || 0.0),
      emotionalContext: entry.emotionalContext || entry.emotional_context || 'normal',
      relatedGoalActive: entry.relatedGoalActive || entry.related_goal_active || false
    };
    scored.push(candidate);
  }

  // 排序：分数 > 召回次数 > 路径字母序
  scored.sort((a, b) =>
    -a.score + b.score ||
    -a.recallCount + b.recallCount ||
    a.path.localeCompare(b.path)
  );

  return scored.slice(0, limit);
}

/**
 * 归一化权重，确保所有权重之和为 1
 */
export function normalizeWeights(weights) {
  const merged = { ...DEFAULT_WEIGHTS, ...weights };
  const total = Object.values(merged).reduce((sum, v) => sum + v, 0);
  if (total <= 0) return DEFAULT_WEIGHTS;
  return Object.fromEntries(
    Object.entries(merged).map(([k, v]) => [k, v / total])
  );
}
