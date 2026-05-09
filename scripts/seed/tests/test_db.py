from unittest.mock import MagicMock, patch
import pytest
import json
import csv
from pathlib import Path
import pandas as pd
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
