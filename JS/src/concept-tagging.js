/**
 * Hermes Dream OS - Concept Tagging Module (JavaScript)
 * 多语言概念标签提取
 */

// ========== 停用词表 ==========

const STOP_WORDS = {
  shared: new Set([
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
  ]),
  english: new Set([
    "and", "are", "for", "its", "our", "the", "then", "were", "you", "your",
    "but", "not", "all", "can", "had", "her", "was", "one", "our", "out",
  ]),
  cjk: new Set([
    // 中文
    "的", "是", "在", "了", "和", "与", "及", "为", "将", "把", "用", "或",
    "及", "和", "在", "于", "上", "下", "中", "内", "外", "以", "所",
    // 日文
    "が", "から", "する", "して", "した", "で", "と", "に", "の", "は",
    "へ", "まで", "も", "や", "を",
    // 韩文
    "과", "는", "도", "로", "를", "에", "에서", "와", "은", "으로",
    "이", "하다", "한", "할", "해", "했다",
  ]),
  spanish: new Set([
    "al", "con", "como", "de", "del", "el", "en", "es", "la", "las", "los",
    "para", "por", "que", "se", "sin", "su", "sus", "una", "uno", "unos", "unas", "y"
  ]),
  french: new Set([
    "au", "aux", "avec", "dans", "de", "des", "du", "en", "est", "et", "la",
    "le", "les", "ou", "pour", "que", "qui", "sans", "ses", "son", "sur", "une", "un"
  ]),
  german: new Set([
    "auf", "aus", "bei", "das", "dem", "den", "der", "des", "die", "ein",
    "eine", "einem", "einen", "einer", "für", "im", "in", "mit", "nach",
    "oder", "ohne", "über", "und", "von", "zu", "zum", "zur"
  ]),
};

// 展平所有停用词
const ALL_STOP_WORDS = new Set();
for (const words of Object.values(STOP_WORDS)) {
  for (const w of words) {
    ALL_STOP_WORDS.add(w.toLowerCase());
  }
}

// ========== 保护词表（技术术语） ==========

const PROTECTED_GLOSSARY = new Set([
  // 英文技术术语
  "backup", "backups", "embedding", "embeddings", "failover", "gateway",
  "glacier", "gpt", "kv", "network", "openai", "qmd", "router", "s3",
  "vlan", "json", "yaml", "toml", "markdown", "api", "cli", "ui",
  // 中文
  "备份", "故障转移", "网络", "网关", "路由器",
  // 日文
  "バックアップ", "フェイルオーバー", "ルーター", "ネットワーク", "ゲートウェイ",
  // 德文
  "sicherung", "überwachung", "konfiguration",
  // 西班牙文
  "respaldo", "enrutador", "puerta-de-enlace",
]);

// ========== 正则表达式 ==========

// CJK Unicode 范围
const CJK_RANGE = '\\u4e00-\\u9fff';
const HIRAGANA_RANGE = '\\u3040-\\u309f';
const KATAKANA_RANGE = '\\u30a0-\\u30ff';
const HANGUL_RANGE = '\\uac00-\\ud7af';
const LATIN_RANGE = 'a-zA-Z';

const LETTER_NUMBER_RANGE = `${LATIN_RANGE}0-9${CJK_RANGE}${HIRAGANA_RANGE}${KATAKANA_RANGE}${HANGUL_RANGE}`;

// 复合词正则
const COMPOUND_RE = new RegExp(`[${LETTER_NUMBER_RANGE}]+(?:[._/-][${LETTER_NUMBER_RANGE}]+)+`, 'g');

// 字母或数字
const LETTER_OR_NUMBER_RE = new RegExp(`[${LETTER_NUMBER_RANGE}]`, 'g');

// 脚本检测正则
const LATIN_RE = new RegExp(`[${LATIN_RANGE}]`);
const HAN_RE = new RegExp(`[${CJK_RANGE}]`);
const HIRAGANA_RE = new RegExp(`[${HIRAGANA_RANGE}]`);
const KATAKANA_RE = new RegExp(`[${KATAKANA_RANGE}]`);
const HANGUL_RE = new RegExp(`[${HANGUL_RANGE}]`);

// ========== 脚本分类 ==========

/**
 * 判断标签属于哪个文字系统
 * @param {string} tag
 * @returns {'latin'|'cjk'|'mixed'|'other'}
 */
export function classifyScript(tag) {
  const normalized = tag || '';
  const hasLatin = LATIN_RE.test(normalized);
  const hasCJK = HAN_RE.test(normalized) || HIRAGANA_RE.test(normalized) ||
                 KATAKANA_RE.test(normalized) || HANGUL_RE.test(normalized);

  if (hasLatin && hasCJK) return 'mixed';
  if (hasCJK) return 'cjk';
  if (hasLatin) return 'latin';
  return 'other';
}

/**
 * 不同脚本的最小标记长度
 */
function minimumTokenLength(script) {
  if (script === 'cjk') return 2;
  return 3;
}

