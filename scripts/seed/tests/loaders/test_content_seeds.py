import csv
import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import content_seeds


def _write_seed(dir_, name, rows):
    path = dir_ / name
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["headword", "pos", "dialect_id", "jsonb_data"])
        for hw, pos, did, jsonb in rows:
            w.writerow([hw, pos, did, json.dumps(jsonb, ensure_ascii=False)])
    return path


def test_source_tag_matches_config():
    assert content_seeds.SOURCE_TAG == "Content Seed"


def test_transform_concatenates_all_seed_files(tmp_path, monkeypatch):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    _write_seed(seed_dir, "content_seed_praise_poetry.csv", [
        ("Ọmọ kùnrin", "praise_poetry", 1, {"source": "Content Seed", "english_translation": "male child"}),
        ("Akin", "praise_poetry", 1, {"source": "Content Seed", "english_translation": "brave one"}),
    ])
    _write_seed(seed_dir, "content_seed_folktale.csv", [
        ("Ijapa", "folktale", 5, {"source": "Content Seed", "english_translation": "tortoise"}),
    ])
    monkeypatch.setattr(content_seeds, "_SEED_DIR", seed_dir)

    out = content_seeds.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 3
    assert list(df.columns) == ["headword", "pos", "dialect_id", "jsonb_data"]
    assert set(df["headword"]) == {"Ọmọ kùnrin", "Akin", "Ijapa"}
    row = df[df["headword"] == "Ijapa"].iloc[0]
    assert json.loads(row["jsonb_data"])["english_translation"] == "tortoise"


def test_transform_writes_empty_csv_when_no_seed_files(tmp_path, monkeypatch):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    monkeypatch.setattr(content_seeds, "_SEED_DIR", seed_dir)

    out = content_seeds.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 0
    assert list(df.columns) == ["headword", "pos", "dialect_id", "jsonb_data"]


def test_download_is_noop_and_reports_files(tmp_path, monkeypatch, capsys):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    _write_seed(seed_dir, "content_seed_praise_poetry.csv", [
        ("Akin", "praise_poetry", 1, {"source": "Content Seed"}),
    ])
    monkeypatch.setattr(content_seeds, "_SEED_DIR", seed_dir)

    content_seeds.download(tmp_path / "raw")
    out = capsys.readouterr().out
    assert "content_seed_praise_poetry.csv" in out


def test_download_warns_when_no_seed_files(tmp_path, monkeypatch, capsys):
    seed_dir = tmp_path / "seed_data"
    seed_dir.mkdir()
    monkeypatch.setattr(content_seeds, "_SEED_DIR", seed_dir)

    content_seeds.download(tmp_path / "raw")
    out = capsys.readouterr().out
    assert "WARN" in out


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "content_seeds_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.content_seeds.db.load_csv", return_value=(12, 12, [])):
        result = content_seeds.load(csv_path, fake_conn)
    assert result.dataset == "content_seeds"
    assert result.sampled == 12
    assert result.inserted == 12
