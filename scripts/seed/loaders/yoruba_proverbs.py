"""Yoruba proverbs loader.

Combines two openly licensed sources of Yoruba proverbs, deduped by the
Yoruba headword text (mxronga rows are added first, MENYO-20k adds only
proverbs not already seen):

- mxronga/yoruba-proverbs-parallel-corpora (Apache-2.0, HuggingFace): 568
  Yoruba/English proverb pairs, JSONL ({"yoruba": ..., "english": ...}).
- MENYO-20k verified/yoruba_proverbs.csv (CC BY-NC 4.0, Adelani et al.
  2021): ~2700 rows of Yoruba/English proverb pairs, columns
  ["", "English", "Yoruba"].

All rows are assigned dialect_id 1 (Standard Yoruba) since neither source
indicates a dialect.
"""
import csv as _csv
import json
import random
from pathlib import Path

import pandas as pd
import requests

import db
from config import CAPS, RNG_SEED, SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["yoruba_proverbs"]

_MXRONGA_URL = ("https://huggingface.co/datasets/mxronga/"
                 "yoruba-proverbs-parallel-corpora/resolve/main/train.jsonl")
_MENYO_URL = ("https://raw.githubusercontent.com/uds-lsv/menyo-20k_MT/"
              "master/verified/yoruba_proverbs.csv")
_DIALECT_ID = 1

_MXRONGA_ORIGIN = "mxronga/yoruba-proverbs-parallel-corpora (Apache-2.0)"
_MENYO_ORIGIN = "MENYO-20k (Adelani et al. 2021)"


def download(raw_root: Path) -> Path:
    """Fetch both upstream sources and write raw/yoruba_proverbs/{mxronga.jsonl,menyo.csv}."""
    raw_root = Path(raw_root)
    raw_dir = raw_root / "yoruba_proverbs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    mxronga_resp = requests.get(_MXRONGA_URL, timeout=120)
    mxronga_resp.raise_for_status()
    mxronga_out = raw_dir / "mxronga.jsonl"
    mxronga_out.write_text(mxronga_resp.text, encoding="utf-8")
    mxronga_count = sum(1 for line in mxronga_resp.text.splitlines() if line.strip())
    print(f"[yoruba_proverbs] wrote {mxronga_count} mxronga rows to {mxronga_out}")

    menyo_resp = requests.get(_MENYO_URL, timeout=120)
    menyo_resp.raise_for_status()
    menyo_out = raw_dir / "menyo.csv"
    menyo_out.write_text(menyo_resp.text, encoding="utf-8")
    menyo_count = max(len(menyo_resp.text.splitlines()) - 1, 0)
    print(f"[yoruba_proverbs] wrote {menyo_count} menyo rows to {menyo_out}")

    return raw_dir


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read both raw sources, dedup by Yoruba text, sample up to cap, write clean CSV."""
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if cap is None:
        cap = CAPS["yoruba_proverbs"]["total"]

    raw_dir = raw_root / "yoruba_proverbs"
    seen: set[str] = set()
    pool: list[tuple] = []

    mxronga_path = raw_dir / "mxronga.jsonl"
    with open(mxronga_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            yo = (rec.get("yoruba") or "").strip()
            en = (rec.get("english") or "").strip()
            if not yo or yo in seen:
                continue
            seen.add(yo)
            jsonb = {
                "source": SOURCE_TAG,
                "genre": "proverb",
                "english_translation": en,
                "origin": _MXRONGA_ORIGIN,
                "license": "Apache-2.0",
                "dialect_assigned_default": True,
            }
            pool.append((yo, "proverb", _DIALECT_ID, jsonb))

    menyo_path = raw_dir / "menyo.csv"
    menyo_df = pd.read_csv(menyo_path, dtype=str, keep_default_na=False, encoding="utf-8")
    for _, r in menyo_df.iterrows():
        yo = (r["Yoruba"] or "").strip()
        en = (r["English"] or "").strip()
        if not yo or yo in seen:
            continue
        seen.add(yo)
        jsonb = {
            "source": SOURCE_TAG,
            "genre": "proverb",
            "english_translation": en,
            "origin": _MENYO_ORIGIN,
            "license": "CC BY-NC 4.0",
            "dialect_assigned_default": True,
        }
        pool.append((yo, "proverb", _DIALECT_ID, jsonb))

    if cap is None or len(pool) <= cap:
        sampled = pool
    else:
        rng = random.Random(RNG_SEED)
        sampled = rng.sample(pool, cap)

    df = pd.DataFrame(
        [(hw, pos, did, json.dumps(j, ensure_ascii=False)) for hw, pos, did, j in sampled],
        columns=["headword", "pos", "dialect_id", "jsonb_data"],
    )
    out = clean_dir / "yoruba_proverbs_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[yoruba_proverbs] wrote {len(df)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="yoruba_proverbs",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
