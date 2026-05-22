# Hermes Dream OS — Architecture Design

> 版本: 1.0.0
> 日期: 2026-05-22
> 定位: 融合 OpenClaw Dreams + Hermes Life OS 的升华记忆系统

---

## 一、设计理念

### 1.1 核心隐喻：记忆的昼夜节律

```
        白天（活跃期）                    夜晚（休眠期）
    ┌─────────────────┐            ┌─────────────────┐
    │  Life OS 模式   │            │  Dreams 模式    │
    │                 │            │                 │
    │  • 连接线索      │     →      │  • 整理去重      │
    │  • 观察模式      │            │  • 评分晋升      │
    │  • 产生洞察      │    ←      │  • 提取主题      │
    │  • Show/Don't   │            │  • 遗忘过滤      │
    │    Remind       │            │  • 归档沉睡      │
    └─────────────────┘            └─────────────────┘
              ↑                              ↓
              └──────────── 记忆循环 ──────────┘
```

### 1.2 两个系统的基因遗传

| 基因 | 来自 | 说明 |
|------|------|------|
| 三阶段睡眠模型 | OpenClaw | Light → Deep → REM 的精妙设计 |
| 六大评分信号 | OpenClaw | frequency/relevance/diversity/recency/consolidation/conceptual |
| 概念标签提取 | OpenClaw | 多语言停用词 + 保护词表 + 脚本分类 |
| 情感记忆schema | Hermes | MOOD/ENERGY/HABIT/GOAL/INSIGHT/WIN/STRUGGLE |
| 每日节律 | Hermes | 07:00 briefing / 12:00 check-in / 18:00 reflection / 23:00 consolidation |
| 模式检测规则 | Hermes | Mood dip / Energy pattern / Habit streak / Goal stall / Win pattern |
| Show, don't remind | Hermes | 不列清单，而是展示画面 |
| Earn trust slowly | Hermes | 从观察到建议的递进信任模型 |

---

## 二、架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                    Hermes Dream OS                          │
│                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────┐ │
│  │   Day Mode    │◄──►│  Memory Hub   │◄──►│   Night Mode  │ │
│  │   (Life OS)   │    │               │    │   (Dreams)    │ │
│  └───────────────┘    └───────────────┘    └───────────────┘ │
│         │                   │                    │           │
│    07:00-23:00         记忆中枢            23:00-07:00      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 记忆中枢（Memory Hub）

```
Memory Hub
    │
    ├── memory/
    │   ├── .dreams/           # 梦境系统数据
    │   │   ├── short-term-recall.json
    │   │   ├── phase-signals.json
    │   │   ├── events.jsonl
    │   │   └── session-corpus/
    │   │
    │   ├── YYYY-MM-DD.md      # 每日记忆（原有）
    │   ├── MEMORY.md           # 长期记忆（原有）
    │   ├── DREAMS.md           # 梦境日记（原有）
    │   │
    │   ├── life-log/           # 新增：Life OS 记忆
    │   │   ├── mood.jsonl      # 情感记录
    │   │   ├── energy.jsonl     # 精力记录
    │   │   ├── habits.json     # 习惯追踪
    │   │   ├── goals.json      # 目标追踪
    │   │   ├── insights.jsonl  # 洞察记录
    │   │   ├── wins.jsonl      # 成就记录
    │   │   └── struggles.jsonl # 困境记录
    │   │
    │   └── patterns/          # 新增：模式发现
    │       ├── weekly-review.md
    │       └── monthly-report.md
    │
    └── HERMES.md              # 主记忆入口（整合所有模块）
```

---

## 三、Day Mode（Life OS 模式）

### 3.1 活跃期节律

| 时间 | Cron | 动作 | 描述 |
|------|------|------|------|
| 07:00 | `0 7 * * *` | Morning Briefing | 能量预测 + 优先级 + 一个洞察 |
| 12:00 | `0 12 * * *` | Midday Check-in | 精力水平 + 上午进展 |
| 18:00 | `0 18 * * *` | Evening Reflection | 完成事项 + 未完成 + 模式观察 |
| 23:00 | `0 23 * * *` | Memory Consolidation | 存储今日模式 + 更新习惯连续 |

