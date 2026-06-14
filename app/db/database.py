import sqlite3
from app.core.paths import DB_PATH, BASE_DIR
from app.db.schema import SCHEMA_SQL


def connect():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = connect()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()
