"""
Hermes Dream OS — Memory Hub
记忆中枢：管理所有记忆存储和读写操作
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import hashlib


class MemoryHub:
    """记忆中枢 - 所有记忆读写的中心入口"""

    def __init__(self, workspace_dir: str):
        self.workspace = Path(workspace_dir)
        self.memory_dir = self.workspace / "memory"
        self.dreams_dir = self.memory_dir / ".dreams"
        self.life_log_dir = self.memory_dir / "life-log"
        self.patterns_dir = self.memory_dir / "patterns"

        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保目录结构存在"""
        for d in [self.memory_dir, self.dreams_dir, self.life_log_dir, self.patterns_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # session-corpus 子目录
        (self.dreams_dir / "session-corpus").mkdir(exist_ok=True)

    # ========== 路径常量 ==========

    @property
    def short_term_recall_path(self) -> Path:
        return self.dreams_dir / "short-term-recall.json"

    @property
    def phase_signals_path(self) -> Path:
        return self.dreams_dir / "phase-signals.json"

    @property
    def events_path(self) -> Path:
        return self.dreams_dir / "events.jsonl"

    @property
    def mood_path(self) -> Path:
        return self.life_log_dir / "mood.jsonl"

    @property
    def energy_path(self) -> Path:
        return self.life_log_dir / "energy.jsonl"

    @property
    def habits_path(self) -> Path:
        return self.life_log_dir / "habits.json"

    @property
    def goals_path(self) -> Path:
        return self.life_log_dir / "goals.json"

    @property
    def insights_path(self) -> Path:
        return self.life_log_dir / "insights.jsonl"

    @property
    def wins_path(self) -> Path:
        return self.life_log_dir / "wins.jsonl"

    @property
    def struggles_path(self) -> Path:
        return self.life_log_dir / "struggles.jsonl"

    @property
    def memory_md_path(self) -> Path:
        return self.memory_dir / "MEMORY.md"

    @property
    def dreams_md_path(self) -> Path:
        return self.memory_dir / "DREAMS.md"

    # ========== 通用读写 ==========

    def read_json(self, path: Path, default=None):
        """读取 JSON 文件"""
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
        return default

    def write_json(self, path: Path, data):
        """写入 JSON 文件（原子操作）"""
        tmp = f"{path}.{os.getpid()}.{datetime.now().timestamp()}.tmp"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if Path(tmp).exists():
            Path(tmp).unlink()

    def append_jsonl(self, path: Path, record: dict):
        """追加 JSONL 记录"""
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def read_jsonl(self, path: Path, limit: Optional[int] = None):
        """读取 JSONL 文件"""
        records = []
        if not path.exists():
            return records
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
        return records

    # ========== Short-term Recall ==========

    def read_short_term_recall(self):
        """读取短期记忆"""
        return self.read_json(self.short_term_recall_path, {"version": 1, "updatedAt": "", "entries": {}})

    def write_short_term_recall(self, store: dict):
        """写入短期记忆"""
        self.write_json(self.short_term_recall_path, store)

    # ========== Phase Signals ==========

    def read_phase_signals(self):
        """读取阶段信号"""
        return self.read_json(self.phase_signals_path, {"version": 1, "updatedAt": "", "entries": {}})

    def write_phase_signals(self, store: dict):
        """写入阶段信号"""
        self.write_json(self.phase_signals_path, store)

    # ========== Life Log ==========

    def record_mood(self, score: int, note: str = "", triggers: list = None, time: str = None):
        """记录情感"""
        now = datetime.now()
        record = {
            "date": now.strftime("%Y-%m-%d"),
            "time": time or now.strftime("%H:%M"),
            "score": max(1, min(10, score)),
            "note": note,
            "triggers": triggers or []
        }
        self.append_jsonl(self.mood_path, record)
        return record

    def get_recent_moods(self, days: int = 7) -> list:
        """获取最近 N 天的情感记录"""
        records = self.read_jsonl(self.mood_path)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [r for r in records if r.get("date", "") >= cutoff]

    def record_energy(self, level: str, context: str = "", productivity: int = None, time: str = None):
        """记录精力"""
        now = datetime.now()
        record = {
            "date": now.strftime("%Y-%m-%d"),
            "time": time or now.strftime("%H:%M"),
            "level": level if level in ("low", "medium", "high") else "medium",
            "context": context,
        }
        if productivity:
            record["productivity"] = max(1, min(10, productivity))
        self.append_jsonl(self.energy_path, record)
        return record

    def get_recent_energy(self, days: int = 7) -> list:
        """获取最近 N 天的精力记录"""
        records = self.read_jsonl(self.energy_path)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [r for r in records if r.get("date", "") >= cutoff]

    def record_insight(self, observation: str, confidence: float, source: str = "memory", pattern_based: bool = True):
        """记录洞察"""
        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "observation": observation,
            "confidence": max(0.0, min(1.0, confidence)),
            "patternBased": pattern_based,
            "source": source
        }
        self.append_jsonl(self.insights_path, record)
        return record

    def get_recent_insights(self, days: int = 7, min_confidence: float = 0.0) -> list:
        """获取最近 N 天的高置信度洞察"""
        records = self.read_jsonl(self.insights_path)
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        return [r for r in records if r.get("date", "") >= cutoff and r.get("confidence", 0) >= min_confidence]

    def record_win(self, description: str, category: str = "general"):
        """记录成就"""
        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": description,
            "category": category
        }
        self.append_jsonl(self.wins_path, record)
        return record

    def record_struggle(self, description: str, resolved: bool = False):
        """记录困境"""
        record = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "description": description,
            "resolved": resolved
        }
        self.append_jsonl(self.struggles_path, record)
        return record

    # ========== Habits ==========

    def read_habits(self) -> dict:
        """读取习惯数据"""
        return self.read_json(self.habits_path, {})

    def update_habit(self, name: str, completed: bool, note: str = ""):
        """更新习惯"""
        habits = self.read_habits()
        today = datetime.now().strftime("%Y-%m-%d")

        if name not in habits:
            habits[name] = {"streak": 0, "last_done": None, "history": []}

        habit = habits[name]
        habit["history"].append({"date": today, "completed": completed, "note": note})

        # 保持最近 90 天历史
        habit["history"] = habit["history"][-90:]

        if completed:
            last_done = habit.get("last_done")
            if last_done:
                last_date = datetime.strptime(last_done, "%Y-%m-%d")
                if (datetime.now() - last_date).days == 1:
                    habit["streak"] += 1
                elif (datetime.now() - last_date).days > 1:
                    habit["streak"] = 1
            else:
                habit["streak"] = 1
            habit["last_done"] = today

        habits[name] = habit
        self.write_json(self.habits_path, habits)
        return habit

    # ========== Goals ==========

    def read_goals(self) -> dict:
        """读取目标数据"""
        return self.read_json(self.goals_path, {})

    def update_goal(self, name: str, progress: float = None, deadline: str = None, milestone: dict = None):
        """更新目标"""
        goals = self.read_goals()
        today = datetime.now().strftime("%Y-%m-%d")

        if name not in goals:
            goals[name] = {
                "progress": 0.0,
                "deadline": deadline or "",
                "lastUpdated": today,
                "milestones": []
            }

        goal = goals[name]
        if progress is not None:
            goal["progress"] = max(0.0, min(1.0, progress))
        if deadline:
            goal["deadline"] = deadline
        goal["lastUpdated"] = today

        if milestone:
            for m in goal["milestones"]:
                if m["title"] == milestone["title"]:
                    m.update(milestone)
                    break
            else:
                goal["milestones"].append(milestone)

        goals[name] = goal
        self.write_json(self.goals_path, goals)
        return goal

    # ========== Events ==========

    def append_event(self, event_type: str, **kwargs):
        """追加事件"""
        record = {
            "type": event_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.append_jsonl(self.events_path, record)
        return record

    # ========== Utilities ==========

    @staticmethod
    def hash_query(query: str) -> str:
        """生成查询哈希"""
        return hashlib.sha1(query.lower().strip().encode()).hexdigest()[:12]

    @staticmethod
    def hash_snippet(snippet: str) -> str:
        """生成片段哈希"""
        normalized = " ".join(snippet.strip().split())
        return hashlib.sha1(normalized.encode()).hexdigest()[:12]

    def today(self) -> str:
        """返回今天的日期字符串"""
        return datetime.now().strftime("%Y-%m-%d")

    def format_iso_day(self, dt: datetime = None) -> str:
        """格式化 ISO 日期"""
        d = dt or datetime.now()
        return f"{d.year}-{d.month:02d}-{d.day:02d}"
