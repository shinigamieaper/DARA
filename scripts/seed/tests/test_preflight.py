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
