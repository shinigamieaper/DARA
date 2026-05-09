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