### 3.2 记忆记录 Schema

```typescript
// mood.jsonl
{ "date": "2026-05-22", "time": "08:30", "score": 7, "note": "上午效率高", "triggers": ["sleep"] }

// energy.jsonl
{ "date": "2026-05-22", "time": "14:00", "level": "high", "context": "第三杯咖啡", "productivity": 8 }

// habits.json (追加写入)
{ "name": "冥想", "date": "2026-05-22", "completed": true, "streak": 7, "note": "10分钟" }

// goals.json (更新)
{
  "name": "完成项目X",
  "progress": 0.65,
  "deadline": "2026-06-01",
  "last_updated": "2026-05-22",
  "milestones": [
    { "title": "需求分析", "done": true, "date": "2026-05-15" },
    { "title": "核心开发", "done": false, "date": null }
  ]
}

// insights.jsonl
{ "date": "2026-05-22", "observation": "周一上午效率总是最低", "confidence": 0.75, "pattern_based": true }

// wins.jsonl
{ "date": "2026-05-22", "description": "完成了拖延两周的任务", "category": "productivity" }

// struggles.jsonl
{ "date": "2026-05-22", "description": "总是被会议打断", "resolved": false }
```

### 3.3 模式检测规则（沿用 Hermes 并增强）

```python
RULES = {
    "mood_dip": {
        "condition": "3+ consecutive days below 6/10",
        "action": "flag_for_attention",
        "threshold": 3
    },
    "energy_pattern": {
        "condition": "same day of week consistently low/high",
        "action": "note_in_briefing",
        "min_samples": 4
    },
    "habit_streak_7": {
        "condition": "7 days completed",
        "action": "celebrate"
    },
    "habit_streak_broken": {
        "condition": "streak broken",
        "action": "acknowledge_without_shame"
    },
    "goal_stall": {
        "condition": "no progress in 7 days",
        "action": "gentle_nudge"
    },
    "win_pattern": {
        "condition": "same type of win 3+ times",
        "action": "reinforce_as_strength"
    },
    # 新增：从记忆召回中检测
    "memory_recency": {
        "condition": "memory not accessed in 14 days",
        "action": "include_in_dream_diary"
    },
    "memory_frequency_spike": {
        "condition": "same memory recalled 3+ times in 2 days",
        "action": "boost_promotion_score"
    }
}
```

---

## 四、Night Mode（Dreams 模式）

### 4.1 休眠期节律

| 时间 | Cron | 阶段 | 动作 |
|------|------|------|------|
| 23:30 | `30 23 * * *` | Light | 整理短期记忆，去重，准备候选 |
| 01:00 | `0 1 * * *` | Deep | 评分、晋升到 MEMORY.md |
| 03:00 | `0 3 * * *` | REM | 主题提取，Dream Diary，洞察生成 |
| 05:00 | `0 5 * * 0` | Weekly | 模式总结，周回顾 |

### 4.2 三阶段详细设计（基于 OpenClaw 升华）

#### Phase 1: Light（浅睡）

```python
def light_phase():
    """
    整理近期的记忆信号，去重并暂存候选内容。
    与 OpenClaw 的区别：
    - 额外整合当天的 life-log 数据（mood/energy/insights）
    - 将 life-log 中高置信度洞察（confidence > 0.8）直接标记为候选
    """
    candidates = []
    
    # 1. 收集当日生活记录中的洞察
    for insight in today_insights():
        if insight.confidence >= 0.8:
            candidates.append(InsightCandidate(
                content=insight.observation,
                source="life-log",
                type="insight",
                priority="high"
            ))
    
    # 2. 收集短期记忆召回
    for recall in today_recalls():
        if recall.relevance > 0.7:
            candidates.append(RecallCandidate(
                content=recall.snippet,
                source="memory",
                type="recall",
                priority="medium"
            ))
    
    # 3. 去重（相似度 > 0.9 合并）
    candidates = deduplicate(candidates, threshold=0.9)
    
    # 4. 记录 Light 阶段命中
    record_light_hits(candidates)
    
    return candidates
```

