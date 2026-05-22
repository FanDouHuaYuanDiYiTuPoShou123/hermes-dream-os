/**
 * Hermes Dream OS - Memory Hub (JavaScript)
 * 记忆中枢：管理所有记忆存储和读写操作
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync } from 'fs';
import { dirname, join } from 'path';
import { createHash } from 'crypto';

// ========== 路径工具 ==========

function ensureDir(dirPath) {
  if (!existsSync(dirPath)) {
    mkdirSync(dirPath, { recursive: true });
  }
}

// ========== MemoryHub 类 ==========

export class MemoryHub {
  /**
   * @param {string} workspaceDir - 工作目录路径
   */
  constructor(workspaceDir) {
    this.workspace = workspaceDir;
    this.memoryDir = join(workspaceDir, 'memory');
    this.dreamsDir = join(this.memoryDir, '.dreams');
    this.lifeLogDir = join(this.memoryDir, 'life-log');
    this.patternsDir = join(this.memoryDir, 'patterns');

    this._ensureDirs();
  }

  _ensureDirs() {
    ensureDir(this.memoryDir);
    ensureDir(this.dreamsDir);
    ensureDir(join(this.dreamsDir, 'session-corpus'));
    ensureDir(this.lifeLogDir);
    ensureDir(this.patternsDir);
  }

  // ========== 路径常量 ==========

  get shortTermRecallPath() { return join(this.dreamsDir, 'short-term-recall.json'); }
  get phaseSignalsPath() { return join(this.dreamsDir, 'phase-signals.json'); }
  get eventsPath() { return join(this.dreamsDir, 'events.jsonl'); }
  get moodPath() { return join(this.lifeLogDir, 'mood.jsonl'); }
  get energyPath() { return join(this.lifeLogDir, 'energy.jsonl'); }
  get habitsPath() { return join(this.lifeLogDir, 'habits.json'); }
  get goalsPath() { return join(this.lifeLogDir, 'goals.json'); }
  get insightsPath() { return join(this.lifeLogDir, 'insights.jsonl'); }
  get winsPath() { return join(this.lifeLogDir, 'wins.jsonl'); }
  get strugglesPath() { return join(this.lifeLogDir, 'struggles.jsonl'); }
  get memoryMdPath() { return join(this.memoryDir, 'MEMORY.md'); }
  get dreamsMdPath() { return join(this.memoryDir, 'DREAMS.md'); }

  // ========== 通用读写 ==========

  /**
   * 读取 JSON 文件
   */
  readJson(filePath, defaultValue = null) {
    try {
      if (existsSync(filePath)) {
        return JSON.parse(readFileSync(filePath, 'utf-8'));
      }
    } catch (e) {
      // 返回默认值
    }
    return defaultValue;
  }

  /**
   * 写入 JSON 文件
   */
  writeJson(filePath, data) {
    ensureDir(dirname(filePath));
    writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
  }

  /**
   * 追加 JSONL 记录
   */
  appendJsonl(filePath, record) {
    ensureDir(dirname(filePath));
    const line = JSON.stringify(record, null) + '\n';
    appendFileSync(filePath, line, 'utf-8');
  }

  /**
   * 读取 JSONL 文件
   * @param {string} filePath
   * @param {number|null} limit
   * @returns {Object[]}
   */
  readJsonl(filePath, limit = null) {
    const records = [];
    if (!existsSync(filePath)) return records;

    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').filter(l => l.trim());

    for (let i = 0; i < lines.length; i++) {
      if (limit && i >= limit) break;
      try {
        records.push(JSON.parse(lines[i]));
      } catch (e) {
        // 跳过无效行
      }
    }
    return records;
  }

  // ========== Short-term Recall ==========

  readShortTermRecall() {
    return this.readJson(this.shortTermRecallPath, { version: 1, updatedAt: '', entries: {} });
  }

  writeShortTermRecall(store) {
    this.writeJson(this.shortTermRecallPath, store);
  }

  // ========== Phase Signals ==========

  readPhaseSignals() {
    return this.readJson(this.phaseSignalsPath, { version: 1, updatedAt: '', entries: {} });
  }

  writePhaseSignals(store) {
    this.writeJson(this.phaseSignalsPath, store);
  }

  // ========== Life Log ==========

  /**
   * 记录情感
   */
  recordMood(score, note = '', triggers = [], time = null) {
    const now = new Date();
    const record = {
      date: now.toISOString().split('T')[0],
      time: time || now.toTimeString().slice(0, 5),
      score: Math.max(1, Math.min(10, score)),
      note,
      triggers: triggers || []
    };
    this.appendJsonl(this.moodPath, record);
    return record;
  }

  /**
   * 获取最近 N 天的情感记录
   */
  getRecentMoods(days = 7) {
    const records = this.readJsonl(this.moodPath);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().split('T')[0];
    return records.filter(r => (r.date || '') >= cutoffStr);
  }

  /**
   * 记录精力
   */
  recordEnergy(level, context = '', productivity = null, time = null) {
    const now = new Date();
    const validLevels = ['low', 'medium', 'high'];
    const record = {
      date: now.toISOString().split('T')[0],
      time: time || now.toTimeString().slice(0, 5),
      level: validLevels.includes(level) ? level : 'medium',
      context,
    };
    if (productivity) {
      record.productivity = Math.max(1, Math.min(10, productivity));
    }
    this.appendJsonl(this.energyPath, record);
    return record;
  }

  /**
   * 获取最近 N 天的精力记录
   */
  getRecentEnergy(days = 7) {
    const records = this.readJsonl(this.energyPath);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().split('T')[0];
    return records.filter(r => (r.date || '') >= cutoffStr);
  }

  /**
   * 记录洞察
   */
  recordInsight(observation, confidence, source = 'memory', patternBased = true) {
    const record = {
      date: new Date().toISOString().split('T')[0],
      observation,
      confidence: Math.max(0.0, Math.min(1.0, confidence)),
      patternBased,
      source
    };
    this.appendJsonl(this.insightsPath, record);
    return record;
  }

  /**
   * 获取最近 N 天的高置信度洞察
   */
  getRecentInsights(days = 7, minConfidence = 0.0) {
    const records = this.readJsonl(this.insightsPath);
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - days);
    const cutoffStr = cutoff.toISOString().split('T')[0];
    return records.filter(r =>
      (r.date || '') >= cutoffStr &&
      (r.confidence || 0) >= minConfidence
    );
  }

  /**
   * 记录成就
   */
  recordWin(description, category = 'general') {
    const record = {
      date: new Date().toISOString().split('T')[0],
      description,
      category
    };
    this.appendJsonl(this.winsPath, record);
    return record;
  }

  /**
   * 记录困境
   */
  recordStruggle(description, resolved = false) {
    const record = {
      date: new Date().toISOString().split('T')[0],
      description,
      resolved
    };
    this.appendJsonl(this.strugglesPath, record);
    return record;
  }

  // ========== Habits ==========

  readHabits() {
    return this.readJson(this.habitsPath, {});
  }

  /**
   * 更新习惯
   */
  updateHabit(name, completed, note = '') {
    const habits = this.readHabits();
    const today = new Date().toISOString().split('T')[0];

    if (!habits[name]) {
      habits[name] = { streak: 0, last_done: null, history: [] };
    }

    const habit = habits[name];
    habit.history = habit.history || [];
    habit.history.push({ date: today, completed, note });

    // 保持最近 90 天历史
    habit.history = habit.history.slice(-90);

    if (completed) {
      const lastDone = habit.last_done;
      if (lastDone) {
        const lastDate = new Date(lastDone);
        const daysDiff = Math.floor((Date.now() - lastDate.getTime()) / (1000 * 60 * 60 * 24));
        if (daysDiff === 1) {
          habit.streak += 1;
        } else if (daysDiff > 1) {
          habit.streak = 1;
        }
      } else {
        habit.streak = 1;
      }
      habit.last_done = today;
    }

    habits[name] = habit;
    this.writeJson(this.habitsPath, habits);
    return habit;
  }

  // ========== Goals ==========

  readGoals() {
    return this.readJson(this.goalsPath, {});
  }

  /**
   * 更新目标
   */
  updateGoal(name, progress = null, deadline = null, milestone = null) {
    const goals = this.readGoals();
    const today = new Date().toISOString().split('T')[0];

    if (!goals[name]) {
      goals[name] = {
        progress: 0.0,
        deadline: deadline || '',
        lastUpdated: today,
        milestones: []
      };
    }

    const goal = goals[name];
    if (progress !== null) {
      goal.progress = Math.max(0.0, Math.min(1.0, progress));
    }
    if (deadline) {
      goal.deadline = deadline;
    }
    goal.lastUpdated = today;

    if (milestone) {
      const existingIdx = goal.milestones.findIndex(m => m.title === milestone.title);
      if (existingIdx >= 0) {
        goal.milestones[existingIdx] = { ...goal.milestones[existingIdx], ...milestone };
      } else {
        goal.milestones.push(milestone);
      }
    }

    goals[name] = goal;
    this.writeJson(this.goalsPath, goals);
    return goal;
  }

  // ========== Events ==========

  /**
   * 追加事件
   */
  appendEvent(eventType, ...args) {
    const record = {
      type: eventType,
      timestamp: new Date().toISOString(),
    };
    // 合并额外参数
    if (args.length === 1 && typeof args[0] === 'object') {
      Object.assign(record, args[0]);
    }
    this.appendJsonl(this.eventsPath, record);
    return record;
  }

  // ========== Utilities ==========

  /**
   * 生成查询哈希
   */
  hashQuery(query) {
    return createHash('sha1').update(query.toLowerCase().trim()).digest('hex').slice(0, 12);
  }

  /**
   * 生成片段哈希
   */
  hashSnippet(snippet) {
    const normalized = snippet.trim().split(/\s+/).join(' ');
    return createHash('sha1').update(normalized).digest('hex').slice(0, 12);
  }

  /**
   * 返回今天的日期字符串
   */
  today() {
    return new Date().toISOString().split('T')[0];
  }

  /**
   * 格式化 ISO 日期
   */
  formatIsoDay(date = null) {
    const d = date || new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
}
