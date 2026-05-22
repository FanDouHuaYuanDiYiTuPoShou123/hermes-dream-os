# Hermes Dream OS

> 适配 Hermes Agent 的个人记忆操作系统 | Personal Memory OS for Hermes Agent

根据昼夜节律运作的记忆系统，白天收集，夜间整合。

## 核心特性

- **双模架构**: 白天活跃期 (Day Mode) + 夜间休眠期 (Night Mode)
- **7维度评分**: 频率、相关性、多样性、时近性、巩固度、洞察价值、情感权重
- **三阶段睡眠**: Light (整理) → Deep (评分晋升) → REM (梦境日记)
- **多语言支持**: 中文、英文、日文、韩文等概念标签提取

## 架构

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

## 快速开始

### 安装依赖

```bash
npm install
```

### CLI 用法

```bash
# Day Mode
node src/cli.js day-mode <workspace> briefing
node src/cli.js day-mode <workspace> checkin high 8 "工作顺利"
node src/cli.js day-mode <workspace> reflection
node src/cli.js day-mode <workspace> win "完成项目X"

# Memory Hub
node src/cli.js memory-hub <workspace> record-mood 8 "心情很好"
node src/cli.js memory-hub <workspace> record-energy high "咖啡" 9
node src/cli.js memory-hub <workspace> read-moods 7

# Night Mode
node src/cli.js night-mode <workspace> light
node src/cli.js night-mode <workspace> deep
node src/cli.js night-mode <workspace> rem
```

### Python Wrapper

```bash
python py_dream.py briefing
python py_dream.py checkin high 8
python py_dream.py night deep
```

## 项目结构

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

## Cron Schedule

| Time | Action |
|------|--------|
| 07:00 | Morning Briefing |
| 12:00 | Midday Check-in |
| 18:00 | Evening Reflection |
| 23:00 | Memory Consolidation |
| 23:30 | Night Light Phase |
| 01:00 | Night Deep Phase |
| 03:00 | Night REM Phase |
| Mon 08:00 | Weekly Review |

## 内存数据

- `memory/.dreams/short-term-recall.json` - 短期记忆
- `memory/.dreams/phase-signals.json` - 阶段信号
- `memory/life-log/mood.jsonl` - 情感记录
- `memory/life-log/energy.jsonl` - 精力记录
- `memory/life-log/habits.json` - 习惯连续
- `memory/life-log/goals.json` - 目标进度
- `memory/MEMORY.md` - 长期记忆
- `memory/DREAMS.md` - 梦境日记

## License

MIT
