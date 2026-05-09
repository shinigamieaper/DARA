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
