SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ip_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    ip_type TEXT,
    description TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    work_type TEXT,
    platform TEXT,
    genre TEXT,
    status TEXT,
    current_volume TEXT,
    current_chapter INTEGER DEFAULT 0,
    current_effective_version_id INTEGER,
    next_action TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS controls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    version_label TEXT,
    title TEXT,
    content TEXT NOT NULL,
    is_current INTEGER DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS manuscript_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    chapter_start INTEGER,
    chapter_end INTEGER,
    version_label TEXT,
    title TEXT,
    manuscript_type TEXT,
    status TEXT,
    is_current_effective INTEGER DEFAULT 0,
    replaces TEXT,
    content TEXT,
    summary TEXT,
    word_count INTEGER,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS stage_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    version_id INTEGER,
    chapter_start INTEGER,
    chapter_end INTEGER,
    title TEXT,
    content TEXT,
    status TEXT DEFAULT 'ACTIVE',
    risk_level TEXT DEFAULT 'NONE',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS writing_packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    target_start INTEGER,
    target_end INTEGER,
    base_version_id INTEGER,
    title TEXT,
    content TEXT,
    status TEXT DEFAULT 'ACTIVE',
    expired_reason TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS diff_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    old_version_ids TEXT,
    new_version_id INTEGER,
    title TEXT,
    summary TEXT,
    markdown_report TEXT,
    html_report TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS outline_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    rule_type TEXT,
    title TEXT,
    content TEXT,
    priority TEXT DEFAULT 'P1',
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS character_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    name TEXT,
    role TEXT,
    current_state TEXT,
    must_keep TEXT,
    forbidden_drift TEXT,
    knowledge_state TEXT,
    last_update_chapter INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ACTIVE',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS clue_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    name TEXT,
    first_chapter INTEGER DEFAULT 0,
    last_progress_chapter INTEGER DEFAULT 0,
    expected_resolve_chapter INTEGER DEFAULT 0,
    related_people TEXT,
    related_objects TEXT,
    current_status TEXT DEFAULT '推进中',
    risk_level TEXT DEFAULT '正常',
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS review_gates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    chapter_start INTEGER,
    chapter_end INTEGER,
    gate_type TEXT,
    status TEXT DEFAULT 'PENDING',
    report TEXT,
    risk_level TEXT DEFAULT 'NONE',
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS cover_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_id INTEGER,
    work_id INTEGER,
    title TEXT,
    file_path TEXT,
    platform TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    status TEXT,
    prompt TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS submission_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    platform TEXT,
    submit_date TEXT,
    status TEXT,
    data_snapshot TEXT,
    screenshot_path TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS version_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_id INTEGER,
    work_id INTEGER,
    version_id INTEGER,
    operation_type TEXT,
    description TEXT,
    related_range TEXT,
    backup_path TEXT,
    created_at TEXT
);
"""
