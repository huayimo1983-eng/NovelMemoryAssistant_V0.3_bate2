from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QInputDialog,
    QTextEdit, QPlainTextEdit, QLineEdit, QComboBox, QSpinBox, QCheckBox, QFileDialog,
    QFormLayout, QSplitter, QFrame
)

from app.ui.styles import APP_STYLE
from app.services import (
    IPService, WorkService, VersionService, NoteService, ImportPackageService,
    RawImportService, WritingPackageService, GuardService, RiskService, DiffService,
    BackupService, AuditPackageService
)
from app.core.utils import extract_text_from_docx, split_chapters, write_text, sanitize_filename, safe_time
from app.core.paths import EXPORT_DIR


def info(parent, title, text, icon=QMessageBox.Information):
    box = QMessageBox(parent)
    box.setIcon(icon); box.setWindowTitle(title); box.setText(text); box.exec()


def set_table(table, rows, headers, getter):
    table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels(headers); table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        vals = getter(row)
        for c, v in enumerate(vals):
            table.setItem(r, c, QTableWidgetItem(str(v if v is not None else "")))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小说项目管理系统 V0.3-beta")
        self.resize(1380, 860)
        self.setStyleSheet(APP_STYLE)
        self.current_ip_id = None
        self.current_work_id = None
        self.pages = {}
        self._build()

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        self.nav = QListWidget(); self.nav.setFixedWidth(230)
        for item in ["IP 工作台", "作品列表", "作品驾驶舱", "导入中心", "版本管理", "版本对比", "大纲防偏", "伏笔台账", "人物状态", "写作包", "备份日志"]:
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self.on_nav)
        outer.addWidget(self.nav)
        self.stack = QStackedWidget(); outer.addWidget(self.stack, 1)

        self.pages["ip"] = IPDashboardPage(self)
        self.pages["works"] = WorkListPage(self)
        self.pages["home"] = WorkHomePage(self)
        self.pages["import"] = ImportPage(self)
        self.pages["versions"] = VersionPage(self)
        self.pages["diff"] = DiffPage(self)
        self.pages["guard"] = GuardPage(self)
        self.pages["clues"] = CluePage(self)
        self.pages["chars"] = CharacterPage(self)
        self.pages["packages"] = PackagePage(self)
        self.pages["logs"] = LogPage(self)
        for p in self.pages.values():
            self.stack.addWidget(p)
        self.nav.setCurrentRow(0)

    def on_nav(self, row):
        names = ["ip", "works", "home", "import", "versions", "diff", "guard", "clues", "chars", "packages", "logs"]
        if row < 0: return
        key = names[row]
        if key != "ip" and key != "works" and not self.require_work():
            self.nav.setCurrentRow(0); return
        if key == "works" and not self.current_ip_id:
            info(self, "未选择 IP", "请先进入一个 IP。", QMessageBox.Warning); self.nav.setCurrentRow(0); return
        self.stack.setCurrentWidget(self.pages[key])
        self.pages[key].refresh()

    def require_work(self):
        return bool(self.current_work_id)

    def go_works(self, ip_id):
        self.current_ip_id = ip_id; self.nav.setCurrentRow(1)

    def go_home(self, work_id):
        self.current_work_id = work_id; self.nav.setCurrentRow(2)


class IPDashboardPage(QWidget):
    def __init__(self, main):
        super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self)
        row = QHBoxLayout(); title = QLabel("IP 工作台"); title.setObjectName("TitleLabel"); row.addWidget(title); row.addStretch()
        btn = QPushButton("+ 新建 IP"); btn.setObjectName("PrimaryButton"); btn.clicked.connect(self.create_ip); row.addWidget(btn); layout.addLayout(row)
        self.table = QTableWidget(); layout.addWidget(self.table)
        row2 = QHBoxLayout(); open_btn = QPushButton("进入选中 IP"); open_btn.clicked.connect(self.open_selected); row2.addWidget(open_btn)
        refresh_btn = QPushButton("刷新"); refresh_btn.clicked.connect(self.refresh); row2.addWidget(refresh_btn); row2.addStretch(); layout.addLayout(row2)
    def refresh(self):
        rows = IPService.list_all()
        set_table(self.table, rows, ["ID", "IP 名称", "类型", "作品数", "更新时间"], lambda r: [r["id"], r["name"], r["ip_type"], r["work_count"], r["updated_at"]])
    def create_ip(self):
        name, ok = QInputDialog.getText(self, "新建 IP", "IP 名称：", text="晚灯照雪")
        if not ok or not name.strip(): return
        ip_type, ok = QInputDialog.getText(self, "IP 类型", "类型：", text="番茄女频")
        IPService.get_or_create(name.strip(), ip_type.strip() if ok else "")
        self.refresh()
    def selected_id(self):
        r = self.table.currentRow()
        if r < 0: info(self, "未选择", "请选择一个 IP。", QMessageBox.Warning); return None
        return int(self.table.item(r, 0).text())
    def open_selected(self):
        ip_id = self.selected_id()
        if ip_id: self.main.go_works(ip_id)


class WorkListPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); row = QHBoxLayout(); self.title = QLabel("作品列表"); self.title.setObjectName("TitleLabel"); row.addWidget(self.title); row.addStretch()
        btn = QPushButton("+ 新建作品"); btn.setObjectName("PrimaryButton"); btn.clicked.connect(self.create_work); row.addWidget(btn); layout.addLayout(row)
        self.table = QTableWidget(); layout.addWidget(self.table)
        row2 = QHBoxLayout(); open_btn = QPushButton("进入选中作品"); open_btn.clicked.connect(self.open_selected); row2.addWidget(open_btn); row2.addStretch(); layout.addLayout(row2)
    def refresh(self):
        ip = IPService.get(self.main.current_ip_id) if self.main.current_ip_id else None
        self.title.setText(f"作品列表：{ip['name'] if ip else ''}")
        rows = WorkService.list_by_ip(self.main.current_ip_id) if self.main.current_ip_id else []
        set_table(self.table, rows, ["ID", "作品名", "类型", "平台", "当前卷", "当前章", "有效版本", "下一步"], lambda w: [w["id"], w["title"], w["work_type"], w["platform"], w["current_volume"], w["current_chapter"], w["current_effective_version_id"], w["next_action"]])
    def create_work(self):
        title, ok = QInputDialog.getText(self, "新建作品", "作品名：", text="重生八零，侨批到账后我断亲南下")
        if not ok or not title.strip(): return
        work_type, _ = QInputDialog.getText(self, "作品类型", "类型：", text="long_novel")
        platform, _ = QInputDialog.getText(self, "平台", "平台：", text="番茄小说")
        current_volume, _ = QInputDialog.getText(self, "当前卷", "当前卷：", text="第四卷")
        WorkService.create(self.main.current_ip_id, title.strip(), work_type.strip(), platform.strip(), current_volume=current_volume.strip())
        self.refresh()
    def selected_id(self):
        r = self.table.currentRow()
        if r < 0: info(self, "未选择", "请选择一个作品。", QMessageBox.Warning); return None
        return int(self.table.item(r, 0).text())
    def open_selected(self):
        wid = self.selected_id()
        if wid: self.main.go_home(wid)


class WorkHomePage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def card(self, title, body):
        f = QFrame(); f.setObjectName("Card"); l = QVBoxLayout(f); t = QLabel(title); t.setObjectName("SubTitle"); l.addWidget(t); b = QLabel(body); b.setWordWrap(True); l.addWidget(b); return f
    def _build(self):
        self.layout = QVBoxLayout(self)
    def refresh(self):
        while self.layout.count():
            item = self.layout.takeAt(0); w = item.widget();
            if w: w.deleteLater()
        work = WorkService.get(self.main.current_work_id); current = VersionService.current(self.main.current_work_id)
        title = QLabel(f"作品驾驶舱：{work['title'] if work else ''}"); title.setObjectName("TitleLabel"); self.layout.addWidget(title)
        level, risks = RiskService.risk_report(self.main.current_work_id)
        grid = QHBoxLayout()
        grid.addWidget(self.card("当前进度", f"当前卷：{work['current_volume'] or '未填写'}\n当前章节：第{work['current_chapter'] or 0}章\n下一步：{work['next_action'] or '未生成'}"))
        grid.addWidget(self.card("当前有效版本", f"{current['title'] if current else '未设置'}\n范围：{current['chapter_start'] if current else ''}—{current['chapter_end'] if current else ''}\n状态：{current['status'] if current else ''}"))
        grid.addWidget(self.card("风险灯", f"{level}\n" + ("\n".join([f"[{lv}] {msg}" for lv, msg in risks]) if risks else "暂无规则风险。")))
        self.layout.addLayout(grid)
        row = QHBoxLayout()
        for text, nav in [("导入中心", 3), ("生成写作包", 9), ("版本对比", 5), ("生成偏纲审查包", None)]:
            btn = QPushButton(text)
            if nav is None: btn.clicked.connect(self.export_audit)
            else: btn.clicked.connect(lambda _, n=nav: self.main.nav.setCurrentRow(n))
            row.addWidget(btn)
        row.addStretch(); self.layout.addLayout(row); self.layout.addStretch()
    def export_audit(self):
        try:
            p = AuditPackageService.generate(self.main.current_work_id)
            info(self, "已生成", f"偏纲审查包已导出：\n{p}")
        except Exception as e:
            info(self, "失败", str(e), QMessageBox.Warning)


class ImportPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("导入中心"); title.setObjectName("TitleLabel"); layout.addWidget(title)
        splitter = QSplitter(Qt.Horizontal); layout.addWidget(splitter, 1)
        left = QWidget(); ll = QVBoxLayout(left); ll.addWidget(QLabel("A. 标准 ChatGPT 导入包"))
        self.package_text = QPlainTextEdit(); self.package_text.setPlaceholderText("粘贴 ===IMPORT_PACKAGE_START=== ... ===IMPORT_PACKAGE_END===")
        ll.addWidget(self.package_text, 1); row = QHBoxLayout(); parse_btn = QPushButton("解析并入库"); parse_btn.setObjectName("PrimaryButton"); parse_btn.clicked.connect(self.import_package); row.addWidget(parse_btn); ll.addLayout(row)
        splitter.addWidget(left)
        right = QWidget(); rl = QVBoxLayout(right); rl.addWidget(QLabel("B. DOCX / 普通正文快速入库"))
        form = QFormLayout(); self.ip_name = QLineEdit("晚灯照雪"); self.work_title = QLineEdit("重生八零，侨批到账后我断亲南下"); self.work_type = QLineEdit("long_novel"); self.platform = QLineEdit("番茄小说"); self.volume = QLineEdit("第四卷")
        self.cs = QSpinBox(); self.cs.setMaximum(9999); self.cs.setValue(1); self.ce = QSpinBox(); self.ce.setMaximum(9999); self.ce.setValue(5)
        self.version = QLineEdit("V1.0"); self.status = QLineEdit("DRAFT"); self.ptype = QLineEdit("raw_import"); self.is_current = QCheckBox("设为当前有效版本"); self.is_current.setChecked(True)
        for label, w in [("IP", self.ip_name), ("作品", self.work_title), ("作品类型", self.work_type), ("平台", self.platform), ("当前卷", self.volume), ("起始章", self.cs), ("结束章", self.ce), ("版本", self.version), ("状态", self.status), ("稿件类型", self.ptype), ("当前有效", self.is_current)]: form.addRow(label, w)
        rl.addLayout(form)
        rowf = QHBoxLayout(); load_btn = QPushButton("选择 DOCX/TXT/MD"); load_btn.clicked.connect(self.load_file); infer_btn = QPushButton("识别章节范围"); infer_btn.clicked.connect(self.infer_range); rowf.addWidget(load_btn); rowf.addWidget(infer_btn); rl.addLayout(rowf)
        self.raw_text = QPlainTextEdit(); self.raw_text.setPlaceholderText("这里可以粘贴普通正文或说明书。")
        rl.addWidget(self.raw_text, 1); rl.addWidget(QLabel("阶段说明 / 五章说明书，可选")); self.stage_note = QPlainTextEdit(); self.stage_note.setMaximumHeight(150); rl.addWidget(self.stage_note)
        import_raw_btn = QPushButton("快速入库"); import_raw_btn.setObjectName("PrimaryButton"); import_raw_btn.clicked.connect(self.import_raw); rl.addWidget(import_raw_btn)
        splitter.addWidget(right); splitter.setSizes([680, 680])
    def refresh(self): pass
    def import_package(self):
        ok, msgs, work_id = ImportPackageService.import_package(self.package_text.toPlainText())
        info(self, "导入结果", "\n".join(msgs), QMessageBox.Information if ok else QMessageBox.Warning)
        if ok and work_id: self.main.current_work_id = work_id
    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择文件", "", "Documents (*.docx *.txt *.md);;All Files (*)")
        if not path: return
        try:
            if path.lower().endswith(".docx"):
                text = extract_text_from_docx(path)
            else:
                text = Path(path).read_text(encoding="utf-8")
            self.raw_text.setPlainText(text); self.infer_range()
        except Exception as e:
            info(self, "读取失败", str(e), QMessageBox.Warning)
    def infer_range(self):
        chapters = split_chapters(self.raw_text.toPlainText())
        nums = [c["number"] for c in chapters if c.get("number")]
        if nums:
            self.cs.setValue(min(nums)); self.ce.setValue(max(nums)); info(self, "识别完成", f"识别到 {len(nums)} 个章节：{min(nums)}—{max(nums)}。")
        else:
            info(self, "未识别", "没有识别到章节标题。支持：第1章、第一章、第一百五十一章、第1节、第一小节。", QMessageBox.Warning)
    def import_raw(self):
        try:
            work_id, vid = RawImportService.import_raw(self.ip_name.text(), self.work_title.text(), self.work_type.text(), self.platform.text(), self.volume.text(), self.cs.value(), self.ce.value(), self.version.text(), self.status.text(), self.ptype.text(), self.is_current.isChecked(), self.raw_text.toPlainText(), self.stage_note.toPlainText())
            self.main.current_work_id = work_id; info(self, "成功", f"已入库，版本ID：{vid}")
        except Exception as e:
            info(self, "失败", str(e), QMessageBox.Warning)


class VersionPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("版本管理"); title.setObjectName("TitleLabel"); layout.addWidget(title); self.table = QTableWidget(); layout.addWidget(self.table)
        row = QHBoxLayout(); cur_btn = QPushButton("设为当前有效版本"); cur_btn.clicked.connect(self.set_current); row.addWidget(cur_btn); refresh_btn = QPushButton("刷新"); refresh_btn.clicked.connect(self.refresh); row.addWidget(refresh_btn); row.addStretch(); layout.addLayout(row)
    def refresh(self):
        rows = VersionService.list_versions(self.main.current_work_id)
        set_table(self.table, rows, ["ID", "标题", "范围", "版本", "类型", "状态", "当前", "字数", "替代"], lambda v: [v["id"], v["title"], f"{v['chapter_start']}—{v['chapter_end']}", v["version_label"], v["manuscript_type"], v["status"], "是" if v["is_current_effective"] else "", v["word_count"], v["replaces"]])
    def selected_id(self):
        r = self.table.currentRow()
        if r < 0: info(self, "未选择", "请选择一个版本。", QMessageBox.Warning); return None
        return int(self.table.item(r, 0).text())
    def set_current(self):
        vid = self.selected_id()
        if not vid: return
        try: VersionService.set_current(self.main.current_work_id, vid); self.refresh(); info(self, "完成", "已设置当前有效版本。")
        except Exception as e: info(self, "失败", str(e), QMessageBox.Warning)


class DiffPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self.report_id = None; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("版本对比"); title.setObjectName("TitleLabel"); layout.addWidget(title)
        row = QHBoxLayout(); self.old_combo = QComboBox(); self.new_combo = QComboBox(); row.addWidget(QLabel("旧版本")); row.addWidget(self.old_combo); row.addWidget(QLabel("新版本")); row.addWidget(self.new_combo)
        btn = QPushButton("开始对比"); btn.setObjectName("PrimaryButton"); btn.clicked.connect(self.compare); row.addWidget(btn); exp = QPushButton("导出报告"); exp.clicked.connect(self.export); row.addWidget(exp); layout.addLayout(row)
        self.report = QPlainTextEdit(); layout.addWidget(self.report, 1)
    def refresh(self):
        rows = VersionService.list_versions(self.main.current_work_id); self.old_combo.clear(); self.new_combo.clear()
        for v in rows:
            label = f"ID{v['id']}｜{v['title']}｜{v['version_label']}｜{v['status']}"
            self.old_combo.addItem(label, v["id"]); self.new_combo.addItem(label, v["id"])
    def compare(self):
        try:
            rid, summary, report = DiffService.compare_versions(self.main.current_work_id, self.old_combo.currentData(), self.new_combo.currentData())
            self.report_id = rid; self.report.setPlainText(report); info(self, "对比完成", summary)
        except Exception as e: info(self, "失败", str(e), QMessageBox.Warning)
    def export(self):
        if not self.report_id: info(self, "未生成", "请先生成对比报告。", QMessageBox.Warning); return
        try: p = DiffService.export_report(self.report_id); info(self, "已导出", str(p))
        except Exception as e: info(self, "失败", str(e), QMessageBox.Warning)


class GuardPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("大纲防偏 / 锁定规则"); title.setObjectName("TitleLabel"); layout.addWidget(title)
        form = QFormLayout(); self.rule_type = QComboBox(); self.rule_type.addItems(["全书主线", "本卷目标", "十章目标", "人物红线", "禁止事项", "平台节奏", "其他"]); self.rule_title = QLineEdit(); self.rule_content = QPlainTextEdit(); self.rule_content.setMaximumHeight(100); self.priority = QComboBox(); self.priority.addItems(["P0", "P1", "P2"])
        form.addRow("规则类型", self.rule_type); form.addRow("标题", self.rule_title); form.addRow("内容", self.rule_content); form.addRow("优先级", self.priority); layout.addLayout(form)
        btn = QPushButton("添加规则"); btn.setObjectName("PrimaryButton"); btn.clicked.connect(self.add); layout.addWidget(btn)
        self.table = QTableWidget(); layout.addWidget(self.table, 1)
    def refresh(self):
        rows = GuardService.list_outline_rules(self.main.current_work_id)
        set_table(self.table, rows, ["ID", "类型", "标题", "优先级", "内容"], lambda r: [r["id"], r["rule_type"], r["title"], r["priority"], r["content"][:120]])
    def add(self):
        GuardService.add_outline_rule(self.main.current_work_id, self.rule_type.currentText(), self.rule_title.text(), self.rule_content.toPlainText(), self.priority.currentText())
        self.rule_title.clear(); self.rule_content.clear(); self.refresh()


class CluePage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("伏笔台账"); title.setObjectName("TitleLabel"); layout.addWidget(title)
        form = QFormLayout(); self.name = QLineEdit(); self.first = QSpinBox(); self.first.setMaximum(9999); self.last = QSpinBox(); self.last.setMaximum(9999); self.expected = QSpinBox(); self.expected.setMaximum(9999); self.people = QLineEdit(); self.status = QComboBox(); self.status.addItems(["新增", "推进中", "待回收", "已回收", "高风险", "已废弃"]); self.notes = QPlainTextEdit(); self.notes.setMaximumHeight(80)
        for label, w in [("名称", self.name), ("首次章节", self.first), ("最近推进", self.last), ("预计回收", self.expected), ("相关人物", self.people), ("状态", self.status), ("备注", self.notes)]: form.addRow(label, w)
        layout.addLayout(form); btn = QPushButton("添加伏笔"); btn.setObjectName("PrimaryButton"); btn.clicked.connect(self.add); layout.addWidget(btn); self.table = QTableWidget(); layout.addWidget(self.table, 1)
    def refresh(self):
        rows = GuardService.list_clues(self.main.current_work_id)
        set_table(self.table, rows, ["ID", "名称", "首次", "最近", "预计", "状态", "风险", "人物", "备注"], lambda c: [c["id"], c["name"], c["first_chapter"], c["last_progress_chapter"], c["expected_resolve_chapter"], c["current_status"], c["risk_level"], c["related_people"], c["notes"]])
    def add(self):
        GuardService.add_clue(self.main.current_work_id, self.name.text(), self.first.value(), self.last.value(), self.expected.value(), self.people.text(), self.status.currentText(), self.notes.toPlainText()); self.name.clear(); self.notes.clear(); self.refresh()


class CharacterPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("人物状态卡"); title.setObjectName("TitleLabel"); layout.addWidget(title)
        form = QFormLayout(); self.name = QLineEdit(); self.role = QLineEdit(); self.state = QPlainTextEdit(); self.state.setMaximumHeight(80); self.must = QPlainTextEdit(); self.must.setMaximumHeight(80); self.forbid = QPlainTextEdit(); self.forbid.setMaximumHeight(80); self.know = QPlainTextEdit(); self.know.setMaximumHeight(80); self.ch = QSpinBox(); self.ch.setMaximum(9999)
        for label, w in [("人物名", self.name), ("角色功能", self.role), ("当前状态", self.state), ("必须保持", self.must), ("禁止偏移", self.forbid), ("掌握信息", self.know), ("更新章节", self.ch)]: form.addRow(label, w)
        layout.addLayout(form); btn = QPushButton("添加人物状态"); btn.setObjectName("PrimaryButton"); btn.clicked.connect(self.add); layout.addWidget(btn); self.table = QTableWidget(); layout.addWidget(self.table, 1)
    def refresh(self):
        rows = GuardService.list_characters(self.main.current_work_id)
        set_table(self.table, rows, ["ID", "人物", "角色", "当前状态", "禁止偏移", "更新章"], lambda c: [c["id"], c["name"], c["role"], c["current_state"][:80], c["forbidden_drift"][:80], c["last_update_chapter"]])
    def add(self):
        GuardService.add_character(self.main.current_work_id, self.name.text(), self.role.text(), self.state.toPlainText(), self.must.toPlainText(), self.forbid.toPlainText(), self.know.toPlainText(), self.ch.value()); self.name.clear(); self.refresh()


class PackagePage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("写作包"); title.setObjectName("TitleLabel"); layout.addWidget(title)
        row = QHBoxLayout(); self.ts = QSpinBox(); self.ts.setMaximum(9999); self.te = QSpinBox(); self.te.setMaximum(9999); row.addWidget(QLabel("目标起始")); row.addWidget(self.ts); row.addWidget(QLabel("目标结束")); row.addWidget(self.te); gen = QPushButton("生成写作包"); gen.setObjectName("PrimaryButton"); gen.clicked.connect(self.generate); row.addWidget(gen); exp = QPushButton("导出选中写作包"); exp.clicked.connect(self.export); row.addWidget(exp); row.addStretch(); layout.addLayout(row)
        self.table = QTableWidget(); layout.addWidget(self.table); self.content = QPlainTextEdit(); layout.addWidget(self.content, 1)
        self.table.itemSelectionChanged.connect(self.show_content)
    def refresh(self):
        work = WorkService.get(self.main.current_work_id); ch = work["current_chapter"] or 0; self.ts.setValue(ch + 1); self.te.setValue(ch + 5)
        rows = WritingPackageService.list_packages(self.main.current_work_id)
        set_table(self.table, rows, ["ID", "标题", "目标", "基于版本", "状态", "过期原因", "时间"], lambda p: [p["id"], p["title"], f"{p['target_start']}—{p['target_end']}", p["base_version_id"], p["status"], p["expired_reason"], p["created_at"]])
    def generate(self):
        try:
            pid, content = WritingPackageService.generate(self.main.current_work_id, self.ts.value(), self.te.value()); self.content.setPlainText(content); self.refresh(); info(self, "完成", f"已生成写作包 ID：{pid}")
        except Exception as e: info(self, "失败", str(e), QMessageBox.Warning)
    def selected_id(self):
        r = self.table.currentRow(); return int(self.table.item(r, 0).text()) if r >= 0 else None
    def show_content(self):
        pid = self.selected_id()
        if not pid: return
        for p in WritingPackageService.list_packages(self.main.current_work_id):
            if p["id"] == pid: self.content.setPlainText(p["content"]); return
    def export(self):
        pid = self.selected_id()
        if not pid: info(self, "未选择", "请选择写作包。", QMessageBox.Warning); return
        try: p = WritingPackageService.export_package(pid); info(self, "已导出", str(p))
        except Exception as e: info(self, "失败", str(e), QMessageBox.Warning)


class LogPage(QWidget):
    def __init__(self, main): super().__init__(); self.main = main; self._build()
    def _build(self):
        layout = QVBoxLayout(self); title = QLabel("备份日志"); title.setObjectName("TitleLabel"); layout.addWidget(title); self.table = QTableWidget(); layout.addWidget(self.table)
    def refresh(self):
        rows = BackupService.list_logs(self.main.current_work_id)
        set_table(self.table, rows, ["ID", "操作", "说明", "范围", "备份路径", "时间"], lambda r: [r["id"], r["operation_type"], r["description"], r["related_range"], r["backup_path"], r["created_at"]])
