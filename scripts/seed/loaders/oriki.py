"""Oríkì (Yoruba praise poetry) loader.

Ingests the project-owned Oríkì dataset — Yoruba praise poems keyed by the
name/subject being praised, each with the full praise text, its meaning,
a category, and keywords. This is the praise-poetry counterpart the Oríkì
generator app consumes live via /api/praise; the source CSV is committed
under seed_data/ (it originated as a manual CSV inside the Oríkì project
and is being moved into this repository/API). No network fetch happens.

Every row becomes a praise_poetry entry: headword = the name/subject (so
consumers can look an oríkì up by name), with the full oríkì text and its
metadata in jsonb. All rows are Yoruba (dialect_id 1, Standard Yoruba).
"""
import csv as _csv
import json
from pathlib import Path

import pandas as pd

import db
from config import SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["oriki"]

_SRC = Path(__file__).resolve().parent.parent / "seed_data" / "oriki_source.csv"
_DIALECT_ID = 1  # Standard Yoruba
_ORIGIN = ("DARA Oríkì dataset (project-owned), migrated from the Oríkì "
           "generator project's manual collection.")


def download(raw_root: Path) -> Path:
    """No-op: the oríkì source CSV is committed under seed_data/."""
    if not _SRC.exists():
        print(f"[oriki] WARN: missing {_SRC}")
    else:
        print(f"[oriki] using committed source {_SRC.name}")
    return _SRC


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read the committed oríkì CSV, map to praise_poetry entries, write clean CSV.

    Deduplicates by the praise text so an identical oríkì is not loaded twice.
    """
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    seen: set[str] = set()
    rows: list[tuple] = []
    with _SRC.open(encoding="utf-8", newline="") as f:
        for r in _csv.DictReader(f):
            name = (r.get("name") or "").strip()
            praise = (r.get("praise_text") or "").strip()
            if not praise or praise in seen:
                continue
            seen.add(praise)
            kw = [k.strip() for k in (r.get("keywords") or "").split(";") if k.strip()]
            jsonb = {
                "source": SOURCE_TAG,
                "genre": "praise_poetry",
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
            rows.append((headword, "praise_poetry", _DIALECT_ID,
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
