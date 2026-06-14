import difflib
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.core.paths import DB_PATH, BACKUP_DIR, EXPORT_DIR
from app.core.utils import (
    now_str, safe_time, sanitize_filename, chinese_word_count, write_text,
    split_chapters, extract_text_from_docx
)
from app.db.database import connect


class BackupService:
    @staticmethod
    def create_backup(operation_type: str, description: str = "", ip_id=None, work_id=None, version_id=None, related_range: str = ""):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / sanitize_filename(f"backup_{operation_type}_{safe_time()}.db")
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, backup_path)
        conn = connect()
        conn.execute(
            """INSERT INTO version_logs
               (ip_id, work_id, version_id, operation_type, description, related_range, backup_path, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (ip_id, work_id, version_id, operation_type, description, related_range, str(backup_path), now_str())
        )
        conn.commit(); conn.close()
        return backup_path

    @staticmethod
    def list_logs(work_id=None):
        conn = connect()
        if work_id:
            rows = conn.execute("SELECT * FROM version_logs WHERE work_id=? ORDER BY id DESC", (work_id,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM version_logs ORDER BY id DESC").fetchall()
        conn.close()
        return rows


class IPService:
    @staticmethod
    def get_or_create(name: str, ip_type: str = "", description: str = ""):
        name = (name or "未命名IP").strip()
        conn = connect()
        row = conn.execute("SELECT * FROM ip_profiles WHERE name=?", (name,)).fetchone()
        if row:
            conn.close(); return row["id"]
        ts = now_str()
        cur = conn.execute(
            "INSERT INTO ip_profiles (name, ip_type, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name, ip_type, description, ts, ts)
        )
        conn.commit(); ip_id = cur.lastrowid; conn.close()
        BackupService.create_backup("create_ip", f"新建IP：{name}", ip_id=ip_id)
        return ip_id

    @staticmethod
    def list_all():
        conn = connect()
        rows = conn.execute(
            """SELECT ip.*, COUNT(w.id) AS work_count
               FROM ip_profiles ip
               LEFT JOIN works w ON w.ip_id=ip.id
               GROUP BY ip.id
               ORDER BY ip.updated_at DESC, ip.id DESC"""
        ).fetchall()
        conn.close(); return rows

    @staticmethod
    def get(ip_id):
        conn = connect(); row = conn.execute("SELECT * FROM ip_profiles WHERE id=?", (ip_id,)).fetchone(); conn.close(); return row


class WorkService:
    @staticmethod
    def create(ip_id: int, title: str, work_type: str = "long_novel", platform: str = "番茄小说", genre: str = "", status: str = "进行中", current_volume: str = "", current_chapter: int = 0):
        ts = now_str(); conn = connect()
        cur = conn.execute(
            """INSERT INTO works
               (ip_id, title, work_type, platform, genre, status, current_volume, current_chapter, next_action, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ip_id, title.strip(), work_type, platform, genre, status, current_volume, int(current_chapter or 0), "", ts, ts)
        )
        conn.commit(); work_id = cur.lastrowid; conn.close()
        BackupService.create_backup("create_work", f"新建作品：{title}", ip_id=ip_id, work_id=work_id)
        return work_id

    @staticmethod
    def get_or_create(ip_id: int, title: str, work_type: str = "long_novel", platform: str = "番茄小说", current_volume: str = ""):
        conn = connect()
        row = conn.execute("SELECT * FROM works WHERE ip_id=? AND title=?", (ip_id, title)).fetchone()
        if row:
            if current_volume and not row["current_volume"]:
                conn.execute("UPDATE works SET current_volume=?, updated_at=? WHERE id=?", (current_volume, now_str(), row["id"]))
                conn.commit()
            wid = row["id"]; conn.close(); return wid
        conn.close(); return WorkService.create(ip_id, title, work_type=work_type, platform=platform, current_volume=current_volume)

    @staticmethod
    def list_by_ip(ip_id: int):
        conn = connect(); rows = conn.execute("SELECT * FROM works WHERE ip_id=? ORDER BY updated_at DESC, id DESC", (ip_id,)).fetchall(); conn.close(); return rows

    @staticmethod
    def get(work_id: int):
        conn = connect(); row = conn.execute("SELECT * FROM works WHERE id=?", (work_id,)).fetchone(); conn.close(); return row

    @staticmethod
    def update_current(work_id: int, version_id: int, current_chapter: int, next_action: str = "", current_volume: str = None):
        conn = connect()
        if current_volume is not None:
            conn.execute("UPDATE works SET current_effective_version_id=?, current_chapter=?, current_volume=?, next_action=?, updated_at=? WHERE id=?", (version_id, int(current_chapter or 0), current_volume, next_action, now_str(), work_id))
        else:
            conn.execute("UPDATE works SET current_effective_version_id=?, current_chapter=?, next_action=?, updated_at=? WHERE id=?", (version_id, int(current_chapter or 0), next_action, now_str(), work_id))
        conn.commit(); conn.close()


