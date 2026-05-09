"""IgboAPI loader: download raw JSON, transform with sampling, load CSV."""
import csv as _csv
import json
import random
from pathlib import Path

import pandas as pd

from config import CAPS, RNG_SEED, SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["igbo_api"]


def transform_entry(raw: dict) -> tuple[str, str, int, dict]:
    """Map one raw IgboAPI entry to (headword, pos, dialect_id, jsonb)."""
    dialects = raw.get("dialects") or []
    if "Ehugbo" in dialects:
        dialect_id = 6
    elif "Enuani" in dialects:
        dialect_id = 7
    else:
        dialect_id = 5

    headword = raw["word"]
    pos = raw.get("wordClass") or "unknown"
    jsonb = {
        "source": SOURCE_TAG,
        "definitions": raw.get("definitions") or [],
        "examples": raw.get("examples") or [],
        "dialect_variants": dialects,
    }
    return headword, pos, dialect_id, jsonb


def transform(raw_dir: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read raw_dir/igbo_api.json, sample with RNG_SEED, write clean CSV.

    cap defaults to CAPS["igbo_api"]["total"]. Minority dialects (Ehugbo,
    Enuani) are kept entirely; Central is sampled to fill the remainder.
    Dedup is by (headword, dialect_id).
    """
    raw_dir = Path(raw_dir)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if cap is None:
        cap = CAPS["igbo_api"]["total"]

    raw_entries = json.loads((raw_dir / "igbo_api.json").read_text(encoding="utf-8"))
    transformed = [transform_entry(e) for e in raw_entries]

    seen: set[tuple[str, int]] = set()
    deduped: list[tuple] = []
    for hw, pos, did, jsonb in transformed:
        key = (hw, did)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((hw, pos, did, jsonb))

    minority = [t for t in deduped if t[2] in (6, 7)]
    central = [t for t in deduped if t[2] == 5]

    rng = random.Random(RNG_SEED)
    central_quota = max(0, cap - len(minority))
    if central_quota >= len(central):
        sampled_central = central
    else:
        sampled_central = rng.sample(central, central_quota)

    final = minority + sampled_central
    df = pd.DataFrame(
        [(hw, pos, did, json.dumps(jsonb, ensure_ascii=False)) for hw, pos, did, jsonb in final],
        columns=["headword", "pos", "dialect_id", "jsonb_data"],
    )
    out = clean_dir / "igbo_api_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    return out
