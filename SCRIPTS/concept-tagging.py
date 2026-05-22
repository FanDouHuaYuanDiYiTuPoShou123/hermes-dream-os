"""
Hermes Dream OS — Concept Tagging Module
多语言概念标签提取
"""

import re
import unicodedata
from typing import Optional


# ========== 停用词表 ==========

STOP_WORDS = {
    "shared": {
        "about", "after", "agent", "again", "also", "assistant", "because",
        "before", "being", "between", "build", "called", "could", "daily",
        "default", "deploy", "during", "every", "file", "files", "from",
        "have", "into", "just", "line", "lines", "long", "main", "make",
        "memory", "month", "more", "most", "move", "much", "next", "note",
        "notes", "over", "part", "past", "port", "same", "score", "search",
        "session", "sessions", "short", "should", "since", "some", "subagent",
        "system", "than", "that", "their", "there", "these", "they", "this",
        "through", "today", "user", "using", "with", "work", "workspace", "year",
        "one", "two", "three", "four", "five", "first", "second", "third",
        "now", "then", "very", "only", "other", "such", "even", "also",
    },
    "english": {
        "and", "are", "for", "its", "our", "the", "then", "were", "you", "your",
        "but", "not", "all", "can", "had", "her", "was", "one", "our", "out",
    },
    "cjk": {
        # 中文
        "的", "是", "在", "了", "和", "与", "及", "为", "将", "把", "用", "或",
        "及", "和", "在", "于", "上", "下", "中", "内", "外", "以", "及", "所",
        # 日文
        "が", "から", "する", "して", "した", "で", "と", "に", "の", "は",
        "へ", "まで", "も", "や", "を",
        # 韩文
        "과", "는", "도", "로", "를", "에", "에서", "와", "은", "으로", "을",
        "이", "하다", "한", "할", "해", "했다",
    },
    "spanish": {
        "al", "con", "como", "de", "del", "el", "en", "es", "la", "las", "los",
        "para", "por", "que", "se", "sin", "su", "sus", "una", "uno", "unos", "unas", "y"
    },
    "french": {
        "au", "aux", "avec", "dans", "de", "des", "du", "en", "est", "et", "la",
        "le", "les", "ou", "pour", "que", "qui", "sans", "ses", "son", "sur", "une", "un"
    },
    "german": {
        "auf", "aus", "bei", "das", "dem", "den", "der", "des", "die", "ein",
        "eine", "einem", "einen", "einer", "für", "im", "in", "mit", "nach",
        "oder", "ohne", "über", "und", "von", "zu", "zum", "zur"
    }
}

# 展平所有停用词
ALL_STOP_WORDS = set()
for words in STOP_WORDS.values():
    ALL_STOP_WORDS.update(w.lower() for w in words)

# ========== 保护词表（技术术语） ==========

PROTECTED_GLOSSARY = {
    # 英文技术术语
    "backup", "backups", "embedding", "embeddings", "failover", "gateway",
    "glacier", "gpt", "kv", "network", "openai", "qmd", "router", "s3",
    "vlan", "json", "yaml", "toml", "markdown", "api", "cli", "ui",
    # 中文
    "备份", "故障转移", "网络", "网关", "路由器", "备份",
    # 日文
    "バックアップ", "フェイルオーバー", "ルーター", "ネットワーク", "ゲートウェイ",
    # 德文
    "sicherung", "überwachung", "konfiguration",
    # 西班牙文
    "respaldo", "enrutador", "puerta-de-enlace",
}

# ========== 正则表达式 ==========

# 尝试使用 regex 模块（支持 Unicode 属性），否则回退到 re
try:
    import regex

    # 复合词：字母数字混合，下划线/点/横线连接
    COMPOUND_RE = regex.compile(r'[\p{L}\p{N}]+(?:[._/-][\p{L}\p{N}]+)+', regex.UNICODE)
    LETTER_OR_NUMBER_RE = regex.compile(r'[\p{L}\p{N}]', regex.UNICODE)
    LATIN_RE = regex.compile(r'\p{Script=Latin}', regex.UNICODE)
    HAN_RE = regex.compile(r'\p{Script=Han}', regex.UNICODE)
    HIRAGANA_RE = regex.compile(r'\p{Script=Hiragana}', regex.UNICODE)
    KATAKANA_RE = regex.compile(r'\p{Script=Katakana}', regex.UNICODE)
    HANGUL_RE = regex.compile(r'\p{Script=Hangul}', regex.UNICODE)
    USE_REGEX = True