/**
 * 判断是否仅含假名（不含汉字和韩文）
 */
function isKanaOnly(value) {
  return !HAN_RE.test(value) && !HANGUL_RE.test(value) &&
    (HIRAGANA_RE.test(value) || KATAKANA_RE.test(value));
}

/**
 * 归一化单个 token
 * @param {string} rawToken
 * @returns {string|null} 返回 null 表示应该过滤掉
 */
export function normalizeToken(rawToken) {
  if (!rawToken) return null;

  // NFKC 正规化
  let normalized = rawToken.normalize('NFKC');

  // 去除首尾非字母数字（分开处理避免正则歧义）
  const patternHead = new RegExp(`^[^${LETTER_NUMBER_RANGE}]+`);
  const patternTail = new RegExp(`[^${LETTER_NUMBER_RANGE}]+$`);
  normalized = normalized.replace(patternHead, '');
  normalized = normalized.replace(patternTail, '');
  normalized = normalized.replace(/_/g, '-').toLowerCase();

  // 长度检查
  if (!normalized || normalized.length > 32) return null;

  // 纯数字过滤
  if (/^\d+$/.test(normalized)) return null;

  // 日期过滤（YYYY-MM-DD）
  if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) return null;

  // 带扩展名的日期过滤（YYYY-MM-DD.xxx）
  const dateExtPattern = new RegExp(`^\\d{4}-\\d{2}-\\d{2}\\.[${LETTER_NUMBER_RANGE}]+$`);
  if (dateExtPattern.test(normalized)) return null;

  // 停用词过滤
  if (ALL_STOP_WORDS.has(normalized)) return null;

  // 路径噪音词过滤
  const parts = normalized.split('.');
  for (const part of parts) {
    if (PATH_NOISE.has(part)) return null;
  }

  // 脚本特定长度检查
  const script = classifyScript(normalized);
  if (normalized.length < minimumTokenLength(script)) return null;

  // 只含假名的 token 至少需要 3 个字符
  if (isKanaOnly(normalized) && normalized.length < 3) return null;

  return normalized;
}

// 路径噪音词
const PATH_NOISE = new Set([
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
]);

/**
 * 提取复合词（用点/下划线/横线连接）
 * @param {string} text
 * @returns {string[]}
 */
export function extractCompoundTokens(text) {
  return (text.match(COMPOUND_RE) || []).map(m => m);
}

/**
 * 提取文本中的所有字母数字序列
 * @param {string} text
 * @returns {string[]}
 */
function segmentText(text) {
  const tokenPattern = new RegExp(`[${LETTER_NUMBER_RANGE}]+`, 'g');
  return (text.match(tokenPattern) || []).map(m => m);
}

/**
 * 从文本中收集保护词表中的术语
 * @param {string} text
 * @returns {string[]}
 */
function collectGlossaryMatches(text) {
  const textLower = text.toLowerCase();
  const matches = [];
  for (const term of PROTECTED_GLOSSARY) {
    if (textLower.includes(term.toLowerCase())) {
      matches.push(term.toLowerCase());
    }
  }
  return matches;
}

/**
 * 从文本中提取概念标签
 * @param {string} text
 * @param {number} maxTags
 * @returns {string[]}
 */
export function extractConcepts(text, maxTags = 8) {
  if (!text) return [];

  const tags = [];

  // 1. 保护词匹配
  tags.push(...collectGlossaryMatches(text));

  // 2. 复合词
  for (const compound of extractCompoundTokens(text)) {
    const normalized = normalizeToken(compound);
    if (normalized && !tags.includes(normalized)) {
      tags.push(normalized);
    }
  }

  // 3. 分词并过滤
  for (const token of segmentText(text)) {
    const normalized = normalizeToken(token);
    if (normalized && !tags.includes(normalized)) {
      tags.push(normalized);
    }

    if (tags.length >= maxTags) break;
  }

  return tags.slice(0, maxTags);
}

/**
 * 统计概念标签的脚本分布
 * @param {string[][]} conceptTagsList
 * @returns {Object}
 */
export function summarizeConceptScripts(conceptTagsList) {
  const coverage = {
    latinEntryCount: 0,
    cjkEntryCount: 0,
    mixedEntryCount: 0,
    otherEntryCount: 0
  };

  for (const conceptTags of conceptTagsList) {
    let hasLatin = false;
    let hasCJK = false;
    let hasOther = false;

    for (const tag of conceptTags) {
      const family = classifyScript(tag);
      if (family === 'mixed') {
        hasLatin = true;
        hasCJK = true;
      } else if (family === 'latin') {
        hasLatin = true;
      } else if (family === 'cjk') {
        hasCJK = true;
      } else {
        hasOther = true;
      }
    }

    if (hasLatin && hasCJK) {
      coverage.mixedEntryCount++;
    } else if (hasCJK) {
      coverage.cjkEntryCount++;
    } else if (hasLatin) {
      coverage.latinEntryCount++;
    } else if (hasOther) {
      coverage.otherEntryCount++;
    }
  }

  return coverage;
}
