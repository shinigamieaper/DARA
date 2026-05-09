# Data Seeding Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python pipeline that downloads four upstream linguistic datasets (IgboAPI, YorùLect, VOA NER, NaijaSenti), transforms them into deterministic CSVs, and loads them into the Railway Postgres `entries` and `metadata` tables across nine pre-seeded dialects.

**Architecture:** A `scripts/seed/` sub-project with a single CLI driver (`seed.py`) and per-dataset modules each exposing `download(raw_dir)`, `transform(raw_dir, clean_dir)`, and `load(csv_path, conn)`. Shared modules cover config (`config.py`), DB access (`db.py`), preflight checks (`preflight.py`), and verification (`verify.py`). Sampling everywhere uses `random.Random(42)` for reproducibility.

**Tech Stack:** Python 3.10+, pandas, datasets (Hugging Face), psycopg2-binary, python-dotenv, gdown, requests, pytest.

**Spec:** [docs/superpowers/specs/2026-05-09-data-seeding-design.md](../specs/2026-05-09-data-seeding-design.md)

---

## File Structure

**Created:**

```
scripts/seed/
├── __init__.py
├── seed.py                          # CLI driver
├── config.py                        # Constants: DIALECT_MAP, RNG_SEED, CAPS, SOURCE_TAGS
├── db.py                            # connect(), entries_row_count, source_row_count, load_csv
├── preflight.py                     # client_encoding + dialect-map + row-count checks
├── verify.py                        # canonical breakdown query + exit code
├── README.md                        # runbook
├── datasets/
│   ├── __init__.py
│   ├── igbo_api.py
│   ├── yorulect.py
│   ├── voa_ner.py
│   └── naijasenti.py
└── tests/
    ├── __init__.py
    ├── conftest.py                  # adds scripts/seed/ to sys.path; shared fixtures
    ├── test_config.py
    ├── test_db.py
    ├── test_preflight.py
    ├── test_verify.py
    ├── test_seed_cli.py
    ├── datasets/
    │   ├── __init__.py
    │   ├── test_igbo_api.py
    │   ├── test_yorulect.py
    │   ├── test_voa_ner.py
    │   └── test_naijasenti.py
    └── fixtures/
        ├── igbo_api_sample.json
        ├── voa_ner_sample.json
        ├── naijasenti_sample.json
        └── yorulect/
            ├── standard/
            │   ├── farming.tsv
            │   └── cooking.tsv
            └── ife/
                └── farming.tsv

requirements.txt                     # at repo root
.gitignore                           # additions at repo root (raw/, .venv/, __pycache__/, *.pyc)
```

**Tests live next to code** under `scripts/seed/tests/`. `conftest.py` injects `scripts/seed/` into `sys.path` so tests `import config`, `import db`, etc. with no package prefix.

**Mocking strategy:** All network calls (`datasets.load_dataset`, `requests.get`, `gdown.download_folder`) and all psycopg2 connections are mocked in unit tests. The transformation core for each dataset is factored into a pure `transform_entry(raw: dict) -> tuple` function that's tested directly with hand-crafted dicts. Real fixture files are used only where file-walking logic is the actual subject (YorùLect cross-file dedup).

---

## Task 1: Bootstrap project structure

**Files:**
- Create: `requirements.txt`
- Create/modify: `.gitignore`
- Create: `scripts/seed/__init__.py`, `scripts/seed/datasets/__init__.py`, `scripts/seed/tests/__init__.py`, `scripts/seed/tests/datasets/__init__.py`
- Create: `scripts/seed/tests/conftest.py`
- Create: `raw/.gitkeep`, `clean/.gitkeep`

- [ ] **Step 1: Create `requirements.txt` at repo root**

```
pandas>=2.0
datasets>=2.14
psycopg2-binary>=2.9
python-dotenv>=1.0
gdown>=5.1
requests>=2.31
pytest>=7.4
```

- [ ] **Step 2: Create or extend `.gitignore` at repo root**

Append (or create with) these lines. Keep existing entries if the file already exists:

```
# Python
.venv/
__pycache__/
*.pyc

# Seed pipeline
raw/
```

`clean/` is intentionally NOT ignored — the deterministic seed makes the four CSVs a reproducible audit artifact.

- [ ] **Step 3: Create directory skeleton + empty package markers**

```
scripts/seed/__init__.py                  # empty file
scripts/seed/loaders/__init__.py          # empty file (note: NOT named "datasets" to avoid clashing with the HF library)
scripts/seed/tests/__init__.py            # empty file
scripts/seed/tests/loaders/__init__.py    # empty file
scripts/seed/tests/fixtures/yorulect/standard/.gitkeep   # empty file
scripts/seed/tests/fixtures/yorulect/ife/.gitkeep        # empty file
scripts/seed/tests/fixtures/yorulect/ilaje/.gitkeep      # empty file (no .tsv on purpose)
scripts/seed/tests/fixtures/yorulect/ijebu/.gitkeep      # empty file (no .tsv on purpose)
raw/.gitkeep                              # empty file (will be ignored, but keeps the dir intent visible)
clean/.gitkeep                            # empty file
```

- [ ] **Step 4: Create `scripts/seed/tests/conftest.py`**

```python
"""Pytest setup: makes scripts/seed/ importable as bare modules."""
import sys
from pathlib import Path

# scripts/seed/ on sys.path so tests do `import config`, `import db`.
_SEED_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(_SEED_DIR))
```

- [ ] **Step 5: Create venv and install**

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Verify pytest works:

```powershell
python -m pytest scripts/seed/tests/ -v
```

Expected: `no tests ran in 0.0Xs` (no tests yet, but pytest finds the directory and exits 0).

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt .gitignore scripts/seed/ raw/.gitkeep clean/.gitkeep
git commit -m "scaffold scripts/seed/ Python pipeline structure"
```

---

## Task 2: Implement `config.py` (constants)

**Files:**
- Create: `scripts/seed/config.py`
- Create: `scripts/seed/tests/test_config.py`

- [ ] **Step 1: Write the failing tests** in `scripts/seed/tests/test_config.py`

```python
import config


def test_dialect_map_matches_railway_seed():
    assert config.DIALECT_MAP == {
        1: ("Standard Yoruba", "Yoruba"),
        2: ("Ife", "Yoruba"),
        3: ("Ilaje", "Yoruba"),
        4: ("Ijebu", "Yoruba"),
        5: ("Central Igbo", "Igbo"),
        6: ("Ehugbo", "Igbo"),
        7: ("Enuani", "Igbo"),
        8: ("Standard Hausa", "Hausa"),
        9: ("Sokoto Hausa", "Hausa"),
    }


def test_rng_seed_is_42():
    assert config.RNG_SEED == 42


def test_caps_match_spec():
    assert config.CAPS == {
        "igbo_api":   {"total": 1000},
        "yorulect":   {"per_dialect": 250},
        "voa_ner":    {"total": 750},
        "naijasenti": {"yor": 500, "ibo": 500, "hau": 750},
    }


def test_source_tags_match_spec():
    assert config.SOURCE_TAGS == {
        "igbo_api":   "IgboAPI",
        "yorulect":   "YorùLect",
        "voa_ner":    "VOA Hausa",
        "naijasenti": "NaijaSenti",
    }


def test_dataset_order():
    assert config.DATASET_ORDER == ["igbo_api", "yorulect", "voa_ner", "naijasenti"]
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest scripts/seed/tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'` (or similar import error).

- [ ] **Step 3: Implement `scripts/seed/config.py`**

```python
"""Constants for the seed pipeline. Single source of truth for dialect IDs,
sampling seed, per-dataset caps, and source tags."""

DIALECT_MAP: dict[int, tuple[str, str]] = {
    1: ("Standard Yoruba", "Yoruba"),
    2: ("Ife", "Yoruba"),
    3: ("Ilaje", "Yoruba"),
    4: ("Ijebu", "Yoruba"),
    5: ("Central Igbo", "Igbo"),
    6: ("Ehugbo", "Igbo"),
    7: ("Enuani", "Igbo"),
    8: ("Standard Hausa", "Hausa"),
    9: ("Sokoto Hausa", "Hausa"),
}

RNG_SEED = 42

CAPS = {
    "igbo_api":   {"total": 1000},
    "yorulect":   {"per_dialect": 250},
    "voa_ner":    {"total": 750},
    "naijasenti": {"yor": 500, "ibo": 500, "hau": 750},
}

SOURCE_TAGS = {
    "igbo_api":   "IgboAPI",
    "yorulect":   "YorùLect",
    "voa_ner":    "VOA Hausa",
    "naijasenti": "NaijaSenti",
}

DATASET_ORDER = ["igbo_api", "yorulect", "voa_ner", "naijasenti"]
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/test_config.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/config.py scripts/seed/tests/test_config.py
git commit -m "add config module with dialect map, caps, and source tags"
```

---

## Task 3: Implement `db.py` connect + row-count helpers

**Files:**
- Create: `scripts/seed/db.py`
- Create: `scripts/seed/tests/test_db.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/test_db.py
from unittest.mock import MagicMock, patch
import pytest
import db


def test_connect_reads_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example/test")
    fake_conn = MagicMock()
    with patch("db.psycopg2.connect", return_value=fake_conn) as mock_connect:
        result = db.connect()
    mock_connect.assert_called_once_with("postgresql://example/test")
    assert result is fake_conn


def test_connect_raises_when_database_url_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        db.connect()


def test_entries_row_count_returns_int():
    fake_conn = MagicMock()
    fake_conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (42,)
    assert db.entries_row_count(fake_conn) == 42


def test_source_row_count_filters_by_source_tag():
    fake_conn = MagicMock()
    cur = fake_conn.cursor.return_value.__enter__.return_value
    cur.fetchone.return_value = (7,)

    result = db.source_row_count(fake_conn, "IgboAPI")

    assert result == 7
    sql, params = cur.execute.call_args[0]
    assert "metadata" in sql
    assert "jsonb_data" in sql
    assert params == ("IgboAPI",)
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
python -m pytest scripts/seed/tests/test_db.py -v
```

