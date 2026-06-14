from pathlib import Path

APP_NAME = "NovelMemoryAssistant_V0.3_beta"
BASE_DIR = Path.home() / ".novel_memory_assistant_v03_beta"
DB_PATH = BASE_DIR / "novel_memory_beta.sqlite3"
EXPORT_DIR = BASE_DIR / "exports"
BACKUP_DIR = BASE_DIR / "backups"

for p in (BASE_DIR, EXPORT_DIR, BACKUP_DIR):
    p.mkdir(parents=True, exist_ok=True)
