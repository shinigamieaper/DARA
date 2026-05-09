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
