import re
import datetime as dt
from pathlib import Path


def now_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_time() -> str:
    return dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def sanitize_filename(name: str) -> str:
    name = name or "untitled"
    return re.sub(r'[\\/:*?"<>|]+', "_", name).strip()[:160] or "untitled"


def chinese_word_count(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text or ""))


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text or "", encoding="utf-8")
    return path


CN_NUM = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}
CN_UNIT = {"十": 10, "百": 100, "千": 1000}


def chinese_num_to_int(s: str):
    """Convert common Chinese numerals such as 一百五十一 / 百五 / 十一 to int."""
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    if re.fullmatch(r"\d+", s):
        return int(s)
    total = 0
    section = 0
    number = 0
    found = False
    for ch in s:
        if ch in CN_NUM:
            number = CN_NUM[ch]
            found = True
        elif ch in CN_UNIT:
            unit = CN_UNIT[ch]
            if number == 0:
                number = 1
            section += number * unit
            number = 0
            found = True
        else:
            return None
    total = section + number
    return total if found else None


CHAPTER_RE = re.compile(
    r"(?m)^\s*第\s*([0-9０-９]+|[零〇一二两三四五六七八九十百千]+)\s*(章|节|小节)\s*[:：、.．\-—]?\s*(.*)\s*$"
)


def normalize_digits(s: str) -> str:
    return (s or "").translate(str.maketrans("０１２３４５６７８９", "0123456789"))


def normalize_chapter_number(s: str):
    s = normalize_digits(s).strip()
    if re.fullmatch(r"\d+", s):
        return int(s)
    return chinese_num_to_int(s)


def split_chapters(text: str):
    """Return list of {number, marker, unit, title, content}. Supports 第1章 / 第一章 / 第1节 / 第一小节."""
    text = text or ""
    matches = list(CHAPTER_RE.finditer(text))
    chapters = []
    if not matches:
        return chapters
    for i, m in enumerate(matches):
        raw_num, unit, title = m.group(1), m.group(2), (m.group(3) or "").strip()
        num = normalize_chapter_number(raw_num)
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        chapters.append({
            "number": num,
            "raw_number": raw_num,
            "unit": unit,
            "title": title,
            "marker": m.group(0).strip(),
            "content": block,
            "word_count": chinese_word_count(block),
        })
    return chapters


def extract_text_from_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