Expected: import error or `AttributeError: module 'db' has no attribute 'connect'`.

- [ ] **Step 3: Implement `scripts/seed/db.py`** (partial — connect + counts only)

```python
"""Database access layer for the seed pipeline."""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def connect():
    """Return a psycopg2 connection using DATABASE_URL from .env.

    Raises RuntimeError if DATABASE_URL is unset. autocommit stays False
    so callers can wrap work in `with conn:` for transactional safety.
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set in the environment")
    return psycopg2.connect(url)


def entries_row_count(conn) -> int:
    """Return the current row count of the entries table."""
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM entries")
        (count,) = cur.fetchone()
    return count


def source_row_count(conn, source_tag: str) -> int:
    """Return the count of metadata rows whose jsonb_data->>'source' equals tag."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM metadata WHERE jsonb_data->>'source' = %s",
            (source_tag,),
        )
        (count,) = cur.fetchone()
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/test_db.py -v
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/db.py scripts/seed/tests/test_db.py
git commit -m "add db.connect and row-count helpers"
```

---

## Task 4: Implement `db.load_csv` (paired-insert helper)

**Files:**
- Modify: `scripts/seed/db.py` (add `load_csv` and `truncate_all`)
- Modify: `scripts/seed/tests/test_db.py` (add tests)

- [ ] **Step 1: Add failing tests** to `scripts/seed/tests/test_db.py`

```python
import json
import csv
from pathlib import Path
import pandas as pd


def test_load_csv_executes_paired_insert(tmp_path):
    csv_path = tmp_path / "sample_clean.csv"
    pd.DataFrame([
        {"headword": "akwa", "pos": "noun", "dialect_id": "5",
         "jsonb_data": json.dumps({"source": "IgboAPI"})},
        {"headword": "ulo", "pos": "noun", "dialect_id": "6",
         "jsonb_data": json.dumps({"source": "IgboAPI"})},
    ]).to_csv(csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    cur = fake_conn.cursor.return_value.__enter__.return_value

    inserted = db.load_csv(csv_path, fake_conn)

    assert inserted == 2
    assert cur.execute.call_count == 2
    first_call = cur.execute.call_args_list[0]
    sql = first_call[0][0]
    params = first_call[0][1]
    assert "WITH new_entry AS" in sql
    assert "INSERT INTO entries" in sql
    assert "INSERT INTO metadata" in sql
    assert params == ("akwa", "noun", 5, '{"source": "IgboAPI"}')


def test_load_csv_drops_null_headword_rows(tmp_path):
    csv_path = tmp_path / "sample_clean.csv"
    pd.DataFrame([
        {"headword": "akwa", "pos": "noun", "dialect_id": "5",
         "jsonb_data": '{"source": "IgboAPI"}'},
        {"headword": "", "pos": "noun", "dialect_id": "5",
         "jsonb_data": '{"source": "IgboAPI"}'},
    ]).to_csv(csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    cur = fake_conn.cursor.return_value.__enter__.return_value

    inserted = db.load_csv(csv_path, fake_conn)

    assert inserted == 1
    assert cur.execute.call_count == 1


def test_truncate_all_runs_truncate_with_cascade():
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    cur = fake_conn.cursor.return_value.__enter__.return_value

    db.truncate_all(fake_conn)

    sql = cur.execute.call_args[0][0]
    assert "TRUNCATE" in sql
    assert "entries" in sql
    assert "metadata" in sql
    assert "RESTART IDENTITY" in sql
    assert "CASCADE" in sql
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest scripts/seed/tests/test_db.py -v`. Expected: 3 FAIL with `AttributeError: ... 'load_csv'` / `'truncate_all'`.

- [ ] **Step 3: Add `load_csv` and `truncate_all` to `scripts/seed/db.py`**

Append to the existing file:

```python
import pandas as pd

_PAIRED_INSERT_SQL = """
WITH new_entry AS (
  INSERT INTO entries (headword, pos, dialect_id)
  VALUES (%s, %s, %s)
  RETURNING entry_id
)
INSERT INTO metadata (entry_id, jsonb_data)
SELECT entry_id, %s::jsonb FROM new_entry
"""


def load_csv(csv_path, conn) -> int:
    """Insert every row of csv_path into entries+metadata in a single transaction.

    Uses a CTE so each metadata row pairs with the entry_id returned by its
    own INSERT. Drops rows with NULL/empty headword with a warning. The
    `with conn:` context commits on clean exit and rolls back on exception.
    Returns the number of rows actually inserted.
    """
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8")
    inserted = 0
    with conn:
        with conn.cursor() as cur:
            for row in df.itertuples(index=False):
                if not row.headword or not str(row.headword).strip():
                    print(f"[load_csv] dropping row with empty headword: {row}")
                    continue
                try:
                    cur.execute(
                        _PAIRED_INSERT_SQL,
                        (
                            row.headword,
                            row.pos,
                            int(row.dialect_id),
                            row.jsonb_data,
                        ),
                    )
                    inserted += 1
                except Exception as e:
                    print(f"[load_csv] insert failed at row {row}: {e}")
                    raise
    return inserted


def truncate_all(conn) -> None:
    """Truncate entries and metadata, resetting SERIAL counters."""
    with conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE entries, metadata RESTART IDENTITY CASCADE")
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/test_db.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/db.py scripts/seed/tests/test_db.py
git commit -m "add db.load_csv and db.truncate_all"
```

---

## Task 5: Implement `preflight.py`

**Files:**
- Create: `scripts/seed/preflight.py`
- Create: `scripts/seed/tests/test_preflight.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/test_preflight.py
from unittest.mock import MagicMock, patch
import preflight


def _make_conn(client_encoding="UTF8", dialect_rows=None):
    if dialect_rows is None:
        dialect_rows = [
            (1, "Standard Yoruba"), (2, "Ife"), (3, "Ilaje"), (4, "Ijebu"),
            (5, "Central Igbo"), (6, "Ehugbo"), (7, "Enuani"),
            (8, "Standard Hausa"), (9, "Sokoto Hausa"),
        ]
    fake_conn = MagicMock()
    cur = fake_conn.cursor.return_value.__enter__.return_value

    def execute_side_effect(sql, *args, **kwargs):
        cur._last_sql = sql
    cur.execute.side_effect = execute_side_effect

    def fetchone():
        if "client_encoding" in cur._last_sql:
            return (client_encoding,)
        return (0,)

    def fetchall():
        return dialect_rows
    cur.fetchone.side_effect = fetchone
    cur.fetchall.side_effect = fetchall
    return fake_conn


def test_preflight_passes_on_clean_db():
    with patch("preflight.db.connect", return_value=_make_conn()):
        exit_code = preflight.run()
    assert exit_code == 0


def test_preflight_fails_on_non_utf8_encoding():
    with patch("preflight.db.connect", return_value=_make_conn(client_encoding="LATIN1")):
        exit_code = preflight.run()
    assert exit_code != 0


def test_preflight_fails_on_dialect_mismatch():
    bad_rows = [(1, "Wrong Name"), (2, "Ife"), (3, "Ilaje"), (4, "Ijebu"),
                (5, "Central Igbo"), (6, "Ehugbo"), (7, "Enuani"),
                (8, "Standard Hausa"), (9, "Sokoto Hausa")]
    with patch("preflight.db.connect", return_value=_make_conn(dialect_rows=bad_rows)):
        exit_code = preflight.run()
    assert exit_code != 0


def test_preflight_fails_on_missing_dialect():
    short_rows = [(1, "Standard Yoruba"), (2, "Ife")]  # missing 3-9
    with patch("preflight.db.connect", return_value=_make_conn(dialect_rows=short_rows)):
        exit_code = preflight.run()
    assert exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest scripts/seed/tests/test_preflight.py -v`. Expected: import error.

- [ ] **Step 3: Implement `scripts/seed/preflight.py`**

```python
"""Preflight checks: connection, encoding, dialect map, row counts."""
import sys
import db
from config import DIALECT_MAP


def run() -> int:
    """Run all preflight checks. Print results. Return 0 if all pass, 1 otherwise."""
    try:
        conn = db.connect()
    except Exception as e:
        print(f"[preflight] FAIL: cannot connect: {e}", file=sys.stderr)
        return 1

    failed = False

    with conn.cursor() as cur:
        cur.execute("SHOW client_encoding")
        (encoding,) = cur.fetchone()
    print(f"[preflight] client_encoding = {encoding}")
    if encoding.upper() != "UTF8":
        print(f"[preflight] FAIL: client_encoding must be UTF8, got {encoding}", file=sys.stderr)
        failed = True

    with conn.cursor() as cur:
        cur.execute("SELECT dialect_id, name FROM dialects ORDER BY dialect_id")
        rows = cur.fetchall()
    actual = {row[0]: row[1] for row in rows}
    expected = {k: v[0] for k, v in DIALECT_MAP.items()}
    if actual != expected:
        print("[preflight] FAIL: dialects table does not match DIALECT_MAP", file=sys.stderr)
        for k in sorted(set(actual) | set(expected)):
            a = actual.get(k, "<missing>")
            e = expected.get(k, "<missing>")
            mark = "OK" if a == e else "DIFF"
            print(f"  [{mark}] id={k}: db={a!r} expected={e!r}")
        failed = True
    else:
        print(f"[preflight] dialect map OK ({len(expected)} entries)")

    entries_count = db.entries_row_count(conn)
    print(f"[preflight] entries row count: {entries_count}")
    print(f"[preflight] metadata row count: {_metadata_count(conn)}")

    conn.close()
    return 1 if failed else 0


def _metadata_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM metadata")
        (count,) = cur.fetchone()
    return count
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest scripts/seed/tests/test_preflight.py -v`. Expected: all 4 PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/preflight.py scripts/seed/tests/test_preflight.py
git commit -m "add preflight module: encoding + dialect-map + row-count checks"
```

---

## Task 6: Implement `verify.py`

**Files:**
- Create: `scripts/seed/verify.py`
- Create: `scripts/seed/tests/test_verify.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/test_verify.py
from unittest.mock import MagicMock, patch
import verify


