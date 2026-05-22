/**
 * Hermes Dream OS - Day Mode (JavaScript)
 * 活跃期处理：Morning Briefing / Midday Check-in / Evening Reflection / Memory Consolidation
 * 融合 Hermes Life OS 的 show, don't remind 原则
 */

import { MemoryHub } from './memory-hub.js';

export const DAY_ACTIONS = {
  BRIEFING: 'briefing',
  CHECKIN: 'checkin',
  REFLECTION: 'reflection',
  CONSOLIDATE: 'consolidate',
  WIN: 'win',
  STRUGGLE: 'struggle'
};

// ========== Day Mode 主函数 ==========

/**
 * Day Mode 入口
 * @param {string} workspaceDir - 工作目录
 * @param {'briefing'|'checkin'|'reflection'|'consolidate'} action - 操作类型
 * @param {...any} args - 额外参数
 */
export function dayMode(workspaceDir, action, ...args) {
  const hub = new MemoryHub(workspaceDir);

  switch (action) {
    case DAY_ACTIONS.BRIEFING:
      return morningBriefing(hub);
    case DAY_ACTIONS.CHECKIN:
      return middayCheckin(hub, ...args);
    case DAY_ACTIONS.REFLECTION:
      return eveningReflection(hub);
    case DAY_ACTIONS.CONSOLIDATE:
      return memoryConsolidation(hub);
    case DAY_ACTIONS.WIN:
      return recordWin(hub, ...args);
    case DAY_ACTIONS.STRUGGLE:
      return recordStruggle(hub, ...args);
    default:
      throw new Error(`Unknown action: ${action}`);
  }
}

// ========== Morning Briefing (07:00) ==========

/**
 * 晨间简报
 * 基于 Hermes Life OS 的 show, don't remind 原则
 */
function morningBriefing(hub) {
  const now = new Date();
  const today = now.toISOString().split('T')[0];
  const weekday = now.toLocaleDateString('en-US', { weekday: 'long' });

  // 1. 能量预测（基于历史数据）
  const recentEnergy = hub.getRecentEnergy(14);
  const weekdayEnergy = recentEnergy.filter(e => {
    try {
      const date = new Date(e.date);
      return date.toLocaleDateString('en-US', { weekday: 'long' }) === weekday;
    } catch {
      return false;
    }
  });

  let energyLevel = '未知（数据不足）';
  if (weekdayEnergy.length > 0) {
    const avgProductivity = weekdayEnergy.reduce((sum, e) => sum + (e.productivity || 5), 0) / weekdayEnergy.length;
    if (avgProductivity >= 7) energyLevel = '高效';
    else if (avgProductivity >= 5) energyLevel = '平稳';
    else energyLevel = '需要调整';
  }

  // 2. 今日目标
  const goals = hub.readGoals();
  const activeGoals = Object.entries(goals)
    .filter(([, goal]) => (goal.progress || 0) < 1.0)
    .map(([name, goal]) => ({
      name,
      progress: goal.progress || 0,
      deadline: goal.deadline || '无'
    }))
    .sort((a, b) => a.progress - b.progress)
    .slice(0, 3);

  // 3. 一个洞察
  const insights = hub.getRecentInsights(14, 0.7);
  const topInsight = insights[0] || null;

  // 4. 今日习惯提醒（未完成的习惯）
  const habits = hub.readHabits();
  const habitReminders = Object.entries(habits)
    .filter(([, data]) => data.last_done !== today)
    .map(([name]) => name)
    .slice(0, 3);

  // 5. 最近的成就（本周）
  const wins = hub.readJsonl(hub.winsPath);
  const recentWins = wins
    .filter(w => {
      try {
        const date = new Date(w.date);
        const daysAgo = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
        return daysAgo <= 7;
      } catch {
        return false;
      }
    })
    .slice(-3);

  const result = {
    type: 'morning_briefing',
    timestamp: now.toISOString(),
    sections: {
      energy_forecast: {
        weekday,
        predicted: energyLevel,
        sample_size: weekdayEnergy.length
      },
      today_goals: {
        active: activeGoals,
        total: Object.keys(goals).length
      },
      insight: topInsight
        ? {
            text: topInsight.observation,
            confidence: topInsight.confidence,
            date: topInsight.date
          }
        : { text: '暂无高置信度洞察', confidence: 0 },
      habit_reminders: habitReminders,
      recent_wins: recentWins.map(w => w.description)
    }
  };

  hub.appendEvent('morning_briefing', { date: today });

  return result;
}

// ========== Midday Check-in (12:00) ==========

/**
 * 午间检查
 * @param {MemoryHub} hub
 * @param {string|null} level - 精力水平: low, medium, high
 * @param {number|null} productivity -生产力评分 1-10
 * @param {string} note - 备注
 */
function middayCheckin(hub, level = null, productivity = null, note = '') {
  const now = new Date();

  // 如果没有提供参数，返回检查表单
  if (!level) {
    return {
      type: 'midday_checkin',
      timestamp: now.toISOString(),
      prompt: '请记录午间精力状态',
      usage: 'day-mode.js <workspace> checkin <level> [productivity] [note]',
      level_options: ['low', 'medium', 'high'],
      example: 'day-mode.js /path/to/workspace checkin high 8'
    };
  }

  const record = hub.recordEnergy(level, note, productivity);

  // 分析上午的进展
  const today = now.toISOString().split('T')[0];
  const wins = hub.readJsonl(hub.winsPath).filter(w => w.date === today);
  const struggles = hub.readJsonl(hub.strugglesPath).filter(w => w.date === today);

  hub.appendEvent('midday_checkin', { level, productivity, note });

  return {
    type: 'midday_checkin',
    timestamp: now.toISOString(),
    record,
    morning_summary: {
      wins_today: wins.length,
      struggles_today: struggles.length
    }
  };
}

