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


def test_load_csv_batches_paired_insert(tmp_path):
    csv_path = tmp_path / "sample_clean.csv"
    pd.DataFrame([
        {"headword": "akwa", "pos": "noun", "dialect_id": "5",
         "jsonb_data": json.dumps({"source": "IgboAPI"})},
        {"headword": "ulo", "pos": "noun", "dialect_id": "6",
         "jsonb_data": json.dumps({"source": "IgboAPI"})},
    ]).to_csv(csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn

    with patch("db.execute_batch") as eb:
        sampled, inserted, dropped = db.load_csv(csv_path, fake_conn)

    assert sampled == 2
    assert inserted == 2
    assert dropped == []
    # One batched call carrying both rows' params.
    eb.assert_called_once()
    _, sql, params = eb.call_args.args[0], eb.call_args.args[1], eb.call_args.args[2]
    assert "WITH new_entry AS" in sql
    assert "INSERT INTO entries" in sql
    assert "INSERT INTO metadata" in sql
    assert params[0] == ("akwa", "noun", 5, '{"source": "IgboAPI"}')
    assert len(params) == 2


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

    with patch("db.execute_batch") as eb:
        sampled, inserted, dropped = db.load_csv(csv_path, fake_conn)

    assert sampled == 2
    assert inserted == 1
    assert dropped == ["empty headword"]
    params = eb.call_args.args[2]
    assert len(params) == 1


def test_load_csv_keeps_row_whose_headword_is_literally_nan(tmp_path):
    """A real headword 'nan' must NOT be dropped — only truly empty cells should be."""
    csv_path = tmp_path / "sample_clean.csv"
    pd.DataFrame([
        {"headword": "nan", "pos": "noun", "dialect_id": "5",
         "jsonb_data": '{"source": "IgboAPI"}'},
    ]).to_csv(csv_path, index=False, encoding="utf-8", quoting=csv.QUOTE_ALL)

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn

    with patch("db.execute_batch") as eb:
        sampled, inserted, dropped = db.load_csv(csv_path, fake_conn)

    assert sampled == 1
    assert inserted == 1
    assert dropped == []
    params = eb.call_args.args[2]
    assert len(params) == 1
    assert params[0][0] == "nan"


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


def test_load_result_format_line_no_drops_no_underflow():
    r = db.LoadResult(dataset="igbo_api", sampled=1000, inserted=1000)
    line = r.format_line()
    assert "sampled  1000" in line
    assert "0 dropped" in line
    assert "0 underflow" in line


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
