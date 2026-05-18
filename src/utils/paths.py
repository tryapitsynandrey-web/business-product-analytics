from pathlib import Path
from collections.abc import Iterable

# Get the absolute path to the project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Define directories
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
SYNTHETIC_DATA_DIR = DATA_DIR / "synthetic"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXPORTS_DATA_DIR = DATA_DIR / "exports"
LOCAL_DATA_DIR = DATA_DIR / "local"
REPORTS_DIR = PROJECT_ROOT / "reports"

# SQLite DB path (default fallback if config is not available)
SQLITE_DB_PATH = LOCAL_DATA_DIR / "productpulse.db"

PROJECT_DIRECTORIES = [
    CONFIG_DIR,
    DATA_DIR,
    SYNTHETIC_DATA_DIR,
    PROCESSED_DATA_DIR,
    EXPORTS_DATA_DIR,
    LOCAL_DATA_DIR,
    REPORTS_DIR,
]


def ensure_directories(extra_directories: Iterable[Path] | None = None) -> None:
    """Create project runtime directories explicitly instead of at import time."""
    directories = list(PROJECT_DIRECTORIES)
    if extra_directories is not None:
        directories.extend(extra_directories)
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
