"""Database access layer for the seed pipeline."""
import os
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
                headword_str = str(row.headword).strip()
                if not headword_str or headword_str == "nan":
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
