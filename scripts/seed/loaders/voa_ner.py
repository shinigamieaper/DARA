"""VOA NER (Hausa) loader."""
import csv as _csv
import json
import random
from pathlib import Path

import pandas as pd
from datasets import load_dataset as hf_load_dataset

import db
from config import CAPS, RNG_SEED, SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["voa_ner"]


def transform_entry(raw: dict) -> tuple[str, str, int, dict]:
    """Map one raw VOA NER row to (headword, pos, dialect_id, jsonb).

    Joins tokens with spaces to form the sentence headword.
    ner_tags are intentionally dropped from the output.
    All rows tagged with dialect_id=8 (Standard Hausa).
    """
    headword = " ".join(raw["tokens"])
    jsonb = {
        "source": SOURCE_TAG,
        "split": raw["split"],
        "dialect_assigned_default": True,
    }
    return headword, "sentence", 8, jsonb


def download(raw_root: Path) -> Path:
    """Download all three HF splits and write raw_root/voa_ner/voa_ner.json.

    Each row gets a 'split' key added before writing so we can track provenance.
    """
    raw_root = Path(raw_root)
    raw_dir = raw_root / "voa_ner"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pooled = []
    for split in ("train", "validation", "test"):
        ds = hf_load_dataset("UdS-LSV/hausa_voa_ner", split=split)
        for row in ds.to_list():
            pooled.append({
                "tokens": list(row.get("tokens") or []),
                "ner_tags": list(row.get("ner_tags") or []),
                "split": split,
            })
    out = raw_dir / "voa_ner.json"
    out.write_text(json.dumps(pooled, ensure_ascii=False), encoding="utf-8")
    print(f"[voa_ner] wrote {len(pooled)} raw entries to {out}")
    return out


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read raw JSON, dedup by sentence, sample up to cap rows, write clean CSV."""
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if cap is None:
        cap = CAPS["voa_ner"]["total"]

    raw_entries = json.loads(
        (raw_root / "voa_ner" / "voa_ner.json").read_text(encoding="utf-8")
    )
    seen: set[str] = set()
    pool: list[tuple] = []
    for e in raw_entries:
        hw, pos, did, jsonb = transform_entry(e)
        if not hw or hw in seen:
            continue
        seen.add(hw)
        pool.append((hw, pos, did, jsonb))

    rng = random.Random(RNG_SEED)
    sampled = pool if len(pool) <= cap else rng.sample(pool, cap)
    df = pd.DataFrame(
        [(hw, pos, did, json.dumps(j, ensure_ascii=False)) for hw, pos, did, j in sampled],
        columns=["headword", "pos", "dialect_id", "jsonb_data"],
    )
    out = clean_dir / "voa_ner_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[voa_ner] wrote {len(df)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="voa_ner",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
