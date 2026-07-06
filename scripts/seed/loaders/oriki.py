"""Praise-poetry (oríkì / praise names / kirari) loader.

Ingests the project-owned praise dataset the generator app consumes live
via /api/praise: praise poems keyed by the name/subject being praised,
each with the full praise text, its meaning, a category, and keywords.
The source CSVs are committed under seed_data/ (they originated as manual
CSVs inside the Oríkì project and are being moved into this repository /
API). No network fetch happens.

All `seed_data/oriki_source*.csv` files are ingested, covering all three
languages. Each row becomes a praise_poetry entry: headword = the
name/subject (so consumers can look a praise poem up by name), with the
full text and metadata in jsonb. The row's `language` column maps to the
standard dialect for that language.
"""
import csv as _csv
import json
from pathlib import Path

import pandas as pd

import db
from config import SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["oriki"]

_SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data"
# Praise rows are assigned to each language's standard dialect.
_LANG_TO_DIALECT = {"yoruba": 1, "igbo": 5, "hausa": 8}
_ORIGIN = ("DARA praise dataset (project-owned), migrated from the Oríkì "
           "generator project's manual collection.")


def _source_files() -> list[Path]:
    return sorted(_SEED_DIR.glob("oriki_source*.csv"))


def download(raw_root: Path) -> Path:
    """No-op: praise source CSVs are committed under seed_data/."""
    files = _source_files()
    if not files:
        print("[oriki] WARN: no seed_data/oriki_source*.csv files found")
    else:
        print(f"[oriki] using {len(files)} committed source(s): "
              f"{', '.join(f.name for f in files)}")
    return _SEED_DIR


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read every committed praise CSV, map to praise_poetry entries, write clean CSV.

    dialect_id is derived from each row's `language` column (Yoruba->1,
    Igbo->5, Hausa->8). Deduplicates by praise text so an identical poem is
    not loaded twice.
    """
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    rows: list[tuple] = []
    for src in _source_files():
        with src.open(encoding="utf-8", newline="") as f:
            for r in _csv.DictReader(f):
                name = (r.get("name") or "").strip()
                praise = (r.get("praise_text") or "").strip()
                if not praise or praise in seen:
                    continue
                seen.add(praise)
                lang = (r.get("language") or "").strip().lower()
                dialect_id = _LANG_TO_DIALECT.get(lang, 1)
                kw = [k.strip() for k in (r.get("keywords") or "").split(";") if k.strip()]
                jsonb = {
                    "source": SOURCE_TAG,
                    "genre": "praise_poetry",
                    "language": lang,
                    "praise_text": praise,
                    "meaning": (r.get("meaning") or "").strip(),
                    "category": (r.get("category") or "").strip(),
                    "keywords": kw,
                    "gender": (r.get("gender") or "").strip(),
                    "origin": _ORIGIN,
                    "license": "CC BY-SA 4.0",
                    "dialect_assigned_default": True,
                }
                headword = name or praise.splitlines()[0][:120]
                rows.append((headword, "praise_poetry", dialect_id,
                             json.dumps(jsonb, ensure_ascii=False)))

    out = clean_dir / "oriki_clean.csv"
    pd.DataFrame(rows, columns=["headword", "pos", "dialect_id", "jsonb_data"]).to_csv(
        out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[oriki] wrote {len(rows)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="oriki",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