#### Phase 2: Deep（深睡）

```python
def deep_phase(candidates):
    """
    评分并将有价值的候选内容推入长期记忆。
    与 OpenClaw 的区别：
    - 引入"洞察价值"维度（来自 life-log 的洞察优先晋升）
    - 引入"主人关注度"维度（基于 goals 关联度）
    - 新增"情感权重"（mood 低迷日的记忆价值适度放大）
    """
    scored = []
    
    for candidate in candidates:
        score = calculate_score(candidate)
        
        # 增强因子
        if candidate.type == "insight" and candidate.priority == "high":
            score *= 1.3  # 高置信度洞察优先
        
        if candidate.related_goal_active:
            score *= 1.2  # 与活跃目标相关
        
        if candidate.emotional_context == "low_mood_day":
            score *= 1.1  # 情感低谷日的记忆更有价值
        
        if score >= MIN_SCORE_THRESHOLD:
            scored.append((score, candidate))
    
    # 按分数排序，晋升 top-N
    scored.sort(key=lambda x: x[0], reverse=True)
    
    for score, candidate in scored[:MAX_PROMOTIONS]:
        promote_to_memory(candidate)
    
    return scored[:MAX_PROMOTIONS]
```

**升华后的评分信号（7个维度）：**

| 信号 | 权重 | 来源 | 说明 |
|------|------|------|------|
| frequency | 0.20 | recallCount | 召回频率（原 OpenClaw） |
| relevance | 0.25 | avgScore | 检索质量（原 OpenClaw） |
| diversity | 0.12 | queryDays | 查询多样性（原 OpenClaw） |
| recency | 0.13 | ageDays | 时近性（原 OpenClaw） |
| consolidation | 0.08 | recallDays | 巩固度（原 OpenClaw） |
| insight_value | 0.15 | life-log | 洞察价值（新增） |
| emotional_weight | 0.07 | mood | 情感权重（新增） |

#### Phase 3: REM（快速眼动）

```python
def rem_phase():
    """
    提取主题和重复模式，生成 Dream Diary。
    与 OpenClaw 的区别：
    - 整合 life-log 中的模式（不只是 memory）
    - 生成"下周预测"和"建议行动"
    - Dream Diary 格式更贴近 Hermes 的 show, don't remind
    """
    patterns = detect_patterns(lookback_days=7)
    
    # 模式发现
    mood_trend = detect_mood_trend(patterns)
    energy_pattern = detect_energy_pattern(patterns)
    habit_progress = detect_habit_progress(patterns)
    
    # 生成梦境日记
    dream_diary = generate_dream_diary(patterns)
    
    # 生成下周预测
    predictions = generate_predictions(patterns)
    
    # 生成建议行动
    actions = generate_suggestions(patterns)
    
    return DreamDiary(
        patterns=patterns,
        dream_narrative=dream_diary,
        predictions=predictions,
        suggested_actions=actions
    )
```

**Dream Diary 格式（Hermes 风格）：**

```markdown
# Dream Diary — 2026-05-22

## 夜间的记忆整理

在过去的夜晚，你的记忆系统完成了以下工作：

**3 条记忆被晋升到长期记忆**
- [score=0.82] 项目X需求分析完成...
- [score=0.78] 微信爬虫框架搭建...
- [score=0.75] 习惯追踪系统设计...

**发现的模式**
- 🔄 每周一上午效率较低（已持续 3 周）
- 📈 冥想习惯连续 7 天完成
- 🎯 "完成项目X"目标进展 65%

## 下周预测

基于你的模式，周二将是你最高效的一天。
建议把最重要的任务安排在周二上午。

## 一个洞察

> 你在心情低落的日子（score < 6）往往会反思生活方向。
> 这种反思带来的洞察价值是平时的 1.3 倍。
> 考虑在心情不好的时候记录笔记。
```

---

## 五、HERMES.md — 统一记忆入口

