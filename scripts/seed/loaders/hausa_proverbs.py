"""Hausa Proverbs loader.

Public-domain historical source: G. Merrick, "Hausa Proverbs" (1905),
transcribed OCR text hosted at archive.org
(hausaproverbs00merrrich_djvu.txt). The proverb section of that OCR text
is a repeating sequence of numbered blocks: a Hausa transliteration line,
a blank line, an English translation (one or more lines), and an
optional explanatory note. Parsing stops before the grammar appendix
("HAUSA SONGS" / "SYSTEM OF NUMERATION" / "NUMBER FORMATION"), which is
not part of the proverb collection.

Because this is 1905-vintage scanned OCR of an old transliteration
convention, the Hausa text is stored exactly as transcribed (imperfect
orthography and all) rather than normalized.
"""
import csv as _csv
import json
import random
import re
from pathlib import Path

import pandas as pd
import requests

import db
from config import CAPS, RNG_SEED, SOURCE_TAGS

SOURCE_TAG = SOURCE_TAGS["hausa_proverbs"]

_SOURCE_URL = ("https://archive.org/download/hausaproverbs00merrrich/"
               "hausaproverbs00merrrich_djvu.txt")
_DIALECT_ID = 8
_ORIGIN = ("Merrick, G. (1905). Hausa Proverbs. Public domain "
           "(archive.org/details/hausaproverbs00merrrich).")

_PROVERB_START_RE = re.compile(r"^\s*(\d+)\s+(\S.*)$")
_STOP_MARKERS = ("HAUSA SONGS", "SYSTEM OF NUMERATION", "NUMBER FORMATION")


def _is_header_line(s: str) -> bool:
    """Running page-header lines mentioning 'proverb(s)'. The 'Hausa' half
    of the header is frequently OCR-garbled ("Haiisa", "Hm^sa", ...) but
    the word 'proverb(s)' itself reliably survives, so we key off that.
    Headers are short running titles (e.g. "HAUSA PROVERBS", "72 Haiisa
    Proverbs"); a longer sentence that happens to mention "proverb" (e.g.
    an explanatory note) is left alone by requiring a short word count.
    """
    if not re.search(r"proverbs?", s, re.IGNORECASE):
        return False
    return len(s.split()) <= 4


def _is_page_number_line(s: str) -> bool:
    return bool(re.fullmatch(r"\d+", s))


def _is_stop_line(s: str) -> bool:
    upper = s.upper()
    return any(marker in upper for marker in _STOP_MARKERS)


def _parse_proverbs(text: str) -> list[dict]:
    """Parse the OCR text into [{number, hausa, english, note}, ...].

    Conservative: a block is only emitted when it has a numeric start, a
    Hausa line, AND a non-empty English translation. Page headers and bare
    page numbers are skipped wherever they appear. Parsing stops entirely
    at the grammar-appendix section headers.
    """
    lines = text.splitlines()
    n = len(lines)
    proverbs: list[dict] = []
    i = 0

    while i < n:
        stripped = lines[i].strip()
        if _is_stop_line(stripped):
            break

        m = _PROVERB_START_RE.match(lines[i])
        if not m or _is_header_line(stripped):
            i += 1
            continue

        number = int(m.group(1))
        hausa = re.sub(r"\s+", " ", m.group(2)).strip().rstrip(".").strip()
        i += 1

        # blank/noise lines before the English translation block
        while i < n and not lines[i].strip():
            i += 1

        english_lines: list[str] = []
        while i < n:
            s = lines[i].strip()
            if not s:
                break
            if _is_stop_line(s) or (_PROVERB_START_RE.match(lines[i]) and not _is_header_line(s)):
                break
            if _is_header_line(s) or _is_page_number_line(s):
                i += 1
                continue
            english_lines.append(s)
            i += 1
        english = " ".join(english_lines).strip()

        note_lines: list[str] = []
        while i < n:
            s = lines[i].strip()
            if _is_stop_line(s):
                break
            if _PROVERB_START_RE.match(lines[i]) and not _is_header_line(s):
                break
            if s and not _is_header_line(s) and not _is_page_number_line(s):
                note_lines.append(s)
            i += 1
        note = " ".join(note_lines).strip()

        if number and hausa and english:
            proverbs.append({
                "number": number,
                "hausa": hausa,
                "english": english,
                "note": note,
            })

    return proverbs


def download(raw_root: Path) -> Path:
    """Fetch the OCR'd public-domain text and write raw/hausa_proverbs/merrick.txt."""
    raw_root = Path(raw_root)
    raw_dir = raw_root / "hausa_proverbs"
    raw_dir.mkdir(parents=True, exist_ok=True)
    resp = requests.get(_SOURCE_URL, timeout=120)
    resp.raise_for_status()
    out = raw_dir / "merrick.txt"
    out.write_text(resp.text, encoding="utf-8")
    print(f"[hausa_proverbs] wrote {len(resp.text.splitlines())} lines to {out}")
    return out


def transform(raw_root: Path, clean_dir: Path, cap: int | None = None) -> Path:
    """Parse the OCR text, build rows, sample up to cap, write clean CSV."""
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if cap is None:
        cap = CAPS["hausa_proverbs"]["total"]

    text = (raw_root / "hausa_proverbs" / "merrick.txt").read_text(encoding="utf-8")
    proverbs = _parse_proverbs(text)

    pool: list[tuple] = []
    for p in proverbs:
        jsonb = {
            "source": SOURCE_TAG,
            "genre": "proverb",
            "english_translation": p["english"],
            "note": p["note"],
            "proverb_number": p["number"],
            "origin": _ORIGIN,
            "license": "Public Domain",
            "dialect_assigned_default": True,
        }
        pool.append((p["hausa"], "proverb", _DIALECT_ID, jsonb))

    if cap is None or len(pool) <= cap:
        sampled = pool
    else:
        rng = random.Random(RNG_SEED)
        sampled = rng.sample(pool, cap)

    df = pd.DataFrame(
        [(hw, pos, did, json.dumps(j, ensure_ascii=False)) for hw, pos, did, j in sampled],
        columns=["headword", "pos", "dialect_id", "jsonb_data"],
    )
    out = clean_dir / "hausa_proverbs_clean.csv"
    df.to_csv(out, index=False, encoding="utf-8", quoting=_csv.QUOTE_ALL)
    print(f"[hausa_proverbs] wrote {len(df)} rows to {out}")
    return out


def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="hausa_proverbs",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
