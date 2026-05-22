/**
 * Hermes Dream OS - Night Mode (JavaScript)
 * 休眠期处理：Light Phase / Deep Phase / REM Phase
 */

import { MemoryHub } from './memory-hub.js';
import { rankCandidates } from './scoring.js';
import { extractConcepts } from './concept-tagging.js';
import { readFileSync, writeFileSync, appendFileSync, existsSync } from 'fs';

export const NIGHT_PHASES = {
  LIGHT: 'light',   // 23:30 - 浅睡整理
  DEEP: 'deep',     // 01:00 - 深睡晋升
  REM: 'rem'        // 03:00 - REM 梦境
};

// ========== Night Mode 主函数 ==========

/**
 * Night Mode 入口
 * @param {string} workspaceDir - 工作目录
 * @param {'light'|'deep'|'rem'} phase - 睡眠阶段
 */
export function nightMode(workspaceDir, phase) {
  const hub = new MemoryHub(workspaceDir);
  const now = new Date();

  hub.appendEvent('night_phase_start', { phase, timestamp: now.toISOString() });

  let result;
  switch (phase) {
    case NIGHT_PHASES.LIGHT:
      result = lightPhase(hub, now);
      break;
    case NIGHT_PHASES.DEEP:
      result = deepPhase(hub, now);
      break;
    case NIGHT_PHASES.REM:
      result = remPhase(hub, now);
      break;
    default:
      throw new Error(`Unknown phase: ${phase}`);
  }

  hub.appendEvent('night_phase_end', { phase, timestamp: new Date().toISOString(), result });

  return result;
}

// ========== Light Phase (23:30) ==========

/**
 * 浅睡阶段：整理短期记忆，去重
 */
function lightPhase(hub, now) {
  // 读取短期记忆
  const shortTerm = hub.readShortTermRecall();

  // 读取阶段信号
  const phaseSignals = hub.readPhaseSignals();

  // 更新 Light 阶段信号
  phaseSignals.entries = phaseSignals.entries || {};
  phaseSignals.entries['_light'] = {
    lightHits: (phaseSignals.entries._light?.lightHits || 0) + 1,
    lastLightAt: now.toISOString()
  };
  phaseSignals.updatedAt = now.toISOString();
  hub.writePhaseSignals(phaseSignals);

  // 统计本次处理的条目
  let dedupCount = 0;
  let mergeCount = 0;

  // 1. 去重：合并相同 queryHash 的条目
  const entries = shortTerm.entries || {};
  const queryGroups = {};

  for (const [key, entry] of Object.entries(entries)) {
    const queryHashes = entry.queryHashes || [];
    for (const qh of queryHashes) {
      if (!queryGroups[qh]) queryGroups[qh] = [];
      queryGroups[qh].push({ key, entry });
    }
  }

  // 合并相同 queryHash 的条目
  for (const [qh, group] of Object.entries(queryGroups)) {
    if (group.length > 1) {
      // 保留最新的，合并其他的信息
      const merged = group.reduce((acc, { entry }) => {
        acc.recallCount = (acc.recallCount || 0) + (entry.recallCount || 0);
        acc.dailyCount = (acc.dailyCount || 0) + (entry.dailyCount || 0);
        acc.groundedCount = (acc.groundedCount || 0) + (entry.groundedCount || 0);
        acc.totalScore = (acc.totalScore || 0) + (entry.totalScore || 0);
        acc.maxScore = Math.max(acc.maxScore || 0, entry.maxScore || 0);

        // 合并日期
        const days = [...(acc.recallDays || []), ...(entry.recallDays || [])];
        acc.recallDays = [...new Set(days)].slice(-10);

        // 合并 queryHashes
        acc.queryHashes = [...new Set([...(acc.queryHashes || []), ...(entry.queryHashes || [])])].slice(-32);

        return acc;
      }, { ...group[0].entry });

      // 保留第一个 key
      entries[group[0].key] = merged;
      dedupCount += group.length - 1;
      mergeCount++;
    }
  }

  shortTerm.entries = entries;
  shortTerm.updatedAt = now.toISOString();
  hub.writeShortTermRecall(shortTerm);

  return {
    phase: NIGHT_PHASES.LIGHT,
    timestamp: now.toISOString(),
    processed: {
      dedupCount,
      mergeCount,
      totalEntries: Object.keys(entries).length
    },
    nextPhase: NIGHT_PHASES.DEEP
  };
}

// ========== Deep Phase (01:00) ==========

/**
 * 深睡阶段：评分晋升到 MEMORY.md
 */