```markdown
# Hermes Memory — {date}

> "Memory first — Never ask what you already know."

## 主人档案

**基本信息**
- 时区: Asia/Shanghai
- 活跃时间: 07:00 - 23:00
- 记忆模式: Dream OS (双模)

**当前目标**
- [进行中] 完成项目X (65%, deadline: 2026-06-01)
- [进行中] 建立冥想习惯 (streak: 7天)

## 今日快照 ({date})

### 情感
06:30起床 | 情绪 7/10 | 上午效率高

### 洞察
- "周一上午效率总是最低" (confidence: 75%)
- "心情不好时的反思更有价值" (confidence: 82%)

### 待处理
- [ ] 项目X 核心模块开发
- [ ] 团队周会准备

## 活跃模式

| 模式 | 状态 | 说明 |
|------|------|------|
| 周一低效 | 已确认 | 连续 3 周周一上午效率低 |
| 冥想连续 | 7天 | 建议继续坚持 |
| 午后低谷 | 已确认 | 14:00-15:00 精力下降 |

## 长期记忆摘要

<details>
<summary>点击展开</summary>

### 已晋升记忆
- 2026-05-15: 项目X需求分析完成
- 2026-05-10: 微信爬虫框架搭建
- 2026-05-05: 习惯追踪系统设计方案

### 核心洞察
- 心情低落时的反思更有价值（2026-05-18）
- 冥想 + 早起是最佳组合（2026-05-12）

</details>
```

---

## 六、技术实现

### 6.1 文件结构

```
D:\hermes\profiles\work\
├── skills\
│   └── hermes-dream-os\
│       ├── SKILL.md
│       ├── ARCHITECTURE.md
│       ├── SCRIPTS/
│       │   ├── memory-hub.py          # 记忆中枢
│       │   ├── day-mode.py            # Day Mode 实现
│       │   ├── night-mode.py          # Night Mode 实现
│       │   ├── scoring.py             # 评分算法
│       │   ├── pattern-detection.py   # 模式检测
│       │   ├── dream-diary.py         # Dream Diary 生成
│       │   └── concept-tagging.py     # 概念标签
│       ├── SCHEMAS/
│       │   └── memory-schema.json      # 数据模型定义
│       └── TEMPLATES\
│           ├── briefing-template.md    # 晨间简报模板
│           ├── evening-template.md     # 晚间反思模板
│           └── dream-diary-template.md # 梦境日记模板
```

### 6.2 依赖

```yaml
# hermes-dream-os/requirements.txt
pymupdf>=1.23.0        # PDF 处理（如需要）
python-dateutil>=2.8.0 # 日期处理
```

### 6.3 Cron Job 配置

```yaml
# D:\hermes\profiles\work\config\dream-os-crons.yaml
cron_jobs:
  - name: "Morning Briefing"
    schedule: "0 7 * * *"
    script: "day-mode.py"
    args: ["briefing"]
    
  - name: "Memory Consolidation"
    schedule: "0 23 * * *"
    script: "day-mode.py"
    args: ["consolidate"]
    
  - name: "Night Dreams - Light"
    schedule: "30 23 * * *"
    script: "night-mode.py"
    args: ["light"]
    
  - name: "Night Dreams - Deep"
    schedule: "0 1 * * *"
    script: "night-mode.py"
    args: ["deep"]
    
  - name: "Night Dreams - REM"
    schedule: "0 3 * * *"
    script: "night-mode.py"
    args: ["rem"]
    
  - name: "Weekly Review"
    schedule: "0 9 * * 1"
    script: "day-mode.py"
    args: ["weekly-review"]
```

---

## 七、核心算法

### 7.1 评分算法（Python 实现）