class VersionService:
    @staticmethod
    def create_version(work_id: int, chapter_start: int, chapter_end: int, version_label: str, title: str, manuscript_type: str, status: str, content: str, replaces: str = "", summary: str = ""):
        ts = now_str(); conn = connect()
        cur = conn.execute(
            """INSERT INTO manuscript_versions
               (work_id, chapter_start, chapter_end, version_label, title, manuscript_type, status,
                is_current_effective, replaces, content, summary, word_count, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)""",
            (work_id, int(chapter_start), int(chapter_end), version_label, title, manuscript_type, status, replaces, content, summary, chinese_word_count(content), ts, ts)
        )
        conn.commit(); vid = cur.lastrowid; conn.close()
        BackupService.create_backup("create_version", f"保存稿件版本：{title}", work_id=work_id, version_id=vid, related_range=f"{chapter_start}-{chapter_end}")
        return vid

    @staticmethod
    def list_versions(work_id: int):
        conn = connect(); rows = conn.execute("SELECT * FROM manuscript_versions WHERE work_id=? ORDER BY chapter_start DESC, id DESC", (work_id,)).fetchall(); conn.close(); return rows

    @staticmethod
    def get(version_id: int):
        conn = connect(); row = conn.execute("SELECT * FROM manuscript_versions WHERE id=?", (version_id,)).fetchone(); conn.close(); return row

    @staticmethod
    def current(work_id: int):
        conn = connect(); row = conn.execute("SELECT * FROM manuscript_versions WHERE work_id=? AND is_current_effective=1 ORDER BY id DESC LIMIT 1", (work_id,)).fetchone(); conn.close(); return row

    @staticmethod
    def set_current(work_id: int, version_id: int):
        version = VersionService.get(version_id)
        if not version: raise ValueError("没有找到这个版本。")
        conn = connect()
        old_rows = conn.execute("SELECT * FROM manuscript_versions WHERE work_id=? AND is_current_effective=1", (work_id,)).fetchall()
        for old in old_rows:
            if old["id"] != version_id:
                conn.execute("UPDATE manuscript_versions SET is_current_effective=0, status='DEPRECATED', updated_at=? WHERE id=?", (now_str(), old["id"]))
                conn.execute("UPDATE writing_packages SET status='EXPIRED', expired_reason=?, updated_at=? WHERE work_id=? AND base_version_id=? AND status='ACTIVE'", ("当前有效版本已更新，旧写作包不再适用", now_str(), work_id, old["id"]))
        conn.execute("UPDATE manuscript_versions SET is_current_effective=1, status='CURRENT', updated_at=? WHERE id=?", (now_str(), version_id))
        conn.execute("UPDATE works SET current_effective_version_id=?, current_chapter=?, next_action=?, updated_at=? WHERE id=?", (version_id, int(version["chapter_end"] or 0), f"生成第{int(version['chapter_end'])+1}—{int(version['chapter_end'])+5}章写作包", now_str(), work_id))
        conn.commit(); conn.close()
        BackupService.create_backup("set_current_version", f"设置当前有效版本：{version['title']}", work_id=work_id, version_id=version_id, related_range=f"{version['chapter_start']}-{version['chapter_end']}")


