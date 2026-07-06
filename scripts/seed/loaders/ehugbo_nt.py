"""Ehugbo New Testament parallel-corpus loader.

1,021 Ehugbo-English sentence pairs from the New Testament, released
Apache-2.0 by Eze-Mbeyu et al., "E.hugbo Ka! Advancing Machine Translation
for the Low-Resource E.hugbo Language" (HuggingFace: Ukachi/NLP-Ehugbo).
The HuggingFace files are gated behind a login, so the source CSV is
committed under seed_data/ for reproducibility. Every sentence is Ehugbo
(Afikpo Igbo), dialect_id 6. No network fetch happens here.
"""
import csv as _csv
import json
from pathlib import Path

import pandas as pd

import db
from config import SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["ehugbo_nt"]

_SRC = Path(__file__).resolve().parent.parent / "seed_data" / "ehugbo_nt_source.csv"
_DIALECT_ID = 6
_CITE = ("Eze-Mbeyu, U. A., Eze-Mbeyu, U. C., & Anjuwon, O. (2025). "
         "'E.hugbo Ka! Advancing Machine Translation for the Low-Resource "
         "E.hugbo Language through Parallel Corpus Development.' "
         "PMLR 302 (Deep Learning Indaba 2025). "
         "Dataset: HuggingFace Ukachi/NLP-Ehugbo (Apache-2.0).")


def download(raw_root: Path) -> Path:
    """No-op: the source CSV is committed under seed_data/ (HF files are gated)."""
    if not _SRC.exists():
        print(f"[ehugbo_nt] WARN: missing {_SRC}")
    else:
        print(f"[ehugbo_nt] using committed source {_SRC.name}")
    return _SRC


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Read the committed En/Ib CSV, dedup by Ehugbo sentence, write clean CSV."""
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(_SRC, dtype=str, keep_default_na=False, encoding="utf-8")
    en_col = next(c for c in df.columns if c.strip().lower() == "en")
    ib_col = next(c for c in df.columns if c.strip().lower() == "ib")

    seen: set[str] = set()
    rows: list[tuple] = []
    for _, r in df.iterrows():
        ehugbo = (r[ib_col] or "").strip()
        english = (r[en_col] or "").strip()
        if not ehugbo or ehugbo in seen:
            continue
        seen.add(ehugbo)
        jsonb = {
            "source": SOURCE_TAG,
            "english_translation": english,
            "type": "bible_verse",
            "license": "Apache-2.0",
            "origin": _CITE,
            "dialect_assigned_default": False,
        }
        rows.append((ehugbo, "sentence", _DIALECT_ID,
                     json.dumps(jsonb, ensure_ascii=False)))

    out = clean_dir / "ehugbo_nt_clean.csv"
    pd.DataFrame(rows, columns=["headword", "pos", "dialect_id", "jsonb_data"]).to_csv(
        out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[ehugbo_nt] wrote {len(rows)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="ehugbo_nt",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
