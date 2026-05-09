"""NaijaSenti loader: hau / ibo / yor configs, pcm skipped."""
import csv as _csv
import json
import random
from pathlib import Path

import pandas as pd
from datasets import load_dataset as hf_load_dataset

import db
from config import CAPS, RNG_SEED, SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["naijasenti"]
_LANG_TO_DIALECT = {"yor": 1, "ibo": 5, "hau": 8}
_LANGS = ("yor", "ibo", "hau")


def transform_entry(raw: dict, lang: str) -> tuple[str, str, int, dict]:
    return (
        raw["tweet"],
        "sentence",
        _LANG_TO_DIALECT[lang],
        {
            "source": SOURCE_TAG,
            "type": "tweet",
            "sentiment": raw["sentiment"],
            "split": raw["split"],
            "dialect_assigned_default": True,
        },
    )


def download(raw_root: Path) -> Path:
    raw_dir = Path(raw_root) / "naijasenti"
    raw_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, list[dict]] = {}
    for lang in _LANGS:
        ds = hf_load_dataset("HausaNLP/NaijaSenti-Twitter", lang)
        rows: list[dict] = []
        for split in ds.keys():
            split_ds = ds[split]
            label_feature = split_ds.features["label"]
            for r in split_ds:
                rows.append({
                    "tweet": r["tweet"],
                    "sentiment": label_feature.int2str(r["label"]),
                    "split": split,
                })
        payload[lang] = rows
        print(f"[naijasenti] {lang}: {len(rows)} raw rows pooled across splits")
    out = raw_dir / "naijasenti.json"
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out


def transform(raw_root: Path, clean_dir: Path,
              quotas: dict[str, int] | None = None) -> Path:
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if quotas is None:
        quotas = CAPS["naijasenti"]

    payload = json.loads(
        (raw_root / "naijasenti" / "naijasenti.json").read_text(encoding="utf-8")
    )
    rng = random.Random(RNG_SEED)
    out_rows: list[tuple] = []
    for lang in _LANGS:
        seen: set[str] = set()
        pool: list[tuple] = []
        for r in payload.get(lang, []):
            hw, pos, did, jsonb = transform_entry(r, lang)
            if not hw or hw in seen:
                continue
            seen.add(hw)
            pool.append((hw, pos, did, jsonb))
        cap = quotas[lang]
        sampled = pool if len(pool) <= cap else rng.sample(pool, cap)
        out_rows.extend(sampled)

    df = pd.DataFrame(
        [(hw, pos, did, json.dumps(j, ensure_ascii=False)) for hw, pos, did, j in out_rows],
        columns=["headword", "pos", "dialect_id", "jsonb_data"],
    )
    out = clean_dir / "naijasenti_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[naijasenti] wrote {len(df)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> int:
    return db.load_csv(csv_path, conn)
