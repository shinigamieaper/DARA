"""Pytest setup: makes scripts/seed/ importable as bare modules."""
import sys
from pathlib import Path

# scripts/seed/ on sys.path so tests do `import config`, `import db`.
_SEED_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_SEED_DIR))