def _make_conn(breakdown_rows, entries_count=100, metadata_count=100):
    fake_conn = MagicMock()
    cur = fake_conn.cursor.return_value.__enter__.return_value
    cur._last_sql = ""

    def execute_side_effect(sql, *a, **kw):
        cur._last_sql = sql
    cur.execute.side_effect = execute_side_effect

    def fetchone():
        if "FROM entries" in cur._last_sql:
            return (entries_count,)
        if "FROM metadata" in cur._last_sql:
            return (metadata_count,)
        return None
    cur.fetchone.side_effect = fetchone
    cur.fetchall.return_value = breakdown_rows
    return fake_conn


def test_verify_returns_zero_when_data_exists():
    rows = [("Yoruba", "Standard Yoruba", 500), ("Igbo", "Central Igbo", 800)]
    with patch("verify.db.connect", return_value=_make_conn(rows, entries_count=1300)):
        assert verify.run() == 0


def test_verify_returns_one_when_entries_empty():
    with patch("verify.db.connect", return_value=_make_conn([], entries_count=0)):
        assert verify.run() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest scripts/seed/tests/test_verify.py -v`. Expected: import error.

- [ ] **Step 3: Implement `scripts/seed/verify.py`**

```python
"""Verify subcommand: prints language/dialect breakdown and exits non-zero if empty."""
import db


_BREAKDOWN_SQL = """
SELECT l.name AS language, d.name AS dialect, COUNT(e.entry_id) AS total
FROM entries e
JOIN dialects d ON e.dialect_id = d.dialect_id
JOIN languages l ON d.language_id = l.language_id
GROUP BY l.name, d.name
ORDER BY l.name, d.name
"""


