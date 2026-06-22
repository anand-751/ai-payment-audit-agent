import os
from pathlib import Path


def ensure_dirs():
    Path("./backend/data/uploads").mkdir(parents=True, exist_ok=True)
    Path("./backend/data/exports").mkdir(parents=True, exist_ok=True)