except ImportError:
    # 回退方案：使用基本 re 模块 + 手动 Unicode 范围
    import re

    # CJK Unicode 范围
    HAN_RANGE = '\u4e00-\u9fff'           # 中文
    HIRAGANA_RANGE = '\u3040-\u309f'      # 日文平假名
    KATAKANA_RANGE = '\u30a0-\u30ff'      # 日文片假名
    HANGUL_RANGE = '\uac00-\ud7af'        # 韩文
    LATIN_EXTENDED = '\u00c0-\u024f'      # 拉丁扩展

    # 组合字母范围（CJK + 拉丁 + 希腊 + 俄文等常用字母）
    LETTER_PATTERN = (
        'a-zA-Z'                           # 基本拉丁
        + LATIN_EXTENDED                   # 拉丁扩展
        + HAN_RANGE                        # 中文
        + HIRAGANA_RANGE                   # 日文平假名
        + KATAKANA_RANGE                   # 日文片假名
        + HANGUL_RANGE                     # 韩文
        + '\u0370-\u03ff'                 # 希腊文
        + '\u0400-\u04ff'                 # 西里尔文
    )
    NUMBER_PATTERN = '0-9\u0660-\u0669\u0966-\u096f'  # 阿拉伯数字 + 其他数字

    LETTER_OR_NUMBER_CHAR = f'[{LETTER_PATTERN}{NUMBER_PATTERN}]'
    COMPOUND_PATTERN = f'{LETTER_OR_NUMBER_CHAR}+(?:[._/-]{LETTER_OR_NUMBER_CHAR}+)+'

    COMPOUND_RE = re.compile(COMPOUND_PATTERN, re.UNICODE)
    LETTER_OR_NUMBER_RE = re.compile(LETTER_OR_NUMBER_CHAR, re.UNICODE)
    # LATIN_RE：基本拉丁字母 + 拉丁扩展
    LATIN_RANGE = 'a-zA-Z\u00c0-\u024f'
    LATIN_RE = re.compile(f'[{LATIN_RANGE}]', re.UNICODE)
    HAN_RE = re.compile(f'[{HAN_RANGE}]', re.UNICODE)
    HIRAGANA_RE = re.compile(f'[{HIRAGANA_RANGE}]', re.UNICODE)
    KATAKANA_RE = re.compile(f'[{KATAKANA_RANGE}]', re.UNICODE)
    HANGUL_RE = re.compile(f'[{HANGUL_RANGE}]', re.UNICODE)
    USE_REGEX = False

# 路径噪音扩展（文件扩展名）
PATH_NOISE = {
    "cjs", "cpp", "cts", "jsx", "json", "md", "mjs", "mts",
    "text", "toml", "ts", "tsx", "txt", "yaml", "yml",
    "py", "pyc", "pyd", "pyo", "gitignore", "env", "log",
    "html", "css", "js", "ts", "tsx", "jsx", "vue", "svelte",
    "java", "class", "jar", "xml", "properties",
    "sh", "bash", "zsh", "fish", "ps1", "bat", "cmd",
    "go", "rs", "rb", "php", "pl", "lua", "r",
    "sql", "db", "sqlite", "mdb",
    "zip", "tar", "gz", "rar", "7z", "bz2",
    "png", "jpg", "jpeg", "gif", "svg", "ico", "webp",
    "mp3", "mp4", "wav", "flac", "avi", "mov", "mkv",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "exe", "dll", "so", "dylib", "app", "ipa", "apk",
    "lock", "tmp", "temp", "cache", "node_modules", "dist", "build",
    "coverage", "nyc_output", "pytest_cache", "__pycache__",
}


def classify_script(tag: str) -> str:
    """判断标签属于哪个文字系统"""
    normalized = tag
    has_latin = LATIN_RE.search(normalized) is not None
    has_cjk = (HAN_RE.search(normalized) is not None or
               HIRAGANA_RE.search(normalized) is not None or
               KATAKANA_RE.search(normalized) is not None or
               HANGUL_RE.search(normalized) is not None)

    if has_latin and has_cjk:
        return "mixed"
    if has_cjk:
        return "cjk"
    if has_latin:
        return "latin"
    return "other"


def minimum_token_length(script: str) -> int:
    """不同脚本的最小标记长度"""
    if script == "cjk":
        return 2
    return 3


