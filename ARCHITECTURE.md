# Hermes Dream OS - Architecture

## Overview

Hermes Dream OS 是适配 Hermes Agent 的个人记忆操作系统，根据昼夜节律运作：
- **Day Mode (07:00-23:00)**: 白天收集生活记录
- **Night Mode (23:00-07:00)**: 夜间整合记忆

## Dual-Mode Architecture

```
Day (07:00-23:00)          Night (23:00-07:00)
┌──────────────┐           ┌─────────────────────────────────┐
│  Life OS     │  events  │  Dream OS                       │
│  Morning     │ ───────► │  23:30 Light Phase (整理)       │
│  Midday      │  stored  │  01:00 Deep Phase (评分晋升)    │
│  Evening     │  in      │  03:00 REM Phase (梦境日记)     │
│  Reflection  │  memory  │                                 │
└──────────────┘           └─────────────────────────────────┘
```

## Project Structure

```
hermes-dream-os/
├── JS/
│   ├── package.json
│   ├── py_dream.py           # Python Wrapper
│   └── src/
│       ├── scoring.js        # 7维度评分算法
│       ├── concept-tagging.js # 多语言概念标签
│       ├── memory-hub.js     # 记忆中枢
│       ├── night-mode.js     # 夜间三阶段
│       ├── day-mode.js       # 日间操作
│       └── cli.js            # CLI 统一入口
```

## 7-Dimensional Scoring

| Signal | Weight | Source |
|--------|--------|--------|
| frequency | 0.20 | recallCount |
| relevance | 0.25 | avgScore |
| diversity | 0.12 | queryDays |
| recency | 0.13 | ageDays |
| consolidation | 0.08 | recallDays |
| insight_value | 0.15 | life-log |
| emotional_weight | 0.07 | mood |

## Night Mode Phases

### Phase 1: Light (23:30)
- Deduplicate short-term memories
- Defragment fragmented concepts
- Merge entries with same queryHash

### Phase 2: Deep (01:00)
- 7-dimensional scoring of short-term memories
- Promote memories scoring ≥ 0.75 to long-term
- Emotional context affects scoring (low mood day = 1.1x weight)

### Phase 3: REM (03:00)
- Theme extraction from high-scoring memories
- Dream diary generation
- Pattern reinforcement

## Data Storage

- `<workspace>/memory/.dreams/short-term-recall.json` - Short-term memory
- `<workspace>/memory/.dreams/phase-signals.json` - Night phase tracking
- `<workspace>/memory/life-log/mood.jsonl` - Mood records
- `<workspace>/memory/life-log/energy.jsonl` - Energy records
- `<workspace>/memory/life-log/habits.json` - Habit streaks
- `<workspace>/memory/life-log/goals.json` - Goal progress
- `<workspace>/memory/life-log/insights.jsonl` - Insights
- `<workspace>/memory/life-log/wins.jsonl` - Wins
- `<workspace>/memory/life-log/struggles.jsonl` - Struggles
- `<workspace>/memory/MEMORY.md` - Long-term memories
- `<workspace>/memory/DREAMS.md` - Dream diary

## Cron Schedule

| Time | Action | Command |
|------|--------|---------|
| 07:00 | Morning Briefing | `node cli.js day-mode <workspace> briefing` |
| 12:00 | Midday Check-in | `node cli.js day-mode <workspace> checkin <level> [productivity] [note]` |
| 18:00 | Evening Reflection | `node cli.js day-mode <workspace> reflection` |
| 23:00 | Memory Consolidation | `node cli.js day-mode <workspace> consolidate` |
| 23:30 | Night Light Phase | `node cli.js night-mode <workspace> light` |
| 01:00 | Night Deep Phase | `node cli.js night-mode <workspace> deep` |
| 03:00 | Night REM Phase | `node cli.js night-mode <workspace> rem` |
| Mon 08:00 | Weekly Review | Summary from previous week's insights |

## Key Files

### scoring.js
- `clamp(value, min, max)` - Constrain value to range
- `calculateRecency(ageDays, halfLifeDays)` - Exponential decay
- `calculateConsolidation(recallCount, recallDays)` - Consolidation score
- `rankCandidates(candidates, maxCount)` - Sort and limit candidates
- `calculateMemoryScore(memory, weights)` - Full 7-dim scoring

### concept-tagging.js
- `extractConcepts(text, options)` - Extract concept tags
- `classifyScript(text)` - Detect language (zh/en/ja/ko/mixed)
- `normalizeToken(raw)` - Normalize and filter tokens

### memory-hub.js
- `MemoryHub` class for all memory operations
- `recordMood()`, `recordEnergy()`, `recordInsight()`, etc.
- `appendEvent()`, `getEvents()`
- `readMoods()`, `readEnergy()`, `readInsights()`

### cli.js
Unified CLI entry: `node cli.js <module> <workspace> <action> [args]`

## Implementation Notes

- **Node.js ESM**: All JS modules use ES modules (`import`/`export`)
- **File-based storage**: JSONL for logs, JSON for structured data
- **Versioned data**: All data files include `version` field
- **No external dependencies**: Core modules use only Node.js built-ins