function deepPhase(hub, now) {
  // 读取短期记忆
  const shortTerm = hub.readShortTermRecall();

  // 读取阶段信号
  const phaseSignals = hub.readPhaseSignals();

  // 更新 Deep 阶段信号
  phaseSignals.entries = phaseSignals.entries || {};
  phaseSignals.entries['_deep'] = {
    deepHits: (phaseSignals.entries._deep?.deepHits || 0) + 1,
    lastDeepAt: now.toISOString()
  };
  phaseSignals.updatedAt = now.toISOString();
  hub.writePhaseSignals(phaseSignals);

  // 读取 Life Log 获取情感上下文
  const moods = hub.getRecentMoods(3);
  const avgMood = moods.length > 0
    ? moods.reduce((sum, m) => sum + (m.score || 5), 0) / moods.length
    : 5;

  // 设置情感上下文
  let emotionalContext = 'normal';
  if (avgMood < 4) emotionalContext = 'low_mood_day';
  else if (avgMood > 7) emotionalContext = 'high_mood_day';

  // 为条目添加情感上下文
  const entries = Object.values(shortTerm.entries || {});
  for (const entry of entries) {
    entry.emotionalContext = emotionalContext;
  }

  // 执行评分
  const candidates = rankCandidates(entries, phaseSignals, null, {
    minScore: 0.5,
    minRecallCount: 2,
    minUniqueQueries: 1,
    maxAgeDays: 16,
    limit: 10
  });

  // 获取当前 MEMORY.md 内容
  let memoryMd = '';
  try {
    if (existsSync(hub.memoryMdPath)) {
      memoryMd = readFileSync(hub.memoryMdPath, 'utf-8');
    }
  } catch (e) {
    // 文件不存在或读取失败
  }

  // 生成晋升条目
  const promoted = [];
  for (const candidate of candidates) {
    if (candidate.score >= 0.65) {
      promoted.push({
        key: candidate.key,
        snippet: candidate.snippet,
        score: candidate.score,
        recallCount: candidate.recallCount,
        type: candidate.type,
        conceptTags: candidate.conceptTags
      });

      // 更新短期记忆：标记已晋升
      if (shortTerm.entries[candidate.key]) {
        shortTerm.entries[candidate.key].promotedAt = now.toISOString();
      }
    }
  }

  // 写入 MEMORY.md
  if (promoted.length > 0) {
    const newSection = formatMemorySection(promoted, now);
    memoryMd = memoryMd.replace(/<!-- DREAM_OS_SECTION -->/g, `<!-- DREAM_OS_SECTION -->\n${newSection}`);
    writeFileSync(hub.memoryMdPath, memoryMd, 'utf-8');
  }

  shortTerm.updatedAt = now.toISOString();
  hub.writeShortTermRecall(shortTerm);

  return {
    phase: NIGHT_PHASES.DEEP,
    timestamp: now.toISOString(),
    emotionalContext,
    candidatesFound: candidates.length,
    promoted: promoted.length,
    topCandidate: candidates[0] || null,
    nextPhase: NIGHT_PHASES.REM
  };
}

// ========== REM Phase (03:00) ==========

/**
 * REM 阶段：主题提取，Dream Diary
 */
function remPhase(hub, now) {
  // 读取短期记忆
  const shortTerm = hub.readShortTermRecall();

  // 读取阶段信号
  const phaseSignals = hub.readPhaseSignals();

  // 更新 REM 阶段信号
  phaseSignals.entries = phaseSignals.entries || {};
  phaseSignals.entries['_rem'] = {
    remHits: (phaseSignals.entries._rem?.remHits || 0) + 1,
    lastRemAt: now.toISOString()
  };
  phaseSignals.updatedAt = now.toISOString();
  hub.writePhaseSignals(phaseSignals);

  // 获取最近未处理的高分条目
  const entries = Object.values(shortTerm.entries || {})
    .filter(e => !e.promotedAt && (e.recallCount || 0) >= 2);

  // 提取主题
  const themes = [];
  const snippets = entries.map(e => e.snippet).filter(Boolean);

  if (snippets.length > 0) {
    // 合并所有片段提取概念
    const allConcepts = [];
    for (const snippet of snippets) {
      allConcepts.push(...extractConcepts(snippet, 3));
    }

    // 统计概念频率
    const conceptCounts = {};
    for (const concept of allConcepts) {
      conceptCounts[concept] = (conceptCounts[concept] || 0) + 1;
    }

    // 取最常见的概念作为主题
    const sortedConcepts = Object.entries(conceptCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([concept]) => concept);

    themes.push(...sortedConcepts);
  }

  // 生成 Dream Diary 条目
  const dreamEntry = {
    date: now.toISOString().split('T')[0],
    timestamp: now.toISOString(),
    themes,
    entryCount: entries.length,
    insights: entries
      .filter(e => (e.recallCount || 0) >= 3)
      .map(e => ({
        snippet: e.snippet?.slice(0, 100),
        recallCount: e.recallCount
      }))
  };

  // 追加到 DREAMS.md
  appendDreamDiary(hub, dreamEntry);

  return {
    phase: NIGHT_PHASES.REM,
    timestamp: now.toISOString(),
    themes,
    entriesProcessed: entries.length,
    dreamEntry
  };
}

// ========== 辅助函数 ==========

/**
 * 格式化 MEMORY.md 内容块
 */
function formatMemorySection(entries, now) {
  const lines = [
    `\n## 🌙 Dream OS晋升 - ${now.toISOString().split('T')[0]}`,
    ''
  ];

  for (const entry of entries) {
    lines.push(`### ${entry.type === 'insight' ? '💡' : '📝'} ${entry.key}`);
    lines.push(`> ${entry.snippet}`);
    lines.push('');
    lines.push(`- 分数: ${entry.score.toFixed(3)}`);
    lines.push(`- 召回: ${entry.recallCount}次`);
    if (entry.conceptTags?.length > 0) {
      lines.push(`- 标签: ${entry.conceptTags.join(', ')}`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * 追加 Dream Diary 条目
 */
function appendDreamDiary(hub, entry) {
  let content = '';
  if (existsSync(hub.dreamsMdPath)) {
    content = readFileSync(hub.dreamsMdPath, 'utf-8');
  } else {
    content = '# 🌙 Dream Diary\n\n';
  }

  const lines = [
    `\n## 🌙 ${entry.date}`,
    `**主题**: ${entry.themes.join(' | ') || '无明显主题'}`,
    `**处理条目**: ${entry.entryCount}个`,
    ''
  ];

  if (entry.insights?.length > 0) {
    lines.push('### 洞察');
    for (const insight of entry.insights) {
      lines.push(`- ${insight.snippet}... (${insight.recallCount}次召回)`);
    }
    lines.push('');
  }

  content += lines.join('\n');
  writeFileSync(hub.dreamsMdPath, content, 'utf-8');
}
