"""Dialect seed loader: hand-curated, cited wordlists for the modelled
dialects that have no open, machine-readable source.

Unlike the other loaders, this one does not fetch anything. The seed rows
are hand-transcribed from real, openly accessible, cited references and
committed under `scripts/seed/seed_data/dialect_seed_<dialect>.csv`, each
already in the pipeline's four-column shape with the source citation in
its `jsonb_data`. `download()` is therefore a no-op, and `transform()`
just concatenates every committed seed file into the clean CSV. Keeping
the curated inputs in version control makes each word's provenance
auditable in git.

As of 2026-07-06 only Sokoto Hausa (dialect_id 9) has a verifiable open
source. Ehugbo (6) and Enuani (7) had no openly accessible dialect-
labelled wordlist and remain documented gaps; when a citable source is
found, dropping a new `dialect_seed_*.csv` into seed_data/ is all that is
needed to include it.
"""
import csv as _csv
from pathlib import Path

import pandas as pd

import db
from config import SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["dialect_seeds"]

_SEED_DIR = Path(__file__).resolve().parent.parent / "seed_data"
_COLUMNS = ["headword", "pos", "dialect_id", "jsonb_data"]


def _seed_files() -> list[Path]:
    return sorted(_SEED_DIR.glob("dialect_seed_*.csv"))


def download(raw_root: Path) -> Path:
    """No-op: seed CSVs are hand-curated and committed under seed_data/."""
    files = _seed_files()
    if not files:
        print("[dialect_seeds] WARN: no seed_data/dialect_seed_*.csv files found")
    else:
        print(f"[dialect_seeds] using {len(files)} committed seed file(s): "
              f"{', '.join(f.name for f in files)}")
    return _SEED_DIR


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Concatenate every committed dialect_seed_*.csv into the clean CSV."""
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)

    frames = [
        pd.read_csv(f, dtype=str, encoding="utf-8", keep_default_na=False)
        for f in _seed_files()
    ]
    if frames:
        df = pd.concat(frames, ignore_index=True)[_COLUMNS]
    else:
        df = pd.DataFrame(columns=_COLUMNS)

    out = clean_dir / "dialect_seeds_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[dialect_seeds] wrote {len(df)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="dialect_seeds",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
