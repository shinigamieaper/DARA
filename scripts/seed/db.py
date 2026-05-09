"""Database access layer for the seed pipeline."""
import os
from collections import Counter
from dataclasses import dataclass, field
import psycopg2
import pandas as pd
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


_PAIRED_INSERT_SQL = """
WITH new_entry AS (
  INSERT INTO entries (headword, pos, dialect_id)
  VALUES (%s, %s, %s)
  RETURNING entry_id
)
INSERT INTO metadata (entry_id, jsonb_data)
SELECT entry_id, %s::jsonb FROM new_entry
"""


def load_csv(csv_path, conn) -> tuple[int, int, list[str]]:
    """Insert every row of csv_path into entries+metadata in a single transaction.

    Returns (sampled, inserted, dropped_reasons). `with conn:` commits on
    clean exit and rolls back on exception.
    """
    df = pd.read_csv(csv_path, dtype=str, encoding="utf-8", keep_default_na=False)
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


def truncate_all(conn) -> None:
    """Truncate entries and metadata, resetting SERIAL counters."""
    with conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE entries, metadata RESTART IDENTITY CASCADE")