// ========== Evening Reflection (18:00) ==========

/**
 * 晚间反思
 */
function eveningReflection(hub) {
  const now = new Date();
  const today = now.toISOString().split('T')[0];

  // 读取今日数据
  const wins = hub.readJsonl(hub.winsPath).filter(w => w.date === today);
  const struggles = hub.readJsonl(hub.strugglesPath).filter(w => w.date === today);
  const moods = hub.getRecentMoods(1);
  const energy = hub.getRecentEnergy(1);

  // 获取未解决的困境
  const unresolvedStruggles = struggles.filter(s => !s.resolved);

  // 计算今日成就总数
  const totalWins = wins.length;

  // 获取活跃目标进度
  const goals = hub.readGoals();
  const activeGoals = Object.entries(goals)
    .filter(([, g]) => (g.progress || 0) < 1.0)
    .map(([name, g]) => ({
      name,
      progress: g.progress || 0,
      deadline: g.deadline || '无'
    }));

  // 获取习惯连续
  const habits = hub.readHabits();
  const habitStreaks = Object.entries(habits)
    .map(([name, data]) => ({
      name,
      streak: data.streak || 0,
      completed_today: data.last_done === today
    }))
    .sort((a, b) => b.streak - a.streak)
    .slice(0, 5);

  const result = {
    type: 'evening_reflection',
    timestamp: now.toISOString(),
    sections: {
      wins_today: wins.map(w => w.description),
      struggles_today: struggles.map(s => s.description),
      unresolved_struggles: unresolvedStruggles.map(s => s.description),
      mood: moods[moods.length - 1] || null,
      energy: energy[energy.length - 1] || null,
      active_goals: activeGoals,
      habit_streaks: habitStreaks
    },
    prompt_suggestions: unresolvedStruggles.length > 0
      ? [`解决困境: ${unresolvedStruggles[0].description}`]
      : []
  };

  hub.appendEvent('evening_reflection', {
    wins_count: wins.length,
    struggles_count: struggles.length
  });

  return result;
}

// ========== Memory Consolidation (23:00) ==========

/**
 * 记忆整合
 * 存储今日模式 + 更新习惯连续
 */
function memoryConsolidation(hub) {
  const now = new Date();
  const today = now.toISOString().split('T')[0];

  // 统计今日数据
  const wins = hub.readJsonl(hub.winsPath).filter(w => w.date === today);
  const struggles = hub.readJsonl(hub.strugglesPath).filter(w => w.date === today);
  const moods = hub.getRecentMoods(1);
  const energy = hub.getRecentEnergy(1);

  // 更新习惯连续
  const habits = hub.readHabits();
  const habitUpdates = [];

  for (const [name, data] of Object.entries(habits)) {
    const completed = data.history?.some(h => h.date === today && h.completed);
    if (completed) {
      habitUpdates.push(hub.updateHabit(name, true));
    }
  }

  // 生成今日摘要
  const summary = {
    date: today,
    wins_count: wins.length,
    struggles_count: struggles.length,
    mood_avg: moods.length > 0
      ? (moods.reduce((sum, m) => sum + (m.score || 5), 0) / moods.length).toFixed(1)
      : null,
    energy_distribution: {
      high: energy.filter(e => e.level === 'high').length,
      medium: energy.filter(e => e.level === 'medium').length,
      low: energy.filter(e => e.level === 'low').length
    },
    habits_updated: Object.keys(habits).length,
    active_streaks: Object.values(habits).filter(h => h.streak > 0).length
  };

  hub.appendEvent('memory_consolidation', summary);

  return {
    type: 'memory_consolidation',
    timestamp: now.toISOString(),
    summary
  };
}

// ========== Record Win/Struggle ==========

/**
 * 记录成就
 */
function recordWin(hub, description) {
  if (!description) {
    return { error: '描述不能为空', usage: 'day-mode.js <workspace> win <description>' };
  }

  const record = hub.recordWin(description);
  hub.appendEvent('win_recorded', { description });

  return {
    success: true,
    type: 'win_recorded',
    record
  };
}

/**
 * 记录困境
 */
function recordStruggle(hub, description, resolved = false) {
  if (!description) {
    return { error: '描述不能为空', usage: 'day-mode.js <workspace> struggle <description> [resolved]' };
  }

  const record = hub.recordStruggle(description, resolved);
  hub.appendEvent('struggle_recorded', { description, resolved });

  return {
    success: true,
    type: 'struggle_recorded',
    record
  };
}

// ========== CLI 入口 ==========

// 使用方式: node day-mode.js <workspace_dir> <action> [args...]
if (import.meta.url === `file://${process.argv[1]}`) {
  const [, , workspaceDir, action, ...args] = process.argv;

  if (!workspaceDir || !action) {
    console.log(`
Hermes Dream OS - Day Mode
==========================

Usage: node day-mode.js <workspace_dir> <action> [args...]

Actions:
  briefing                    - Morning briefing
  checkin <level> [prod] [n]  - Midday check-in (level: low|medium|high)
  reflection                  - Evening reflection
  consolidate                 - Memory consolidation
  win <description>           - Record a win
  struggle <description> [r] - Record a struggle (r: true|false)

Examples:
  node day-mode.js /path/to/workspace briefing
  node day-mode.js /path/to/workspace checkin high 8
  node day-mode.js /path/to/workspace win "完成项目X"
  node day-mode.js /path/to/workspace struggle "会议太多"
`);
    process.exit(1);
  }

  try {
    const result = dayMode(workspaceDir, action, ...args);
    console.log(JSON.stringify(result, null, 2));
  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  }
}