def run() -> int:
    """Print breakdown. Exit 0 if entries has any rows, 1 if empty."""
    conn = db.connect()
    try:
        entries_count = db.entries_row_count(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM metadata")
            (metadata_count,) = cur.fetchone()
            cur.execute(_BREAKDOWN_SQL)
            rows = cur.fetchall()

        print(f"{'Language':<10} {'Dialect':<20} {'Total':>8}")
        print("-" * 40)
        for language, dialect, total in rows:
            print(f"{language:<10} {dialect:<20} {total:>8}")
        print("-" * 40)
        print(f"entries:  {entries_count}")
        print(f"metadata: {metadata_count}")
        if entries_count != metadata_count:
            print(f"WARNING: entries and metadata row counts differ ({entries_count} vs {metadata_count})")
        return 0 if entries_count > 0 else 1
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest scripts/seed/tests/test_verify.py -v`. Expected: 2 PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/verify.py scripts/seed/tests/test_verify.py
git commit -m "add verify module: language/dialect breakdown + exit code"
```

---

## Task 7: IgboAPI — `transform_entry` (pure function) and `transform`

**Files:**
- Create: `scripts/seed/loaders/igbo_api.py`
- Create: `scripts/seed/tests/loaders/test_igbo_api.py`
- Create: `scripts/seed/tests/fixtures/igbo_api_sample.json`

**Note on package name:** `loaders/` (not `datasets/`) avoids shadowing the Hugging Face `datasets` Python package, which we import inside our loader modules. Tests refer to our package as `loaders.<name>`; HF's library stays as `import datasets`.

- [ ] **Step 1: Create test fixture** at `scripts/seed/tests/fixtures/igbo_api_sample.json`

```json
[
  {"word": "akwa", "wordClass": "noun", "definitions": ["cloth", "egg"],
   "examples": ["Akwa di mma."], "dialects": []},
  {"word": "akwa", "wordClass": "noun", "definitions": ["a different sense"],
   "examples": [], "dialects": ["Ehugbo"]},
  {"word": "ulo", "wordClass": "noun", "definitions": ["house"],
   "examples": [], "dialects": ["Ehugbo"]},
  {"word": "mmiri", "wordClass": "noun", "definitions": ["water"],
   "examples": [], "dialects": ["Enuani"]},
  {"word": "anya", "definitions": ["eye"], "examples": [], "dialects": []},
  {"word": "isi", "wordClass": "noun", "definitions": ["head"],
   "examples": [], "dialects": []}
]
```

- [ ] **Step 2: Write the failing tests** in `scripts/seed/tests/loaders/test_igbo_api.py`

```python
import json
from pathlib import Path
import pandas as pd
from loaders import igbo_api


FIXTURE = Path(__file__).parent.parent / "fixtures" / "igbo_api_sample.json"


def test_transform_entry_uses_central_default_when_no_dialect():
    raw = {"word": "isi", "wordClass": "noun", "definitions": ["head"],
           "examples": [], "dialects": []}
    headword, pos, dialect_id, jsonb = igbo_api.transform_entry(raw)
    assert headword == "isi"
    assert pos == "noun"
    assert dialect_id == 5
    assert jsonb["source"] == "IgboAPI"
    assert jsonb["definitions"] == ["head"]
    assert jsonb["dialect_variants"] == []


def test_transform_entry_maps_ehugbo_to_6():
    raw = {"word": "ulo", "wordClass": "noun", "definitions": ["house"],
           "examples": [], "dialects": ["Ehugbo"]}
    _, _, dialect_id, jsonb = igbo_api.transform_entry(raw)
    assert dialect_id == 6
    assert jsonb["dialect_variants"] == ["Ehugbo"]


def test_transform_entry_maps_enuani_to_7():
    raw = {"word": "mmiri", "wordClass": "noun", "definitions": ["water"],
           "examples": [], "dialects": ["Enuani"]}
    _, _, dialect_id, _ = igbo_api.transform_entry(raw)
    assert dialect_id == 7


def test_transform_entry_defaults_pos_to_unknown_when_missing():
    raw = {"word": "anya", "definitions": ["eye"], "examples": [], "dialects": []}
    _, pos, _, _ = igbo_api.transform_entry(raw)
    assert pos == "unknown"


def test_transform_keeps_all_minority_and_caps_central(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    # 3 Central, 1 Ehugbo, 1 Enuani; cap is "1000 total" but for this test we
    # patch the cap to 3 so the math is: 1 Ehugbo + 1 Enuani + sample 1 from 3 Central.
    entries = (
        [{"word": f"central_{i}", "wordClass": "noun", "definitions": [],
          "examples": [], "dialects": []} for i in range(3)]
        + [{"word": "ulo", "wordClass": "noun", "definitions": [],
            "examples": [], "dialects": ["Ehugbo"]}]
        + [{"word": "mmiri", "wordClass": "noun", "definitions": [],
            "examples": [], "dialects": ["Enuani"]}]
    )
    (raw_dir / "igbo_api.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = igbo_api.transform(raw_dir, tmp_path / "clean", cap=3)

    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 3
    assert (df["dialect_id"] == "6").sum() == 1
    assert (df["dialect_id"] == "7").sum() == 1
    assert (df["dialect_id"] == "5").sum() == 1


def test_transform_dedups_by_headword_and_dialect(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    entries = [
        {"word": "akwa", "wordClass": "noun", "definitions": ["cloth"],
         "examples": [], "dialects": []},
        {"word": "akwa", "wordClass": "noun", "definitions": ["egg"],
         "examples": [], "dialects": []},
        {"word": "akwa", "wordClass": "noun", "definitions": ["different"],
         "examples": [], "dialects": ["Ehugbo"]},
    ]
    (raw_dir / "igbo_api.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = igbo_api.transform(raw_dir, tmp_path / "clean", cap=10)

    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 2
    assert set(df["dialect_id"]) == {"5", "6"}


def test_transform_uses_fixture_file_to_produce_csv():
    # End-to-end against the committed fixture.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        raw = td / "raw"
        raw.mkdir()
        (raw / "igbo_api.json").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        csv_path = igbo_api.transform(raw, td / "clean", cap=10)
        df = pd.read_csv(csv_path, dtype=str)
        # 5 unique (headword, dialect_id) tuples after dedup
        # akwa/5, akwa/6, ulo/6, mmiri/7, anya/5, isi/5  -> 6
        assert len(df) == 6
        assert "headword" in df.columns
        assert "pos" in df.columns
        assert "dialect_id" in df.columns
        assert "jsonb_data" in df.columns
```

- [ ] **Step 3: Run tests to verify they fail**

```powershell
python -m pytest scripts/seed/tests/loaders/test_igbo_api.py -v
```

Expected: `ModuleNotFoundError: No module named 'loaders.igbo_api'`.

- [ ] **Step 4: Implement `scripts/seed/loaders/igbo_api.py`**

```python
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
    Enuani) are kept entirely; Central is sampled to fill remainder.
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
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/loaders/test_igbo_api.py -v
```

Expected: 7 PASS.

- [ ] **Step 6: Commit**

```powershell
git add scripts/seed/loaders/ scripts/seed/tests/loaders/test_igbo_api.py scripts/seed/tests/fixtures/igbo_api_sample.json
git commit -m "add IgboAPI loader: transform_entry and transform with seeded sampling"
```

---

## Task 8: IgboAPI — `download` and `load` (thin wrappers)

**Files:**
- Modify: `scripts/seed/loaders/igbo_api.py`
- Modify: `scripts/seed/tests/loaders/test_igbo_api.py`

- [ ] **Step 1: Add failing tests**

```python
from unittest.mock import MagicMock, patch


def test_download_uses_hf_dataset_first(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_ds = MagicMock()
    fake_ds["train"].to_list.return_value = [{"word": "x", "wordClass": "n",
                                              "definitions": [], "examples": [], "dialects": []}]
    with patch("loaders.igbo_api.hf_load_dataset", return_value=fake_ds) as load_ds:
        igbo_api.download(raw_dir)
    load_ds.assert_called_once_with("nkowaokwu/igbo_api")
    assert (raw_dir / "igbo_api.json").exists()


def test_download_falls_back_to_github_on_hf_failure(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_response = MagicMock()
    fake_response.json.return_value = [{"word": "x", "wordClass": "n",
                                        "definitions": [], "examples": [], "dialects": []}]
    fake_response.raise_for_status.return_value = None
    with patch("loaders.igbo_api.hf_load_dataset", side_effect=RuntimeError("HF down")), \
         patch("loaders.igbo_api.requests.get", return_value=fake_response) as get:
        igbo_api.download(raw_dir)
    assert get.called
    assert (raw_dir / "igbo_api.json").exists()


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "igbo_api_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.igbo_api.db.load_csv", return_value=42) as load_csv:
        result = igbo_api.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 42
```

- [ ] **Step 2: Run failing**

```powershell
python -m pytest scripts/seed/tests/loaders/test_igbo_api.py -v
```

Expected: 3 new tests FAIL with `AttributeError: module 'loaders.igbo_api' has no attribute 'download'` / `'load'`.

- [ ] **Step 3: Add `download` and `load` to `scripts/seed/loaders/igbo_api.py`**

Append:

```python
import requests
from datasets import load_dataset as hf_load_dataset  # HF library

import db

_GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/nkowaokwu/igbo_api/main/"
    "src/dictionaries/ig-en/ig-en.json"
)


def download(raw_dir: Path) -> Path:
    """Download IgboAPI to raw_dir/igbo_api.json. HF first, GitHub fallback."""
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    out = raw_dir / "igbo_api.json"

    try:
        ds = hf_load_dataset("nkowaokwu/igbo_api")
        records = ds["train"].to_list()
    except Exception as e:
        print(f"[igbo_api] HF download failed ({e}); falling back to GitHub raw")
        resp = requests.get(_GITHUB_RAW_URL, timeout=60)
        resp.raise_for_status()
        records = resp.json()

    out.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    print(f"[igbo_api] wrote {len(records)} raw entries to {out}")
    return out


def load(csv_path: Path, conn) -> int:
    """Insert the cleaned CSV via db.load_csv."""
    return db.load_csv(csv_path, conn)
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/loaders/test_igbo_api.py -v
```

Expected: 10 PASS (7 prior + 3 new).

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/loaders/igbo_api.py scripts/seed/tests/loaders/test_igbo_api.py
git commit -m "add IgboAPI download (HF + GitHub fallback) and load wrapper"
```

---

## Task 9: YorùLect — `download` (README scrape + gdown)

**Files:**
- Create: `scripts/seed/loaders/yorulect.py`
- Create: `scripts/seed/tests/loaders/test_yorulect.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/loaders/test_yorulect.py
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from loaders import yorulect


def test_extract_drive_url_from_readme():
    readme = """
    # YorùLect
    Download the data from
    https://drive.google.com/drive/folders/1aBcDeF12345 here.
    """
    url = yorulect.extract_drive_url(readme)
    assert url == "https://drive.google.com/drive/folders/1aBcDeF12345"


def test_extract_drive_url_raises_when_missing():
    with pytest.raises(ValueError, match="No Google Drive"):
        yorulect.extract_drive_url("# README with no link")


def test_download_scrapes_readme_then_calls_gdown(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_resp = MagicMock()
    fake_resp.text = "see https://drive.google.com/drive/folders/XYZ for data"
    fake_resp.raise_for_status.return_value = None
    with patch("loaders.yorulect.requests.get", return_value=fake_resp) as gh, \
         patch("loaders.yorulect.gdown.download_folder") as gd:
        yorulect.download(raw_dir)
    gh.assert_called_once()
    gd.assert_called_once()
    assert "XYZ" in gd.call_args[0][0]


def test_download_falls_back_to_drive_link_txt(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "DRIVE_LINK.txt").write_text(
        "https://drive.google.com/drive/folders/MANUAL", encoding="utf-8"
    )
    with patch("loaders.yorulect.requests.get", side_effect=RuntimeError("rate limited")), \
         patch("loaders.yorulect.gdown.download_folder") as gd:
        yorulect.download(raw_dir)
    gd.assert_called_once()
    assert "MANUAL" in gd.call_args[0][0]
```

- [ ] **Step 2: Run failing**

Expected: `ModuleNotFoundError: No module named 'loaders.yorulect'`.

- [ ] **Step 3: Implement `scripts/seed/loaders/yorulect.py`** (download portion only)

```python
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


def download(raw_dir: Path) -> Path:
    """Resolve the Drive URL and pull the folder via gdown.

    Tries the GitHub README first; if that fails, looks for
    raw_dir/DRIVE_LINK.txt as a manual override.
    """
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(_README_URL, timeout=30)
        resp.raise_for_status()
        url = extract_drive_url(resp.text)
        print(f"[yorulect] resolved Drive URL from README: {url}")
    except Exception as e:
        link_file = raw_dir / "DRIVE_LINK.txt"
        if link_file.exists():
            url = link_file.read_text(encoding="utf-8").strip()
            print(f"[yorulect] README fetch failed ({e}); using {link_file}: {url}")
        else:
            print(f"[yorulect] FAIL: README unreachable and no {link_file}", flush=True)
            raise

    gdown.download_folder(url, output=str(raw_dir), quiet=False)
    return raw_dir
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/loaders/yorulect.py scripts/seed/tests/loaders/test_yorulect.py
git commit -m "add YorùLect download with README scrape and DRIVE_LINK.txt fallback"
```

---

## Task 10: YorùLect — `transform` and `load`

**Files:**
- Modify: `scripts/seed/loaders/yorulect.py`
- Modify: `scripts/seed/tests/loaders/test_yorulect.py`
- Create: `scripts/seed/tests/fixtures/yorulect/standard/farming.tsv`
- Create: `scripts/seed/tests/fixtures/yorulect/standard/cooking.tsv`
- Create: `scripts/seed/tests/fixtures/yorulect/ife/farming.tsv`

- [ ] **Step 1: Create fixture files**

`scripts/seed/tests/fixtures/yorulect/standard/farming.tsv`:
```
english	yoruba
The farmer plants yam.	Àgbẹ̀ ń gbin iṣu.
The rain is heavy.	Òjò ń rọ̀ púpọ̀.
He owns a farm.	Ó ní oko.
```

`scripts/seed/tests/fixtures/yorulect/standard/cooking.tsv` (deliberately repeats one line from farming to exercise cross-file dedup):
```
english	yoruba
She cooks rice.	Ó ń se ìrẹsì.
He owns a farm.	Ó ní oko.
The pot is hot.	Ìkòkò gbígbóná ni.
```

`scripts/seed/tests/fixtures/yorulect/ife/farming.tsv`:
```
english	yoruba
The farmer plants yam.	Àgbẹ̀ ǹ gbin iṣu.
The rain is heavy.	Òjò ǹ rọ̀ púpọ̀.
```

- [ ] **Step 2: Add failing tests**

```python
import shutil
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures" / "yorulect"


def _copy_fixtures(dest: Path):
    shutil.copytree(FIXTURES, dest)


def test_transform_picks_yoruba_column_and_assigns_dialect_from_folder(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["pos"] == "sentence").all()
    standard = df[df["dialect_id"] == "1"]
    ife = df[df["dialect_id"] == "2"]
    assert "Àgbẹ̀ ń gbin iṣu." in standard["headword"].values
    assert "Àgbẹ̀ ǹ gbin iṣu." in ife["headword"].values  # different diacritic


def test_transform_jsonb_carries_domain_and_english(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    row = df[df["headword"] == "Àgbẹ̀ ń gbin iṣu."].iloc[0]
    jsonb = json.loads(row["jsonb_data"])
    assert jsonb["source"] == "YorùLect"
    assert jsonb["domain"] == "farming"
    assert jsonb["english_translation"] == "The farmer plants yam."


def test_transform_cross_file_dedup_keeps_first_alphabetical(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    # "Ó ní oko." appears in both standard/farming.tsv and standard/cooking.tsv.
    # cooking.tsv sorts before farming.tsv alphabetically, so cooking wins.
    duplicates = df[df["headword"] == "Ó ní oko."]
    assert len(duplicates) == 1
    jsonb = json.loads(duplicates.iloc[0]["jsonb_data"])
    assert jsonb["domain"] == "cooking"


def test_transform_underflow_caps_at_available(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    # ife only has 2 unique sentences in the fixture; cap of 250 means we get 2.
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=250)
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["dialect_id"] == "2").sum() == 2


def test_transform_aborts_on_missing_dialect_folder(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    raw.mkdir(parents=True)
    # only standard/, no others
    (raw / "standard").mkdir()
    (raw / "standard" / "x.tsv").write_text("english\tyoruba\nhi\tbonjour\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)


def test_transform_aborts_on_missing_columns(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    for sub in ("standard", "ife", "ilaje", "ijebu"):
        (raw / sub).mkdir(parents=True)
        (raw / sub / "bad.tsv").write_text("col1\tcol2\nx\ty\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "yorulect_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.yorulect.db.load_csv", return_value=11) as load_csv:
        result = yorulect.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 11
```

- [ ] **Step 3: Run failing**

Expected: 7 new tests FAIL.

- [ ] **Step 4: Implement `transform` and `load` in `scripts/seed/loaders/yorulect.py`**

Append:

```python
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
                             keep_default_na=False)
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
    return out


def load(csv_path: Path, conn) -> int:
    return db.load_csv(csv_path, conn)
```

- [ ] **Step 5: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/loaders/test_yorulect.py -v
```

Expected: 11 PASS (4 prior + 7 new).

- [ ] **Step 6: Commit**

```powershell
git add scripts/seed/loaders/yorulect.py scripts/seed/tests/loaders/test_yorulect.py scripts/seed/tests/fixtures/yorulect/
git commit -m "add YorùLect transform with cross-file dedup, underflow handling, and load"
```

---

## Task 11: VOA NER — `transform_entry`, `transform`, `download`, `load`

**Files:**
- Create: `scripts/seed/loaders/voa_ner.py`
- Create: `scripts/seed/tests/loaders/test_voa_ner.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/loaders/test_voa_ner.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from loaders import voa_ner


def test_transform_entry_joins_tokens_and_marks_default_dialect():
    raw = {"tokens": ["Sannu", "duniya", "."], "ner_tags": [0, 0, 0], "split": "train"}
    headword, pos, dialect_id, jsonb = voa_ner.transform_entry(raw)
    assert headword == "Sannu duniya ."
    assert pos == "sentence"
    assert dialect_id == 8
    assert jsonb == {"source": "VOA Hausa", "split": "train",
                     "dialect_assigned_default": True}


def test_transform_entry_drops_ner_tags():
    raw = {"tokens": ["a", "b"], "ner_tags": [1, 2], "split": "test"}
    *_, jsonb = voa_ner.transform_entry(raw)
    assert "ner_tags" not in jsonb


def test_transform_dedups_and_caps(tmp_path):
    raw_dir = tmp_path / "raw" / "voa_ner"
    raw_dir.mkdir(parents=True)
    entries = [
        {"tokens": [f"sentence", str(i)], "ner_tags": [0, 0], "split": "train"}
        for i in range(20)
    ] + [
        {"tokens": ["dup"], "ner_tags": [0], "split": "train"},
        {"tokens": ["dup"], "ner_tags": [0], "split": "test"},  # duplicate, dropped
    ]
    (raw_dir / "voa_ner.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = voa_ner.transform(raw_dir.parent, tmp_path / "clean", cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 10
    assert df["headword"].is_unique
    assert (df["dialect_id"] == "8").all()


def test_download_pulls_all_three_splits(tmp_path):
    raw_dir = tmp_path / "raw" / "voa_ner"
    fake_ds = {
        "train":      [{"tokens": ["a"], "ner_tags": [0]}],
        "validation": [{"tokens": ["b"], "ner_tags": [0]}],
        "test":       [{"tokens": ["c"], "ner_tags": [0]}],
    }

    def fake_load_dataset(name, split=None):
        m = MagicMock()
        m.to_list.return_value = list(fake_ds[split])
        return m

    with patch("loaders.voa_ner.hf_load_dataset", side_effect=fake_load_dataset):
        voa_ner.download(raw_dir.parent)

    out = json.loads((raw_dir / "voa_ner.json").read_text(encoding="utf-8"))
    splits = {row["split"] for row in out}
    assert splits == {"train", "validation", "test"}


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "voa_ner_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.voa_ner.db.load_csv", return_value=5) as load_csv:
        result = voa_ner.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 5
```

- [ ] **Step 2: Run failing**

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/seed/loaders/voa_ner.py`**

```python
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
    headword = " ".join(raw["tokens"])
    jsonb = {
        "source": SOURCE_TAG,
        "split": raw["split"],
        "dialect_assigned_default": True,
    }
    return headword, "sentence", 8, jsonb


def download(raw_root: Path) -> Path:
    raw_dir = Path(raw_root) / "voa_ner"
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
    raw_root = Path(raw_root)
    clean_dir = Path(clean_dir)
    clean_dir.mkdir(parents=True, exist_ok=True)
    if cap is None:
        cap = CAPS["voa_ner"]["total"]

    raw_entries = json.loads((raw_root / "voa_ner" / "voa_ner.json").read_text(encoding="utf-8"))
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


def load(csv_path: Path, conn) -> int:
    return db.load_csv(csv_path, conn)
```

- [ ] **Step 4: Run tests to verify they pass**

Expected: 5 PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/loaders/voa_ner.py scripts/seed/tests/loaders/test_voa_ner.py
git commit -m "add VOA NER loader: download, transform with seeded sample, load"
```

---

## Task 12: NaijaSenti — `transform_entry`, `transform`, `download`, `load`

**Files:**
- Create: `scripts/seed/loaders/naijasenti.py`
- Create: `scripts/seed/tests/loaders/test_naijasenti.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/loaders/test_naijasenti.py
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from loaders import naijasenti


def test_transform_entry_yor_maps_to_dialect_1():
    raw = {"tweet": "Mo nife re", "sentiment": "positive", "split": "train"}
    headword, pos, dialect_id, jsonb = naijasenti.transform_entry(raw, lang="yor")
    assert headword == "Mo nife re"
    assert pos == "sentence"
    assert dialect_id == 1
    assert jsonb == {"source": "NaijaSenti", "type": "tweet", "sentiment": "positive",
                     "split": "train", "dialect_assigned_default": True}


def test_transform_entry_ibo_maps_to_5():
    _, _, dialect_id, _ = naijasenti.transform_entry(
        {"tweet": "x", "sentiment": "neutral", "split": "test"}, lang="ibo"
    )
    assert dialect_id == 5


def test_transform_entry_hau_maps_to_8():
    _, _, dialect_id, _ = naijasenti.transform_entry(
        {"tweet": "y", "sentiment": "negative", "split": "validation"}, lang="hau"
    )
    assert dialect_id == 8


def test_transform_applies_per_language_quotas(tmp_path):
    raw_root = tmp_path / "raw" / "naijasenti"
    raw_root.mkdir(parents=True)
    payload = {
        "yor": [{"tweet": f"yor_{i}", "sentiment": "positive", "split": "train"}
                for i in range(800)],
        "ibo": [{"tweet": f"ibo_{i}", "sentiment": "neutral", "split": "train"}
                for i in range(800)],
        "hau": [{"tweet": f"hau_{i}", "sentiment": "negative", "split": "train"}
                for i in range(800)],
    }
    (raw_root / "naijasenti.json").write_text(json.dumps(payload), encoding="utf-8")

    csv_path = naijasenti.transform(
        raw_root.parent, tmp_path / "clean",
        quotas={"yor": 50, "ibo": 50, "hau": 75},
    )
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["dialect_id"] == "1").sum() == 50
    assert (df["dialect_id"] == "5").sum() == 50
    assert (df["dialect_id"] == "8").sum() == 75


def test_transform_dedups_within_language(tmp_path):
    raw_root = tmp_path / "raw" / "naijasenti"
    raw_root.mkdir(parents=True)
    payload = {
        "yor": [{"tweet": "same", "sentiment": "positive", "split": "train"},
                {"tweet": "same", "sentiment": "neutral", "split": "test"},
                {"tweet": "different", "sentiment": "positive", "split": "train"}],
        "ibo": [],
        "hau": [],
    }
    (raw_root / "naijasenti.json").write_text(json.dumps(payload), encoding="utf-8")

    csv_path = naijasenti.transform(
        raw_root.parent, tmp_path / "clean",
        quotas={"yor": 10, "ibo": 10, "hau": 10},
    )
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["dialect_id"] == "1").sum() == 2


def test_download_skips_pcm_and_resolves_int_labels(tmp_path):
    raw_root = tmp_path / "raw" / "naijasenti"

    class FakeFeatures:
        def __init__(self, label_names):
            self.label_names = label_names
            self.label = MagicMock()
            self.label.int2str = lambda i: label_names[i]
        def __getitem__(self, k):
            return self.label

    def fake_load_dataset(name, lang):
        assert lang in ("yor", "ibo", "hau")  # not pcm
        ds = MagicMock()
        ds.keys.return_value = ["train"]
        feats = FakeFeatures(["negative", "neutral", "positive"])

        def fake_split_iter():
            return iter([{"tweet": f"{lang}_t1", "label": 2},
                         {"tweet": f"{lang}_t2", "label": 0}])

        ds.__getitem__.return_value.features = feats
        ds.__getitem__.return_value.__iter__ = lambda _self: fake_split_iter()
        return ds

    with patch("loaders.naijasenti.hf_load_dataset", side_effect=fake_load_dataset) as load_ds:
        naijasenti.download(raw_root.parent)

    called_langs = [call.kwargs.get("lang") or call.args[1] for call in load_ds.call_args_list]
    assert "pcm" not in called_langs
    assert set(called_langs) == {"yor", "ibo", "hau"}
    payload = json.loads((raw_root / "naijasenti.json").read_text(encoding="utf-8"))
    assert "pcm" not in payload
    assert payload["yor"][0]["sentiment"] == "positive"


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "naijasenti_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.naijasenti.db.load_csv", return_value=9) as load_csv:
        result = naijasenti.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 9
```

- [ ] **Step 2: Run failing**

Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement `scripts/seed/loaders/naijasenti.py`**

```python
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

    payload = json.loads((raw_root / "naijasenti" / "naijasenti.json").read_text(encoding="utf-8"))
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
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/loaders/test_naijasenti.py -v
```

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/loaders/naijasenti.py scripts/seed/tests/loaders/test_naijasenti.py
git commit -m "add NaijaSenti loader: hau/ibo/yor with per-language quotas, pcm skipped"
```

---

## Task 13: `seed.py` CLI — argparse and subcommand dispatch

**Files:**
- Create: `scripts/seed/seed.py`
- Create: `scripts/seed/tests/test_seed_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
# scripts/seed/tests/test_seed_cli.py
from unittest.mock import MagicMock, patch
import pytest
import seed


def test_parser_accepts_preflight():
    args = seed.build_parser().parse_args(["preflight"])
    assert args.command == "preflight"


def test_parser_accepts_verify():
    args = seed.build_parser().parse_args(["verify"])
    assert args.command == "verify"


def test_parser_per_dataset_subcommands():
    for sub in ("download", "sample", "transform", "load"):
        args = seed.build_parser().parse_args([sub, "igbo_api"])
        assert args.command == sub
        assert args.dataset == "igbo_api"


def test_parser_load_accepts_flags():
    args = seed.build_parser().parse_args(["load", "voa_ner", "--abort-if-not-empty", "--force"])
    assert args.abort_if_not_empty is True
    assert args.force is True


def test_parser_load_rejects_truncate_flag():
    parser = seed.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["load", "igbo_api", "--truncate"])


def test_parser_all_requires_one_of_truncate_or_abort():
    parser = seed.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["all"])


def test_parser_all_accepts_truncate():
    args = seed.build_parser().parse_args(["all", "--truncate"])
    assert args.truncate is True
    assert args.abort_if_not_empty is False


def test_parser_all_accepts_abort_if_not_empty():
    args = seed.build_parser().parse_args(["all", "--abort-if-not-empty"])
    assert args.abort_if_not_empty is True
    assert args.truncate is False


def test_parser_all_rejects_both_flags():
    parser = seed.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["all", "--truncate", "--abort-if-not-empty"])
```

- [ ] **Step 2: Run failing**

Expected: `ModuleNotFoundError: No module named 'seed'`.

- [ ] **Step 3: Implement `scripts/seed/seed.py`** (parser only — dispatch added in Task 14)

```python
"""seed.py — CLI driver for the seed pipeline."""
import argparse
import sys

DATASETS = ("igbo_api", "yorulect", "voa_ner", "naijasenti")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seed")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="Connection + encoding + dialect-map checks")
    sub.add_parser("verify", help="Print breakdown; exit 1 if entries empty")

    for cmd in ("download", "sample", "transform"):
        p = sub.add_parser(cmd)
        p.add_argument("dataset", choices=DATASETS)

    p_load = sub.add_parser("load")
    p_load.add_argument("dataset", choices=DATASETS)
    p_load.add_argument("--abort-if-not-empty", action="store_true",
                        help="Refuse if entries table is non-empty")
    p_load.add_argument("--force", action="store_true",
                        help="Override the source-tag check")

    p_all = sub.add_parser("all")
    grp = p_all.add_mutually_exclusive_group(required=True)
    grp.add_argument("--truncate", action="store_true",
                     help="TRUNCATE entries+metadata before loading")
    grp.add_argument("--abort-if-not-empty", action="store_true",
                     help="Refuse if entries table is non-empty")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Dispatch added in Task 14.
    raise NotImplementedError(f"command {args.command} not wired yet")


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/test_seed_cli.py -v
```

Expected: 9 PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/seed.py scripts/seed/tests/test_seed_cli.py
git commit -m "add seed.py argparse with preflight/verify/per-dataset/all subcommands"
```

---

## Task 14: `seed.py` — gate checks for `load` subcommand

**Files:**
- Modify: `scripts/seed/seed.py`
- Modify: `scripts/seed/tests/test_seed_cli.py`

- [ ] **Step 1: Add failing tests**

```python
def test_load_dispatch_aborts_if_table_non_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 5)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)

    rc = seed.main(["load", "igbo_api", "--abort-if-not-empty"])
    assert rc == 1


def test_load_dispatch_aborts_if_source_already_loaded(monkeypatch):
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 100)

    rc = seed.main(["load", "igbo_api"])
    assert rc == 1


def test_load_dispatch_force_overrides_source_check(monkeypatch, tmp_path):
    csv_path = tmp_path / "igbo_api_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 100)
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("loaders.igbo_api.load", MagicMock(return_value=0))

    rc = seed.main(["load", "igbo_api", "--force"])
    assert rc == 0
```

- [ ] **Step 2: Run failing**

Run: `python -m pytest scripts/seed/tests/test_seed_cli.py -v`. Expected: new tests fail with `NotImplementedError`.

- [ ] **Step 3: Replace the `main()` body in `scripts/seed/seed.py`**

Add at top of file:

```python
from pathlib import Path

import db
import preflight as preflight_module
import verify as verify_module
from loaders import igbo_api, yorulect, voa_ner, naijasenti
from config import SOURCE_TAGS

CLEAN_DIR = Path(__file__).resolve().parent.parent.parent / "clean"
RAW_DIR = Path(__file__).resolve().parent.parent.parent / "raw"

LOADERS = {
    "igbo_api": igbo_api,
    "yorulect": yorulect,
    "voa_ner": voa_ner,
    "naijasenti": naijasenti,
}
```

Replace `main()`:

```python
def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "preflight":
        return preflight_module.run()
    if args.command == "verify":
        return verify_module.run()
    if args.command == "download":
        LOADERS[args.dataset].download(RAW_DIR)
        return 0
    if args.command == "sample":
        return _do_sample(args.dataset)
    if args.command == "transform":
        LOADERS[args.dataset].transform(RAW_DIR, CLEAN_DIR)
        return 0
    if args.command == "load":
        return _do_load(args)
    if args.command == "all":
        return _do_all(args)
    raise AssertionError(f"unhandled command: {args.command}")


def _do_load(args) -> int:
    csv_path = CLEAN_DIR / f"{args.dataset}_clean.csv"
    if not csv_path.exists():
        print(f"[load] missing {csv_path}; run `transform {args.dataset}` first",
              file=sys.stderr)
        return 1
    conn = db.connect()
    try:
        if args.abort_if_not_empty and db.entries_row_count(conn) > 0:
            print("[load] refusing: entries table is not empty "
                  "(--abort-if-not-empty was set)", file=sys.stderr)
            return 1
        tag = SOURCE_TAGS[args.dataset]
        if not args.force and db.source_row_count(conn, tag) > 0:
            print(f"[load] refusing: source {tag!r} already has rows. "
                  f"Pass --force to override.", file=sys.stderr)
            return 1
        inserted = LOADERS[args.dataset].load(csv_path, conn)
        print(f"[load] {args.dataset}: inserted {inserted} rows")
        return 0
    finally:
        conn.close()


def _do_sample(dataset: str) -> int:
    """Print one raw entry from raw/<dataset>/ and exit. Read-only."""
    import json as _json
    raw_root = RAW_DIR / dataset
    if dataset == "naijasenti":
        payload = _json.loads((raw_root / "naijasenti.json").read_text(encoding="utf-8"))
        first_lang = next(iter(payload))
        print(f"[sample] naijasenti {first_lang}[0]:")
        print(_json.dumps(payload[first_lang][0], ensure_ascii=False, indent=2))
    elif dataset == "voa_ner":
        rows = _json.loads((raw_root / "voa_ner.json").read_text(encoding="utf-8"))
        print(_json.dumps(rows[0], ensure_ascii=False, indent=2))
    elif dataset == "igbo_api":
        rows = _json.loads((RAW_DIR / "igbo_api.json").read_text(encoding="utf-8"))
        print(_json.dumps(rows[0], ensure_ascii=False, indent=2))
    elif dataset == "yorulect":
        # Print the first .tsv we find under standard/.
        std = RAW_DIR / "yorulect" / "standard"
        first_tsv = sorted(std.glob("*.tsv"))[0]
        print(f"[sample] yorulect standard/{first_tsv.name} (head -3):")
        with open(first_tsv, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 3:
                    break
                print(line.rstrip())
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/test_seed_cli.py -v
```

Expected: all pass (12 prior + 3 new). One subtlety: the IgboAPI download writes to `RAW_DIR / "igbo_api.json"`, but other datasets write to `RAW_DIR / <dataset> / *.json`. Adjust the IgboAPI download to also create a subfolder in Task 8 if you want consistency — but for now `_do_sample` matches the existing behavior.

If a test fails because `igbo_api.download` writes to `raw_dir / "igbo_api.json"` (not `raw_dir / "igbo_api" / "igbo_api.json"`), update Task 8's `download` to use `raw_dir / "igbo_api" / "igbo_api.json"` for symmetry. Update `transform` and `_do_sample` to match.

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/seed.py scripts/seed/tests/test_seed_cli.py
git commit -m "wire seed.py dispatch with gate checks for load subcommand"
```

---

## Task 15: `seed.py` — `all` orchestration

**Files:**
- Modify: `scripts/seed/seed.py`
- Modify: `scripts/seed/tests/test_seed_cli.py`

- [ ] **Step 1: Add failing tests**

```python
def test_all_truncate_path_calls_truncate_then_loads_all_in_order(monkeypatch, tmp_path):
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        (tmp_path / f"{ds}_clean.csv").write_text(
            "headword,pos,dialect_id,jsonb_data\n", encoding="utf-8"
        )
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("seed.RAW_DIR", tmp_path)
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)
    truncate = MagicMock()
    monkeypatch.setattr("seed.db.truncate_all", truncate)

    call_order = []
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        monkeypatch.setattr(
            f"loaders.{ds}.download",
            lambda raw, _ds=ds: call_order.append(("download", _ds))
        )
        monkeypatch.setattr(
            f"loaders.{ds}.transform",
            lambda raw, clean, _ds=ds: (call_order.append(("transform", _ds)), tmp_path / f"{_ds}_clean.csv")[1]
        )
        monkeypatch.setattr(
            f"loaders.{ds}.load",
            lambda csv, conn, _ds=ds: (call_order.append(("load", _ds)), 100)[1]
        )

    rc = seed.main(["all", "--truncate"])
    assert rc == 0
    truncate.assert_called_once()
    loads = [ds for action, ds in call_order if action == "load"]
    assert loads == ["igbo_api", "yorulect", "voa_ner", "naijasenti"]


def test_all_abort_if_not_empty_refuses_when_table_has_rows(monkeypatch):
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 1)
    rc = seed.main(["all", "--abort-if-not-empty"])
    assert rc == 1


def test_all_stops_on_first_failure(monkeypatch, tmp_path):
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        (tmp_path / f"{ds}_clean.csv").write_text(
            "headword,pos,dialect_id,jsonb_data\n", encoding="utf-8"
        )
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("seed.RAW_DIR", tmp_path)
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)
    monkeypatch.setattr("seed.db.truncate_all", MagicMock())

    called = []
    monkeypatch.setattr("loaders.igbo_api.download", lambda raw: called.append("d_ia"))
    monkeypatch.setattr("loaders.igbo_api.transform",
                        lambda raw, clean: tmp_path / "igbo_api_clean.csv")
    monkeypatch.setattr("loaders.igbo_api.load",
                        lambda csv, conn: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("loaders.yorulect.download", lambda raw: called.append("d_yl"))

    rc = seed.main(["all", "--truncate"])
    assert rc == 1
    assert "d_ia" in called
    assert "d_yl" not in called
```

- [ ] **Step 2: Run failing**

Expected: `AssertionError: unhandled command: all`.

- [ ] **Step 3: Add `_do_all` to `scripts/seed/seed.py`**

```python
from config import DATASET_ORDER


def _do_all(args) -> int:
    conn = db.connect()
    try:
        if args.abort_if_not_empty and db.entries_row_count(conn) > 0:
            print("[all] refusing: entries table is not empty", file=sys.stderr)
            return 1
        if args.truncate:
            print("[all] truncating entries and metadata")
            db.truncate_all(conn)

        summary: list[dict] = []
        for ds in DATASET_ORDER:
            print(f"\n=== {ds} ===")
            try:
                LOADERS[ds].download(RAW_DIR)
                csv_path = LOADERS[ds].transform(RAW_DIR, CLEAN_DIR)
                inserted = LOADERS[ds].load(csv_path, conn)
                summary.append({"dataset": ds, "inserted": inserted})
            except Exception as e:
                print(f"[all] {ds} failed: {e}", file=sys.stderr)
                return 1

        print("\n=== Summary ===")
        for row in summary:
            print(f"  {row['dataset']:<12} inserted {row['inserted']}")
        return 0
    finally:
        conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```powershell
python -m pytest scripts/seed/tests/test_seed_cli.py -v
```

Expected: all PASS (15 prior + 3 new).

- [ ] **Step 5: Commit**

```powershell
git add scripts/seed/seed.py scripts/seed/tests/test_seed_cli.py
git commit -m "implement seed.py all subcommand: truncate, ordered loads, halt on failure"
```

---

## Task 16: Per-dataset summary output (sampled / inserted / dropped / underflow)

**Files:**
- Modify: `scripts/seed/db.py` (add `LoadResult`, change `load_csv` return)
- Modify: each loader (`load()` returns `LoadResult`; YorùLect writes/reads underflow sidecar)
- Modify: `scripts/seed/seed.py` (`_do_all` prints new summary + Underflow detail)
- Modify: tests across all of the above

This upgrades the summary to match spec §9 exactly:

```
  igbo_api:    sampled 1000, inserted 1000 (0 dropped, 0 underflow)
  yorulect:    sampled 953,  inserted 953  (0 dropped, 47 underflow on ife)
  voa_ner:     sampled 750,  inserted 750  (0 dropped, 0 underflow)
  naijasenti:  sampled 1750, inserted 1745 (5 dropped: empty headword, 0 underflow)

Underflow detail:
  yorulect / ife:   target 250, available 203 (47 short)
```

- [ ] **Step 1: Add `LoadResult` and change `db.load_csv` signature**

Add to `scripts/seed/db.py` (before `_PAIRED_INSERT_SQL`):

```python
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class LoadResult:
    """Per-dataset outcome surfaced by each loader's load() function.

    Fields:
        dataset: short name (e.g. "igbo_api")
        sampled: rows in the clean CSV before inserts
        inserted: rows actually written to entries+metadata
        dropped_reasons: list of reason strings (one per dropped row, may repeat)
        underflow: {dialect_name: (available, target)} for sources that
                   couldn't hit per-dialect quotas
    """
    dataset: str
    sampled: int
    inserted: int
    dropped_reasons: list[str] = field(default_factory=list)
    underflow: dict[str, tuple[int, int]] = field(default_factory=dict)

    def format_line(self) -> str:
        dropped_n = self.sampled - self.inserted
        if dropped_n == 0:
            dropped_part = "0 dropped"
        else:
            distinct_reasons = ", ".join(Counter(self.dropped_reasons).keys())
            dropped_part = f"{dropped_n} dropped: {distinct_reasons}"

        if not self.underflow:
            uf_part = "0 underflow"
        else:
            shortfalls = []
            for name, (avail, target) in self.underflow.items():
                shortfalls.append(f"{target - avail} underflow on {name}")
            uf_part = ", ".join(shortfalls)

        return (f"  {self.dataset:<12} sampled {self.sampled:>5}, "
                f"inserted {self.inserted:>5}  ({dropped_part}, {uf_part})")
```

Replace the body of `db.load_csv` (do **not** change function name):

```python
def load_csv(csv_path, conn) -> tuple[int, int, list[str]]:
    """Insert every row of csv_path into entries+metadata in a single transaction.

    Returns (sampled, inserted, dropped_reasons). `with conn:` commits on
    clean exit and rolls back on exception.
    """
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8")
    sampled = len(df)
    inserted = 0
    dropped: list[str] = []
    with conn:
        with conn.cursor() as cur:
            for row in df.itertuples(index=False):
                if not row.headword or not str(row.headword).strip():
                    dropped.append("empty headword")
                    continue
                cur.execute(
                    _PAIRED_INSERT_SQL,
                    (row.headword, row.pos, int(row.dialect_id), row.jsonb_data),
                )
                inserted += 1
    return sampled, inserted, dropped
```

- [ ] **Step 2: Update `db.load_csv` tests**

Edit `scripts/seed/tests/test_db.py`. The two existing tests:

```python
def test_load_csv_executes_paired_insert(tmp_path):
    # ...build the 2-row CSV as before...
    sampled, inserted, dropped = db.load_csv(csv_path, fake_conn)
    assert sampled == 2
    assert inserted == 2
    assert dropped == []
    assert cur.execute.call_count == 2
    # (rest of SQL/params assertions unchanged)


def test_load_csv_drops_null_headword_rows(tmp_path):
    # ...build the 2-row CSV with one empty headword as before...
    sampled, inserted, dropped = db.load_csv(csv_path, fake_conn)
    assert sampled == 2
    assert inserted == 1
    assert dropped == ["empty headword"]
```

Add a test for `LoadResult.format_line`:

```python
def test_load_result_format_line_no_drops_no_underflow():
    r = db.LoadResult(dataset="igbo_api", sampled=1000, inserted=1000)
    assert "sampled  1000" in r.format_line()
    assert "0 dropped" in r.format_line()
    assert "0 underflow" in r.format_line()


def test_load_result_format_line_with_drops_and_underflow():
    r = db.LoadResult(
        dataset="yorulect",
        sampled=953,
        inserted=950,
        dropped_reasons=["empty headword", "empty headword", "empty headword"],
        underflow={"ife": (203, 250)},
    )
    line = r.format_line()
    assert "3 dropped: empty headword" in line
    assert "47 underflow on ife" in line
```

- [ ] **Step 3: Update each loader's `load()` to return `LoadResult`**

Replace `load` in `scripts/seed/loaders/igbo_api.py`:

```python
def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    return db.LoadResult(
        dataset="igbo_api",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
    )
```

Same pattern in `voa_ner.py` (dataset="voa_ner") and `naijasenti.py` (dataset="naijasenti").

For YorùLect, also pipe through underflow. Modify `transform` to write a sidecar JSON next to the CSV:

```python
# in transform(), at the end before `return out`:
sidecar = clean_dir / "yorulect_underflow.json"
sidecar.write_text(json.dumps(underflow, ensure_ascii=False), encoding="utf-8")
```

And modify `load`:

```python
def load(csv_path: Path, conn) -> "db.LoadResult":
    sampled, inserted, reasons = db.load_csv(csv_path, conn)
    sidecar = Path(csv_path).parent / "yorulect_underflow.json"
    underflow_raw = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    # JSON loses tuples, restore (avail, target):
    underflow = {k: tuple(v) for k, v in underflow_raw.items()}
    return db.LoadResult(
        dataset="yorulect",
        sampled=sampled,
        inserted=inserted,
        dropped_reasons=reasons,
        underflow=underflow,
    )
```

- [ ] **Step 4: Update each loader's `test_load_*` test**

Each loader test gets one new test (replacing the old delegation test):

```python
# loaders/test_igbo_api.py — replace test_load_delegates_to_db_load_csv with:
def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "igbo_api_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.igbo_api.db.load_csv", return_value=(10, 9, ["empty headword"])):
        result = igbo_api.load(csv_path, fake_conn)
    assert result.dataset == "igbo_api"
    assert result.sampled == 10
    assert result.inserted == 9
    assert result.dropped_reasons == ["empty headword"]
    assert result.underflow == {}
```

For YorùLect, add a test that the sidecar is read:

```python
def test_load_reads_underflow_sidecar(tmp_path):
    csv_path = tmp_path / "yorulect_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    sidecar = tmp_path / "yorulect_underflow.json"
    sidecar.write_text('{"ife": [203, 250]}', encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.yorulect.db.load_csv", return_value=(950, 950, [])):
        result = yorulect.load(csv_path, fake_conn)
    assert result.underflow == {"ife": (203, 250)}
```

Add to YorùLect transform tests:

```python
def test_transform_writes_underflow_sidecar(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=250)
    sidecar = tmp_path / "clean" / "yorulect_underflow.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    # ife fixture has 2 unique sentences; with cap=250 it underflows.
    assert data["ife"] == [2, 250]
```

- [ ] **Step 5: Update `_do_all` to print summary and Underflow detail**

In `scripts/seed/seed.py`, replace the inline summary print with:

```python
print("\n=== Summary ===")
print(f"Datasets loaded:  {', '.join(r.dataset for r in summary)}")
print(f"Total entries:    {sum(r.inserted for r in summary)}")
print()
print("Per-dataset:")
for r in summary:
    print(r.format_line())

# Underflow detail subsection
underflow_rows: list[tuple[str, str, int, int]] = []
for r in summary:
    for name, (avail, target) in r.underflow.items():
        underflow_rows.append((r.dataset, name, avail, target))
if underflow_rows:
    print()
    print("Underflow detail:")
    for ds, name, avail, target in underflow_rows:
        short = target - avail
        print(f"  {ds} / {name}:   target {target}, available {avail} ({short} short)")
```

`summary` now collects `LoadResult`s, so update the loop:

```python
summary: list[db.LoadResult] = []
for ds in DATASET_ORDER:
    print(f"\n=== {ds} ===")
    try:
        LOADERS[ds].download(RAW_DIR)
        csv_path = LOADERS[ds].transform(RAW_DIR, CLEAN_DIR)
        result = LOADERS[ds].load(csv_path, conn)
        summary.append(result)
    except Exception as e:
        print(f"[all] {ds} failed: {e}", file=sys.stderr)
        return 1
```

- [ ] **Step 6: Add a CLI test for the Underflow detail subsection**

Add to `scripts/seed/tests/test_seed_cli.py`:

```python
def test_all_summary_includes_underflow_detail(monkeypatch, tmp_path, capsys):
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        (tmp_path / f"{ds}_clean.csv").write_text(
            "headword,pos,dialect_id,jsonb_data\n", encoding="utf-8"
        )
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("seed.RAW_DIR", tmp_path)
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)
    monkeypatch.setattr("seed.db.truncate_all", MagicMock())

    def make_result(ds, underflow=None):
        return db.LoadResult(
            dataset=ds, sampled=100, inserted=100,
            underflow=underflow or {},
        )

    for ds in ("igbo_api", "voa_ner", "naijasenti"):
        monkeypatch.setattr(f"loaders.{ds}.download", lambda raw: None)
        monkeypatch.setattr(f"loaders.{ds}.transform",
                            lambda raw, clean, _ds=ds: tmp_path / f"{_ds}_clean.csv")
        monkeypatch.setattr(f"loaders.{ds}.load",
                            lambda csv, conn, _ds=ds: make_result(_ds))
    monkeypatch.setattr("loaders.yorulect.download", lambda raw: None)
    monkeypatch.setattr("loaders.yorulect.transform",
                        lambda raw, clean: tmp_path / "yorulect_clean.csv")
    monkeypatch.setattr("loaders.yorulect.load",
                        lambda csv, conn: make_result("yorulect", {"ife": (203, 250)}))

    rc = seed.main(["all", "--truncate"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Underflow detail:" in out
    assert "yorulect / ife" in out
    assert "47 short" in out
```

- [ ] **Step 7: Run all tests**

```powershell
python -m pytest scripts/seed/tests/ -v
```

Expected: full suite green.

- [ ] **Step 8: Commit**

```powershell
git add scripts/seed/db.py scripts/seed/seed.py scripts/seed/loaders/ scripts/seed/tests/
git commit -m "track sampled/inserted/dropped/underflow per dataset in summary"
```

---

## Task 17: Write the runbook (`scripts/seed/README.md`)

**Files:**
- Create: `scripts/seed/README.md`

- [ ] **Step 1: Create `scripts/seed/README.md`**

Content matches the spec's §10 verbatim, including the corrected "first dataset uses --abort-if-not-empty, subsequent loads do not" guidance and the three-recovery "When things break" section. Use this content:

```markdown
# Seed Pipeline Runbook

Python sub-project that loads four upstream datasets into the Railway
Postgres `entries` and `metadata` tables. See the design spec at
[../../docs/superpowers/specs/2026-05-09-data-seeding-design.md](../../docs/superpowers/specs/2026-05-09-data-seeding-design.md).

## First-time setup

```powershell
python -m venv .venv
.\.venv\Scripts\activate              # Windows; source .venv/bin/activate on POSIX
pip install -r requirements.txt
python scripts/seed/seed.py preflight
```

## One-at-a-time first run

`--abort-if-not-empty` checks the *whole* `entries` table, so it only
fits on the first dataset. Subsequent loads rely on the always-on
source-tag gate (refuses if this dataset's `SOURCE_TAG` already has rows
in `metadata`) to prevent double-loading.

```powershell
# Dataset 1: validates the table starts empty.
python scripts/seed/seed.py download igbo_api
python scripts/seed/seed.py sample   igbo_api          # eyeball one raw entry
python scripts/seed/seed.py transform igbo_api
python scripts/seed/seed.py load     igbo_api --abort-if-not-empty

# Datasets 2-4: source-tag gate is always on.
python scripts/seed/seed.py download yorulect
python scripts/seed/seed.py sample   yorulect
python scripts/seed/seed.py transform yorulect
python scripts/seed/seed.py load     yorulect

python scripts/seed/seed.py download voa_ner
python scripts/seed/seed.py sample   voa_ner
python scripts/seed/seed.py transform voa_ner
python scripts/seed/seed.py load     voa_ner

python scripts/seed/seed.py download naijasenti
python scripts/seed/seed.py sample   naijasenti
python scripts/seed/seed.py transform naijasenti
python scripts/seed/seed.py load     naijasenti

python scripts/seed/seed.py verify
```

## Re-run from scratch

```powershell
python scripts/seed/seed.py all --truncate
python scripts/seed/seed.py verify
```

## When things break

1. **`gdown` failure on YorùLect.** The Drive link printed in the error
   is the same one the README scrapes. Open it in a browser, download
   the folder manually into `raw/yorulect/`, then re-run
   `python scripts/seed/seed.py transform yorulect`. The download step
   is the only one that touches Drive; everything downstream reads from
   `raw/`.

2. **Mid-dataset INSERT failure.** The whole dataset's transaction
   rolls back, so the DB is in the state it was in before the dataset
   started. Read the printed psycopg2 error and the offending row, fix
   the underlying cause (usually a malformed JSONB or an unexpected
   character in `headword`), then re-run `load <dataset>` for just
   that dataset — the prior datasets stay intact.

3. **Dialect ID mismatch.** Preflight printed a diff between the map in
   `config.py` and the `dialects` table. If the table is wrong, fix it
   in Railway. If the map is wrong, edit `config.py` and re-run
   preflight. Do **not** transform or load until preflight passes
   cleanly.

## Subcommand reference

| Subcommand | Purpose |
|------------|---------|
| `preflight` | Connection + UTF8 + dialect map + row counts |
| `download <dataset>` | Pull raw data into `raw/<dataset>/` |
| `sample <dataset>` | Print one raw entry; read-only |
| `transform <dataset>` | Read `raw/`, write `clean/<dataset>_clean.csv` |
| `load <dataset>` | Insert the clean CSV in one transaction |
| `all --truncate` | TRUNCATE + run all four datasets in order |
| `all --abort-if-not-empty` | Refuse if non-empty + run all four |
| `verify` | Print breakdown; exit 1 if entries empty |
```

- [ ] **Step 2: Commit**

```powershell
git add scripts/seed/README.md
git commit -m "add seed pipeline runbook with three recovery paths"
```

---

## Task 18: End-to-end smoke test against Railway

**Files:**
- No new code; this is a manual verification task using the real DB.

This is the integration check that ties everything together. The unit tests in tasks 2-15 mock all network and DB calls; this task runs the real pipeline against the live Railway database.

- [ ] **Step 1: Confirm `.env` has `DATABASE_URL`**

```powershell
type .env | Select-String DATABASE_URL
```

Expected: a line `DATABASE_URL=postgresql://...`.

- [ ] **Step 2: Run preflight**

```powershell
python scripts/seed/seed.py preflight
```

Expected output includes `client_encoding = UTF8`, the 9-row dialect map matching the spec, and current row counts in `entries` and `metadata`. Exit 0.

If exit non-zero, fix per the runbook's "When things break" section before continuing.

- [ ] **Step 3: Run the one-at-a-time flow for the first dataset**

```powershell
python scripts/seed/seed.py download igbo_api
python scripts/seed/seed.py sample   igbo_api
```

Inspect the raw entry printed by `sample`. Confirm it has the expected shape (`word`, `wordClass`, `definitions`, `dialects`).

```powershell
python scripts/seed/seed.py transform igbo_api
python scripts/seed/seed.py load     igbo_api --abort-if-not-empty
```

If the entries table is empty, `load` succeeds. If the table is non-empty, the run aborts with a clear message — at that point either truncate (`all --truncate`) or skip ahead.

- [ ] **Step 4: Run remaining datasets**

```powershell
foreach ($ds in @("yorulect", "voa_ner", "naijasenti")) {
  python scripts/seed/seed.py download $ds
  python scripts/seed/seed.py sample   $ds
  python scripts/seed/seed.py transform $ds
  python scripts/seed/seed.py load     $ds
}
```

If any step fails, halt and follow the runbook's recovery guide before re-running just that step.

- [ ] **Step 5: Run verify**

```powershell
python scripts/seed/seed.py verify
```

Expected: a 9-row breakdown table with non-zero counts for each dialect that received data, plus `entries == metadata` row counts. Exit 0.

- [ ] **Step 6: Commit the four CSVs in `clean/`**

```powershell
git add clean/
git commit -m "commit deterministic clean CSVs as audit artifacts"
```

These CSVs are the reproducible record of what was loaded. The deterministic seed (42) means re-running the pipeline on the same upstream data produces the same files.

- [ ] **Step 7: Final all-tests pass**

```powershell
python -m pytest scripts/seed/tests/ -v
```

Expected: full suite green. The pipeline is ready to ship.

---

## Self-Review Notes

Mapped against the spec to confirm coverage:

- **§2 Database contract** → Task 2 (config), Task 5 (preflight verifies the map).
- **§3 Datasets and caps** → Tasks 7-12 implement each dataset's sampling rules with `random.Random(42)`.
- **§4 Repository layout** → Task 1.
- **§5 CLI surface (preflight, download, sample, transform, load, all, verify)** → Tasks 5, 6, 13, 14, 15.
- **§6.1 IgboAPI dialect map, dedup by (headword, dialect_id), all-minority sampling** → Task 7.
- **§6.2 YorùLect column choice, cross-file dedup, underflow** → Task 10.
- **§6.3 VOA NER token-join, ner_tags dropped** → Task 11.
- **§6.4 NaijaSenti per-language quotas (500/500/750), pcm skipped, int2str labels** → Task 12.
- **§7 Insert path, CTE, encoding, dropped-row policy** → Task 4.
- **§8 Failure modes** → Tasks 4 (rollback via `with conn:`), 5 (preflight), 9 (gdown fallback), 14 (gate checks).
- **§9 Summary format with sampled/inserted/dropped/underflow** → Task 16.
- **§10 Runbook including "When things break"** → Task 17.
- **§11 Stopping rules** → enforced by preflight (Task 5), per-dataset transactions (Task 4), and `_do_all`'s halt-on-failure (Task 15).
