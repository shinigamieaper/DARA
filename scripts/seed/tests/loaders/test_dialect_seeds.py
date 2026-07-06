import csv
import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import dialect_seeds


def _write_seed(dir_, name, rows):
    path = dir_ / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["headword", "pos", "dialect_id", "jsonb_data"])
        for hw, pos, did, jsonb in rows:
            w.writerow([hw, pos, did, json.dumps(jsonb, ensure_ascii=False)])
    return path


def test_transform_concatenates_all_seed_files(tmp_path, monkeypatch):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    _write_seed(seed_dir, "dialect_seed_sokoto_hausa.csv", [
        ("haure", "noun", 9, {"source": "Dialect Seed", "english_translation": "tooth"}),
        ("gambu", "noun", 9, {"source": "Dialect Seed", "english_translation": "door"}),
    ])
    _write_seed(seed_dir, "dialect_seed_example.csv", [
        ("xyz", "noun", 6, {"source": "Dialect Seed", "english_translation": "thing"}),
    ])
    monkeypatch.setattr(dialect_seeds, "_SEED_DIR", seed_dir)

    out = dialect_seeds.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 3
    assert list(df.columns) == ["headword", "pos", "dialect_id", "jsonb_data"]
    assert set(df["headword"]) == {"haure", "gambu", "xyz"}
    # jsonb survives the round-trip as valid JSON
    row = df[df["headword"] == "haure"].iloc[0]
    assert json.loads(row["jsonb_data"])["english_translation"] == "tooth"


def test_transform_writes_empty_csv_when_no_seed_files(tmp_path, monkeypatch):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    monkeypatch.setattr(dialect_seeds, "_SEED_DIR", seed_dir)

    out = dialect_seeds.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 0
    assert list(df.columns) == ["headword", "pos", "dialect_id", "jsonb_data"]


def test_download_is_noop_and_reports_files(tmp_path, monkeypatch, capsys):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    _write_seed(seed_dir, "dialect_seed_sokoto_hausa.csv", [
        ("haure", "noun", 9, {"source": "Dialect Seed"}),
    ])
    monkeypatch.setattr(dialect_seeds, "_SEED_DIR", seed_dir)

    dialect_seeds.download(tmp_path / "raw")
    out = capsys.readouterr().out
    assert "dialect_seed_sokoto_hausa.csv" in out


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "dialect_seeds_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.dialect_seeds.db.load_csv", return_value=(24, 24, [])):
        result = dialect_seeds.load(csv_path, fake_conn)
    assert result.dataset == "dialect_seeds"
    assert result.sampled == 24
    assert result.inserted == 24


def test_committed_sokoto_seed_is_valid():
    """The real committed Sokoto Hausa seed parses and is dialect_id 9."""
    seed_file = dialect_seeds._SEED_DIR / "dialect_seed_sokoto_hausa.csv"
    assert seed_file.exists()
    df = pd.read_csv(seed_file, dtype=str, keep_default_na=False)
    assert len(df) > 0
    assert set(df["dialect_id"]) == {"9"}
    for raw in df["jsonb_data"]:
        j = json.loads(raw)
        assert j["source"] == "Dialect Seed"
        assert j["origin"]  # every row cites its source
        assert j["english_translation"]
