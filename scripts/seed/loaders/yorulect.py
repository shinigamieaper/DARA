"""YorùLect loader: scrape Drive link, download, transform, load."""
import csv as _csv
import json
import random
import re
from pathlib import Path

import gdown
import pandas as pd
import requests

import db
from config import CAPS, DIALECT_MAP, RNG_SEED, SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["yorulect"]

_README_URL = "https://raw.githubusercontent.com/orevaahia/yorulect/main/README.md"
_DRIVE_PATTERN = re.compile(r"https://drive\.google\.com/drive/folders/[A-Za-z0-9_-]+")
_DIALECT_FOLDERS = {"standard": 1, "ife": 2, "ilaje": 3, "ijebu": 4}


def extract_drive_url(readme_text: str) -> str:
    """Find the first Google Drive folder URL in the README text."""
    m = _DRIVE_PATTERN.search(readme_text)
    if not m:
        raise ValueError("No Google Drive folder link found in README")
    return m.group(0)


def download(raw_root: Path) -> Path:
    """Resolve the Drive URL and pull the folder via gdown.

    Tries the GitHub README first; if that fails, looks for
    raw_root/yorulect/DRIVE_LINK.txt as a manual override.
    Output goes into raw_root/yorulect/.
    """
    raw_root = Path(raw_root)
    out_dir = raw_root / "yorulect"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(_README_URL, timeout=30)
        resp.raise_for_status()
        url = extract_drive_url(resp.text)
        print(f"[yorulect] resolved Drive URL from README: {url}")
    except Exception as e:
        link_file = out_dir / "DRIVE_LINK.txt"
        if link_file.exists():
            url = link_file.read_text(encoding="utf-8").strip()
            print(f"[yorulect] README fetch failed ({e}); using {link_file}: {url}")
        else:
            print(f"[yorulect] FAIL: README unreachable and no {link_file}", flush=True)
            raise

    gdown.download_folder(url, output=str(out_dir), quiet=False)
    return out_dir


def transform(raw_root: Path, clean_dir: Path, per_dialect_cap: int | None = None) -> Path:
    """Walk raw_root/yorulect/<dialect>/*.tsv, sample per dialect, write CSV."""
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if per_dialect_cap is None:
        per_dialect_cap = CAPS["yorulect"]["per_dialect"]

    yl_root = raw_root / "yorulect"
    rng = random.Random(RNG_SEED)
    rows: list[dict] = []
    underflow: dict[str, tuple[int, int]] = {}

    for folder_name, dialect_id in _DIALECT_FOLDERS.items():
        folder = yl_root / folder_name
        if not folder.is_dir():
            print(f"[yorulect] FAIL: missing dialect folder {folder}")
            raise SystemExit(2)

        seen: set[str] = set()
        per_dialect: list[dict] = []
        for tsv_path in sorted(folder.glob("*.tsv")):
            df = pd.read_csv(tsv_path, sep="\t", dtype=str, encoding="utf-8",
                             keep_default_na=False, quoting=_csv.QUOTE_NONE)
            cols = {c.lower(): c for c in df.columns}
            if "yoruba" not in cols or "english" not in cols:
                print(f"[yorulect] FAIL: {tsv_path} columns={list(df.columns)}; "
                      f"need 'english' and 'yoruba'")
                raise SystemExit(2)

            domain = tsv_path.stem
            for _, r in df.iterrows():
                yo = (r[cols["yoruba"]] or "").strip()
                en = (r[cols["english"]] or "").strip()
                if not yo or yo in seen:
                    continue
                seen.add(yo)
                per_dialect.append({
                    "headword": yo,
                    "pos": "sentence",
                    "dialect_id": dialect_id,
                    "jsonb": {
                        "source": SOURCE_TAG,
                        "domain": domain,
                        "english_translation": en,
                    },
                })

        if len(per_dialect) <= per_dialect_cap:
            sampled = per_dialect
            if len(per_dialect) < per_dialect_cap:
                underflow[folder_name] = (len(per_dialect), per_dialect_cap)
                print(f"[yorulect] WARN: {folder_name} underflow: "
                      f"{len(per_dialect)} available, cap was {per_dialect_cap}")
        else:
            sampled = rng.sample(per_dialect, per_dialect_cap)
        rows.extend(sampled)

    df_out = pd.DataFrame([{
        "headword": r["headword"],
        "pos": r["pos"],
        "dialect_id": r["dialect_id"],
        "jsonb_data": json.dumps(r["jsonb"], ensure_ascii=False),
    } for r in rows])
    out = clean_dir / "yorulect_clean.csv"
    df_out.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[yorulect] wrote {len(df_out)} rows to {out}")
    if underflow:
        print(f"[yorulect] underflow detail: {underflow}")
    sidecar = clean_dir / "yorulect_underflow.json"
    sidecar.write_text(json.dumps(underflow, ensure_ascii=False), encoding="utf-8")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    sidecar = Path(csv_path).parent / "yorulect_underflow.json"
    if sidecar.exists():
        underflow_raw = json.loads(sidecar.read_text(encoding="utf-8"))
        # JSON loses tuples; restore (avail, target) shape:
        underflow = {k: tuple(v) for k, v in underflow_raw.items()}
    else:
        underflow = {}
    return db.LoadResult(
        dataset="yorulect",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
        underflow=underflow,
    )
