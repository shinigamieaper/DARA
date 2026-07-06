"""Hausa dictionary loader: kaikki.org Wiktextract of Hausa Wiktionary.

CC BY-SA. Assigns every word to Standard Hausa (dialect_id=8). See
loaders/wiktionary.py for the shared JSONL parsing + grouping logic.
"""
import csv as _csv
import json
import random
from pathlib import Path

import pandas as pd
import requests

import db
from config import CAPS, RNG_SEED, SOURCE_TAGS
from loaders import wiktionary

SOURCE_TAG = SOURCE_TAGS["hausa_dict"]

_URL = "https://kaikki.org/dictionary/Hausa/kaikki.org-dictionary-Hausa.jsonl"

_DIALECT_ID = 8


def download(raw_root: Path) -> Path:
    """Fetch the Hausa kaikki JSONL and write raw_root/hausa_dict/hausa_dict.jsonl."""
    raw_root = Path(raw_root)
    raw_dir = raw_root / "hausa_dict"
    raw_dir.mkdir(parents=True, exist_ok=True)
    resp = requests.get(_URL, timeout=120)
    resp.raise_for_status()
    out = raw_dir / "hausa_dict.jsonl"
    out.write_text(resp.text, encoding="utf-8")
    n_lines = sum(1 for line in resp.text.splitlines() if line.strip())
    print(f"[hausa_dict] wrote {n_lines} raw lines to {out}")
    return out


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read raw JSONL, group by word, sample up to cap rows, write clean CSV."""
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if cap is None:
        cap = CAPS["hausa_dict"]["total"]

    text = (raw_root / "hausa_dict" / "hausa_dict.jsonl").read_text(encoding="utf-8")
    raw_entries = wiktionary.parse_jsonl(text)
    pool = wiktionary.build_rows(raw_entries, _DIALECT_ID, SOURCE_TAG)

    if cap is None or len(pool) <= cap:
        sampled = pool
    else:
        rng = random.Random(RNG_SEED)
        sampled = rng.sample(pool, cap)

    df = pd.DataFrame(
        [(hw, pos, did, json.dumps(j, ensure_ascii=False)) for hw, pos, did, j in sampled],
        columns=["headword", "pos", "dialect_id", "jsonb_data"],
    )
    out = clean_dir / "hausa_dict_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[hausa_dict] wrote {len(df)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="hausa_dict",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
