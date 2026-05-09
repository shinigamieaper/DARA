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