class NoteService:
    @staticmethod
    def save_stage_note(work_id: int, version_id, chapter_start: int, chapter_end: int, title: str, content: str, risk_level: str = "NONE"):
        if not (content or "").strip(): return None
        ts = now_str(); conn = connect()
        cur = conn.execute(
            """INSERT INTO stage_notes
               (work_id, version_id, chapter_start, chapter_end, title, content, status, risk_level, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?, ?)""",
            (work_id, version_id, int(chapter_start), int(chapter_end), title, content, risk_level, ts, ts)
        )
        conn.commit(); nid = cur.lastrowid; conn.close(); return nid

    @staticmethod
    def latest_stage_note(work_id: int):
        conn = connect(); row = conn.execute("SELECT * FROM stage_notes WHERE work_id=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1", (work_id,)).fetchone(); conn.close(); return row

    @staticmethod
    def has_review_for(work_id: int, start: int, end: int):
        conn = connect()
        row = conn.execute("SELECT * FROM stage_notes WHERE work_id=? AND chapter_start<=? AND chapter_end>=? AND status='ACTIVE' ORDER BY id DESC LIMIT 1", (work_id, start, end)).fetchone()
        conn.close(); return row is not None


class GuardService:
    @staticmethod
    def add_outline_rule(work_id: int, rule_type: str, title: str, content: str, priority: str = "P1"):
        ts = now_str(); conn = connect()
        conn.execute("INSERT INTO outline_rules (work_id, rule_type, title, content, priority, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, ?)", (work_id, rule_type, title, content, priority, ts, ts))
        conn.commit(); conn.close()

    @staticmethod
    def list_outline_rules(work_id: int):
        conn = connect(); rows = conn.execute("SELECT * FROM outline_rules WHERE work_id=? AND status='ACTIVE' ORDER BY id DESC", (work_id,)).fetchall(); conn.close(); return rows

    @staticmethod
    def delete_outline_rule(rule_id: int):
        conn = connect(); conn.execute("UPDATE outline_rules SET status='DELETED', updated_at=? WHERE id=?", (now_str(), rule_id)); conn.commit(); conn.close()

    @staticmethod
    def add_character(work_id: int, name: str, role: str, current_state: str, must_keep: str, forbidden_drift: str, knowledge_state: str, last_update_chapter: int):
        ts = now_str(); conn = connect()
        conn.execute("""INSERT INTO character_states
            (work_id, name, role, current_state, must_keep, forbidden_drift, knowledge_state, last_update_chapter, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)""", (work_id, name, role, current_state, must_keep, forbidden_drift, knowledge_state, int(last_update_chapter or 0), ts, ts))
        conn.commit(); conn.close()

    @staticmethod
    def list_characters(work_id: int):
        conn = connect(); rows = conn.execute("SELECT * FROM character_states WHERE work_id=? AND status='ACTIVE' ORDER BY id DESC", (work_id,)).fetchall(); conn.close(); return rows

    @staticmethod
    def add_clue(work_id: int, name: str, first_chapter: int, last_progress_chapter: int, expected_resolve_chapter: int, related_people: str, status: str, notes: str):
        ts = now_str(); conn = connect()
        conn.execute("""INSERT INTO clue_items
            (work_id, name, first_chapter, last_progress_chapter, expected_resolve_chapter, related_people, current_status, notes, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (work_id, name, int(first_chapter or 0), int(last_progress_chapter or 0), int(expected_resolve_chapter or 0), related_people, status or "推进中", notes, ts, ts))
        conn.commit(); conn.close()

    @staticmethod
    def list_clues(work_id: int):
        conn = connect(); rows = conn.execute("SELECT * FROM clue_items WHERE work_id=? ORDER BY id DESC", (work_id,)).fetchall(); conn.close(); return rows


class RiskService:
    @staticmethod
    def risk_report(work_id: int):
        work = WorkService.get(work_id)
        current = VersionService.current(work_id)
        risks = []
        level = "GREEN"
        if not current:
            risks.append(("RED", "当前作品没有设置当前有效版本。"))
        else:
            ch = int(work["current_chapter"] or current["chapter_end"] or 0)
            if ch and ch % 10 == 0:
                start = max(1, ch - 9)
                if not NoteService.has_review_for(work_id, start, ch):
                    risks.append(("YELLOW", f"已到第{ch}章，建议导入第{start}—{ch}章联合审查/阶段修订说明。"))
        conn = connect()
        expired = conn.execute("SELECT COUNT(*) AS c FROM writing_packages WHERE work_id=? AND status='EXPIRED'", (work_id,)).fetchone()["c"]
        if expired:
            risks.append(("YELLOW", f"存在 {expired} 个已过期写作包，请勿继续使用。"))
        active_old = 0
        if current:
            active_old = conn.execute("SELECT COUNT(*) AS c FROM writing_packages WHERE work_id=? AND status='ACTIVE' AND base_version_id<>?", (work_id, current["id"])).fetchone()["c"]
        if active_old:
            risks.append(("RED", f"存在 {active_old} 个基于非当前有效版本的 ACTIVE 写作包，建议作废。"))
        if work:
            ch = int(work["current_chapter"] or 0)
            clues = conn.execute("SELECT * FROM clue_items WHERE work_id=? AND current_status NOT IN ('已回收','已废弃')", (work_id,)).fetchall()
            for clue in clues:
                last = int(clue["last_progress_chapter"] or clue["first_chapter"] or 0)
                if ch and last and ch - last >= 20:
                    risks.append(("YELLOW", f"伏笔《{clue['name']}》已超过 {ch-last} 章未推进。"))
        conn.close()
        if any(r[0] == "RED" for r in risks): level = "RED"
        elif any(r[0] == "YELLOW" for r in risks): level = "YELLOW"
        return level, risks


@dataclass
class ImportPackage:
    fields: dict
    blocks: dict
    errors: list
    def ok(self): return not self.errors


class ImportPackageService:
    BLOCK_RE = re.compile(r"\[(\w+)\]\s*(.*?)\s*\[/\1\]", re.S)

    @staticmethod
    def parse(raw: str) -> ImportPackage:
        errors = []; text = raw or ""
        if "===IMPORT_PACKAGE_START===" not in text or "===IMPORT_PACKAGE_END===" not in text:
            errors.append("缺少 IMPORT_PACKAGE_START / END 标记。")
        fields = {}
        header = text.split("[MANUSCRIPT]", 1)[0]
        header = header.replace("===IMPORT_PACKAGE_START===", "").replace("===IMPORT_PACKAGE_END===", "")
        for line in header.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                key = k.strip().upper()
                if re.fullmatch(r"[A-Z_]+", key): fields[key] = v.strip()
        blocks = {m.group(1).upper(): m.group(2).strip() for m in ImportPackageService.BLOCK_RE.finditer(text)}
        required = ["IP_NAME", "WORK_TITLE", "PACKAGE_TYPE", "CHAPTER_START", "CHAPTER_END", "VERSION", "STATUS"]
        for k in required:
            if not fields.get(k): errors.append(f"缺少字段：{k}")
        for k in ["CHAPTER_START", "CHAPTER_END", "CURRENT_CHAPTER_AFTER_IMPORT"]:
            if fields.get(k):
                try: int(fields[k])
                except Exception: errors.append(f"字段 {k} 必须是阿拉伯数字。")
        if "MANUSCRIPT" not in blocks and "STAGE_NOTE" not in blocks:
            errors.append("至少需要 [MANUSCRIPT] 或 [STAGE_NOTE] 内容。")
        return ImportPackage(fields, blocks, errors)

    @staticmethod
    def import_package(raw: str):
        pkg = ImportPackageService.parse(raw)
        if not pkg.ok(): return False, pkg.errors, None
        f, b = pkg.fields, pkg.blocks
        ip_id = IPService.get_or_create(f.get("IP_NAME"), f.get("IP_TYPE", ""))
        work_id = WorkService.get_or_create(ip_id, f.get("WORK_TITLE"), f.get("WORK_TYPE", "long_novel"), f.get("PLATFORM", "番茄小说"), f.get("CURRENT_VOLUME", ""))
        cs, ce = int(f["CHAPTER_START"]), int(f["CHAPTER_END"])
        manuscript = b.get("MANUSCRIPT", "")
        title = f"第{cs}—{ce}章 {f.get('VERSION')}"
        version_id = None
        if manuscript.strip():
            version_id = VersionService.create_version(work_id, cs, ce, f.get("VERSION"), title, f.get("PACKAGE_TYPE"), f.get("STATUS"), manuscript, f.get("REPLACES", ""), b.get("SUMMARY", ""))
        if b.get("STAGE_NOTE"):
            NoteService.save_stage_note(work_id, version_id, cs, ce, f"第{cs}—{ce}章阶段说明", b.get("STAGE_NOTE"), f.get("RISK_LEVEL", "NONE"))
        if b.get("OUTLINE_RULES"):
            GuardService.add_outline_rule(work_id, "导入规则", f"第{cs}—{ce}章导入规则", b.get("OUTLINE_RULES"), "P1")
        if version_id and f.get("IS_CURRENT_EFFECTIVE", "").lower() in ["true", "yes", "1", "是"]:
            VersionService.set_current(work_id, version_id)
            if f.get("CURRENT_VOLUME"):
                WorkService.update_current(work_id, version_id, int(f.get("CURRENT_CHAPTER_AFTER_IMPORT") or ce), f"生成第{ce+1}—{ce+5}章写作包", current_volume=f.get("CURRENT_VOLUME"))
        BackupService.create_backup("import_package", f"导入更新包：{title}", ip_id=ip_id, work_id=work_id, version_id=version_id, related_range=f"{cs}-{ce}")
        return True, ["导入成功。"], work_id


class RawImportService:
    @staticmethod
    def infer_range(text: str):
        chapters = split_chapters(text)
        nums = [c["number"] for c in chapters if c.get("number") is not None]
        if nums: return min(nums), max(nums), chapters
        return 1, 1, chapters

    @staticmethod
    def import_raw(ip_name, work_title, work_type, platform, current_volume, chapter_start, chapter_end, version, status, package_type, is_current, raw_text, stage_note=""):
        ip_id = IPService.get_or_create(ip_name or "未命名IP")
        work_id = WorkService.get_or_create(ip_id, work_title or "未命名作品", work_type or "long_novel", platform or "番茄小说", current_volume or "")
        cs, ce = int(chapter_start), int(chapter_end)
        version_id = VersionService.create_version(work_id, cs, ce, version or "V1.0", f"第{cs}—{ce}章 {version or 'V1.0'}", package_type or "raw_import", status or "DRAFT", raw_text or "")
        if stage_note.strip(): NoteService.save_stage_note(work_id, version_id, cs, ce, f"第{cs}—{ce}章阶段说明", stage_note)
        if is_current: VersionService.set_current(work_id, version_id)
        return work_id, version_id


class WritingPackageService:
    @staticmethod
    def generate(work_id: int, target_start=None, target_end=None):
        work = WorkService.get(work_id); current = VersionService.current(work_id)
        if not work: raise ValueError("未找到作品。")
        if not current: raise ValueError("请先设置当前有效版本。")
        ip = IPService.get(work["ip_id"])
        base_end = int(current["chapter_end"] or work["current_chapter"] or 0)
        ts = int(target_start or base_end + 1); te = int(target_end or ts + 4)
        latest_note = NoteService.latest_stage_note(work_id)
        rules = GuardService.list_outline_rules(work_id)
        chars = GuardService.list_characters(work_id)
        clues = GuardService.list_clues(work_id)
        risk_level, risks = RiskService.risk_report(work_id)
        warning_text = "\n".join([f"- [{lv}] {msg}" for lv, msg in risks]) or "- 暂无规则风险。"
        rules_text = "\n".join([f"- 【{r['rule_type']}｜{r['priority']}】{r['title']}：{r['content']}" for r in rules]) or "暂无大纲锁定规则。"
        chars_text = "\n".join([f"- {c['name']}｜{c['role']}｜当前：{c['current_state']}｜禁止偏移：{c['forbidden_drift']}" for c in chars]) or "暂无人物状态卡。"
        clues_text = "\n".join([f"- {c['name']}｜状态：{c['current_status']}｜首次：{c['first_chapter']}｜最近推进：{c['last_progress_chapter']}｜预计回收：{c['expected_resolve_chapter']}｜风险：{c['risk_level']}" for c in clues]) or "暂无伏笔台账。"
        content = f"""# 给 ChatGPT 的写作包

项目名：{work['title']}
作者/IP：{ip['name'] if ip else ''}
平台：{work['platform'] or ''}
作品类型：{work['work_type'] or ''}
当前卷：{work['current_volume'] or ''}
当前章节：第{work['current_chapter'] or current['chapter_end']}章
目标章节：第{ts}—{te}章
当前有效版本：第{current['chapter_start']}—{current['chapter_end']}章 {current['version_label']}｜{current['status']}｜CURRENT
风险灯：{risk_level}

> 注意：本写作包基于当前有效版本生成。历史草稿、已替代版本、过期写作包不作为承接依据。

---

## 〇、写作前风险提示
{warning_text}

---

## 一、大纲锁定区 / 防跑偏规则
{rules_text}

---

## 二、人物状态卡
{chars_text}

---

## 三、伏笔台账
{clues_text}

---

## 四、当前有效正文 / 修订稿

{current['content'] or ''}

---

## 五、阶段说明 / 总控补丁

{latest_note['content'] if latest_note else '暂无阶段说明。'}

---

## 六、本次写作任务

请严格承接当前有效版本，继续写第{ts}—{te}章。

要求：

1. 不要承接旧版草稿。
2. 不要推翻当前有效版本。
3. 女主不能退回被动挨打状态。
4. 每章必须有明确推进。
5. 每章结尾保留自然钩子。
6. 必须遵守大纲锁定区、人物状态卡、伏笔台账。
7. 写完后输出五章说明书。

---

## 七、写完后必须输出

# 第{ts}—{te}章五章说明书

## 一、本单元总体摘要
## 二、每章剧情拆解
## 三、人物状态变化
## 四、伏笔新增
## 五、伏笔推进
## 六、伏笔回收
## 七、证据链变化
## 八、事业线变化
## 九、爽点与反转
## 十、与大纲符合度
## 十一、风险提醒
## 十二、下一单元承接事项
"""
        conn = connect(); now = now_str()
        cur = conn.execute("""INSERT INTO writing_packages
            (work_id, target_start, target_end, base_version_id, title, content, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)""", (work_id, ts, te, current["id"], f"第{ts}—{te}章写作包", content, now, now))
        conn.commit(); pid = cur.lastrowid; conn.close()
        BackupService.create_backup("generate_package", f"生成第{ts}—{te}章写作包", work_id=work_id, version_id=current["id"], related_range=f"{ts}-{te}")
        return pid, content

    @staticmethod
    def list_packages(work_id: int):
        conn = connect(); rows = conn.execute("SELECT * FROM writing_packages WHERE work_id=? ORDER BY id DESC", (work_id,)).fetchall(); conn.close(); return rows

    @staticmethod
    def export_package(package_id: int):
        conn = connect(); p = conn.execute("SELECT * FROM writing_packages WHERE id=?", (package_id,)).fetchone(); conn.close()
        if not p: raise ValueError("未找到写作包。")
        out = EXPORT_DIR / sanitize_filename(f"{p['title']}_{safe_time()}.md")
        return write_text(out, p["content"])


class DiffService:
    @staticmethod
    def paragraph_lines(text: str):
        return [p.strip() for p in re.split(r"\n+", text or "") if p.strip()]

    @staticmethod
    def compare_versions(work_id: int, old_version_id: int, new_version_id: int):
        old = VersionService.get(old_version_id); new = VersionService.get(new_version_id)
        if not old or not new: raise ValueError("版本不存在。")
        old_lines, new_lines = DiffService.paragraph_lines(old["content"]), DiffService.paragraph_lines(new["content"])
        diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=old["title"], tofile=new["title"], lineterm=""))
        added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
        deleted = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
        summary = f"新增段落约 {added} 处，删除段落约 {deleted} 处。旧版字数 {old['word_count']}，新版字数 {new['word_count']}，变化 {int(new['word_count'] or 0)-int(old['word_count'] or 0)} 字。"
        report = f"""# 版本对比报告

作品ID：{work_id}
旧版本：{old['title']}｜ID {old['id']}
新版本：{new['title']}｜ID {new['id']}
生成时间：{now_str()}

## 摘要
{summary}

## 统一差异文本

```diff
{chr(10).join(diff[:4000])}
```

> 注：本报告为基础文本对比，不等同于文学质量审稿。需要判断人物、节奏、爽点、伏笔风险时，请生成偏纲审查包交给 ChatGPT 审查。
"""
        conn = connect()
        cur = conn.execute("""INSERT INTO diff_reports
            (work_id, old_version_ids, new_version_id, title, summary, markdown_report, html_report, created_at)
            VALUES (?, ?, ?, ?, ?, ?, '', ?)""", (work_id, str(old_version_id), new_version_id, f"{old['version_label']} 对比 {new['version_label']}", summary, report, now_str()))
        conn.commit(); rid = cur.lastrowid; conn.close()
        return rid, summary, report

    @staticmethod
    def export_report(report_id: int):
        conn = connect(); r = conn.execute("SELECT * FROM diff_reports WHERE id=?", (report_id,)).fetchone(); conn.close()
        if not r: raise ValueError("未找到对比报告。")
        out = EXPORT_DIR / sanitize_filename(f"版本对比报告_{report_id}_{safe_time()}.md")
        return write_text(out, r["markdown_report"])


class AuditPackageService:
    @staticmethod
    def generate(work_id: int):
        work = WorkService.get(work_id); current = VersionService.current(work_id)
        if not work: raise ValueError("未找到作品。")
        ip = IPService.get(work["ip_id"])
        rules = GuardService.list_outline_rules(work_id)
        chars = GuardService.list_characters(work_id)
        clues = GuardService.list_clues(work_id)
        level, risks = RiskService.risk_report(work_id)
        latest_note = NoteService.latest_stage_note(work_id)
        content = f"""# 偏纲审查包

作品：{work['title']}
作者/IP：{ip['name'] if ip else ''}
平台：{work['platform'] or ''}
当前卷：{work['current_volume'] or ''}
当前章节：{work['current_chapter'] or 0}
风险灯：{level}
生成时间：{now_str()}

## 一、风险提示
{chr(10).join([f'- [{lv}] {msg}' for lv, msg in risks]) or '暂无规则风险。'}

## 二、当前有效正文
{current['content'] if current else '暂无当前有效版本。'}

## 三、最近阶段说明
{latest_note['content'] if latest_note else '暂无阶段说明。'}

## 四、大纲锁定区
{chr(10).join([f'- 【{r['rule_type']}】{r['title']}：{r['content']}' for r in rules]) or '暂无。'}

## 五、人物状态卡
{chr(10).join([f'- {c['name']}：{c['current_state']}；禁止偏移：{c['forbidden_drift']}' for c in chars]) or '暂无。'}

## 六、伏笔台账
{chr(10).join([f'- {c['name']}：状态{c['current_status']}，最近推进{c['last_progress_chapter']}，预计回收{c['expected_resolve_chapter']}。' for c in clues]) or '暂无。'}

## 七、请 ChatGPT 审查
请从番茄/长篇编辑角度判断：是否偏纲，人物是否偏移，伏笔是否断裂，节奏是否变水，下一阶段应如何修正。
"""
        out = EXPORT_DIR / sanitize_filename(f"偏纲审查包_{work['title']}_{safe_time()}.md")
        return write_text(out, content)
