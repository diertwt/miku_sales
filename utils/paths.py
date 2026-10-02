# пути для работы из exe


import sys
from pathlib import Path


def app_dir() -> Path:
    """Папка рядом с exe (или с main.py при разработке)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


DATA_DIR = app_dir() / "data"
RECEIPTS_DIR = DATA_DIR / "receipts"

DATA_DIR.mkdir(exist_ok=True)
RECEIPTS_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "sales.db"