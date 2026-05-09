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