def normalize_token(raw_token: str) -> Optional[str]:
    """
    归一化单个 token
    返回 None 表示应该过滤掉
    """
    if not raw_token:
        return None

    # NFKC 正规化，去除首尾非字母数字
    normalized = unicodedata.normalize("NFKC", raw_token)
    # 分开处理首尾的非字母数字（合并模式有歧义）
    CJK_RANGE = 'a-zA-Z0-9\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
    pattern_head = r'^[^' + CJK_RANGE + r']+'
    pattern_tail = r'[^' + CJK_RANGE + r']+$'
    normalized = re.sub(pattern_head, '', normalized)
    normalized = re.sub(pattern_tail, '', normalized)
    normalized = normalized.replace("_", "-").lower()

    # 长度检查
    if not normalized or len(normalized) > 32:
        return None

    # 纯数字过滤
    if re.match(r'^\d+$', normalized):
        return None

    # 日期过滤（YYYY-MM-DD）
    if re.match(r'^\d{4}-\d{2}-\d{2}$', normalized):
        return None

    # 带扩展名的日期过滤（YYYY-MM-DD.xxx）
    # 使用手动范围替代 \p{L}\p{N}
    LETTER_NUMBER_RANGE = 'a-zA-Z0-9\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
    date_ext_pattern = r'^\d{4}-\d{2}-\d{2}\.[' + LETTER_NUMBER_RANGE + ']+$'
    if re.match(date_ext_pattern, normalized):
        return None

    # 停用词过滤
    if normalized in ALL_STOP_WORDS:
        return None

    # 路径噪音词过滤
    parts = normalized.split('.')
    for part in parts:
        if part in PATH_NOISE:
            return None

    # 脚本特定长度检查
    script = classify_script(normalized)
    if len(normalized) < minimum_token_length(script):
        return None

    # 只含假名的 token 至少需要 3 个字符
    if is_kana_only(normalized) and len(normalized) < 3:
        return None

    return normalized


def is_kana_only(value: str) -> bool:
    """判断是否仅含假名（不含汉字和韩文）"""
    return (not HAN_RE.search(value) and
            not HANGUL_RE.search(value) and
            (HIRAGANA_RE.search(value) or KATAKANA_RE.search(value)))


def extract_compound_tokens(text: str) -> list:
    """提取复合词（用点/下划线/横线连接）"""
    return [m.group() for m in COMPOUND_RE.finditer(text)]


def segment_text(text: str) -> list:
    """
    分词
    优先使用 regex 模块（如果可用），否则使用回退方案
    """
    try:
        if USE_REGEX:
            # 使用 regex 模块支持 Unicode 属性
            tokens = regex.findall(r'[\p{L}\p{N}]+', text, regex.UNICODE)
            return tokens
    except NameError:
        pass

    # 回退：使用 LETTER_OR_NUMBER_RE 的手动范围
    LETTER_NUMBER_RANGE = 'a-zA-Z0-9\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af'
    tokens = re.findall(f'[{LETTER_NUMBER_RANGE}]+', text, re.UNICODE)
    return tokens


def collect_glossary_matches(text: str) -> list:
    """从文本中收集保护词表中的术语"""
    text_lower = text.lower()
    matches = []
    for term in PROTECTED_GLOSSARY:
        if term.lower() in text_lower:
            matches.append(term.lower())
    return matches


def extract_concepts(text: str, max_tags: int = 8) -> list:
    """
    从文本中提取概念标签

    策略：
    1. 先收集保护词（技术术语）
    2. 提取复合词
    3. 分词并过滤停用词
    4. 去重，截取前 max_tags 个
    """
    tags = []

    # 1. 保护词匹配
    tags.extend(collect_glossary_matches(text))

    # 2. 复合词
    for compound in extract_compound_tokens(text):
        normalized = normalize_token(compound)
        if normalized and normalized not in tags:
            tags.append(normalized)

    # 3. 分词并过滤
    for token in segment_text(text):
        normalized = normalize_token(token)
        if normalized and normalized not in tags:
            tags.append(normalized)

        if len(tags) >= max_tags:
            break

    return tags[:max_tags]


def summarize_concept_scripts(concept_tags_list: list) -> dict:
    """
    统计概念标签的脚本分布
    用于审计
    """
    coverage = {
        "latinEntryCount": 0,
        "cjkEntryCount": 0,
        "mixedEntryCount": 0,
        "otherEntryCount": 0
    }

    for concept_tags in concept_tags_list:
        has_latin = False
        has_cjk = False
        has_other = False

        for tag in concept_tags:
            family = classify_script(tag)
            if family == "mixed":
                has_latin = True
                has_cjk = True
            elif family == "latin":
                has_latin = True
            elif family == "cjk":
                has_cjk = True
            else:
                has_other = True

        if has_latin and has_cjk:
            coverage["mixedEntryCount"] += 1
        elif has_cjk:
            coverage["cjkEntryCount"] += 1
        elif has_latin:
            coverage["latinEntryCount"] += 1
        elif has_other:
            coverage["otherEntryCount"] += 1

    return coverage
