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