```python
# scoring.py

DEFAULT_WEIGHTS = {
    "frequency": 0.20,
    "relevance": 0.25,
    "diversity": 0.12,
    "recency": 0.13,
    "consolidation": 0.08,
    "insight_value": 0.15,
    "emotional_weight": 0.07,
}

MIN_SCORE = 0.75
MIN_RECALL_COUNT = 3
MIN_UNIQUE_QUERIES = 2
RECENCY_HALF_LIFE_DAYS = 14

def calculate_score(entry, weights=DEFAULT_WEIGHTS):
    """
    计算记忆条目晋升分数
    """
    # frequency: log 缩放
    frequency = clamp(math.log1p(entry.signal_count) / math.log1p(10), 0, 1)
    
    # relevance: 平均相关度
    relevance = clamp(entry.total_score / max(1, entry.signal_count), 0, 1)
    
    # diversity: 查询多样性
    diversity = clamp(len(entry.unique_queries) / 5, 0, 1)
    
    # recency: 指数衰减
    recency = math.exp(-math.ln2 / RECENCY_HALF_LIFE_DAYS * entry.age_days)
    
    # consolidation: 跨天数跨度
    consolidation = calculate_consolidation(entry.recall_days)
    
    # insight_value: 洞察质量（来自 life-log）
    insight_value = entry.insight_confidence if entry.type == "insight" else 0.5
    
    # emotional_weight: 情感权重
    emotional_weight = 1.0 + (0.1 if entry.emotional_context == "low_mood_day" else 0)
    
    score = (
        weights["frequency"] * frequency +
        weights["relevance"] * relevance +
        weights["diversity"] * diversity +
        weights["recency"] * recency +
        weights["consolidation"] * consolidation +
        weights["insight_value"] * insight_value +
        weights["emotional_weight"] * emotional_weight
    )
    
    return clamp(score, 0, 1)
```

### 7.2 概念标签提取

```python
# concept-tagging.py

STOP_WORDS = {
    "shared": {"about", "after", "agent", "again", "also", "assistant", ...},
    "english": {"and", "are", "for", "into", "its", "our", "the", ...},
    "cjk": {"的", "是", "在", "了", "和", "与", ...}
}

PROTECTED_GLOSSARY = {
    "embedding", "embeddings", "failover", "gateway",
    "backup", "router", "backup", "故障转移", "网关", ...
}

COMPOUND_RE = re.compile(r'[\p{L}\p{N}]+(?:[._/-][\p{L}\p{N}]+)+', re.U)

def extract_concepts(text, max_tags=8):
    """
    提取概念标签
    1. 优先提取保护词（技术术语）
    2. 提取复合词
    3. 分词提取
    4. 过滤停用词
    """
    tags = []
    
    # 保护词匹配
    for term in PROTECTED_GLOSSARY:
        if term.lower() in text.lower():
            tags.append(term)
    
    # 复合词
    for match in COMPOUND_RE.finditer(text):
        token = match.group().lower()
        if token not in STOP_WORDS["shared"] and len(token) >= 3:
            tags.append(token)
    
    # 分词（中文/日文/韩文用 jieba，英文用简单分词）
    tokens = tokenize(text)
    for token in tokens:
        if token.lower() not in STOP_WORDS["shared"] and len(token) >= 2:
            tags.append(token.lower())
    
    # 去重并截断
    return list(dict.fromkeys(tags))[:max_tags]
```

---

## 八、差异化优势

| 特性 | OpenClaw Dreams | Hermes Life OS | Hermes Dream OS |
|------|-----------------|----------------|-----------------|
| 记忆类型 | 通用记忆 | 生活记忆（情感/习惯） | 全域记忆 |
| 白天处理 | 无 | 有限（仅记录） | 主动连接 + 模式发现 |
| 夜晚处理 | 评分晋升 | 无 | 升华：洞察生成 + 预测 |
| 主人交互 | 被动查询 | 主动推送 | 双向增强 |
| 遗忘机制 | 依赖评分 | 无 | 情感加权保留 |
| 成长追踪 | 无 | 基础 | 完整闭环 |
| Show/Don't Remind | 无 | 有 | 有（增强版） |

---

## 九、路线图

### Phase 1: 基础实现（当前）
- [x] 架构设计
- [ ] 核心模块实现
- [ ] Cron job 配置
- [ ] SKILL.md 编写

### Phase 2: 增强功能
- [ ] 情感分析集成
- [ ] 预测模型
- [ ] 多语言支持

### Phase 3: 智能增强
- [ ] LLM 驱动的洞察生成
- [ ] 自适应权重调整
- [ ] 主人偏好学习

---

*Architecture Design v1.0 — Hermes Dream OS*
