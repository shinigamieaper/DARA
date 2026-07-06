import csv
import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import oriki


def _write_source(path, rows):
    fields = ["id", "name", "gender", "language", "praise_text",
              "meaning", "category", "keywords"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def test_transform_maps_oriki_to_praise_poetry(tmp_path, monkeypatch):
    src = tmp_path / "oriki_source.csv"
    _write_source(src, [
        {"id": "1", "name": "Ade", "gender": "male", "language": "yoruba",
         "praise_text": "Adé, ọmọ ọlọ́lá,\nAdé ọmọ akín", "meaning": "Child of royalty",
         "category": "royalty", "keywords": "brave;royal;crown"},
        {"id": "2", "name": "Sade", "gender": "female", "language": "yoruba",
         "praise_text": "Sadé, ọmọ ọlọ́lá", "meaning": "Princess of light",
         "category": "royalty", "keywords": "queen;light"},
    ])
    monkeypatch.setattr(oriki, "_SRC", src)

    out = oriki.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 2
    assert (df["pos"] == "praise_poetry").all()
    assert (df["dialect_id"] == "1").all()
    assert set(df["headword"]) == {"Ade", "Sade"}
    j = json.loads(df[df["headword"] == "Ade"].iloc[0]["jsonb_data"])
    assert j["source"] == "Oriki"
    assert j["genre"] == "praise_poetry"
    assert "ọmọ akín" in j["praise_text"]
    assert j["keywords"] == ["brave", "royal", "crown"]
    assert j["meaning"] == "Child of royalty"
    assert j["gender"] == "male"


def test_transform_dedups_by_praise_text(tmp_path, monkeypatch):
    src = tmp_path / "oriki_source.csv"
    _write_source(src, [
        {"id": "1", "name": "Ade", "gender": "male", "language": "yoruba",
         "praise_text": "same oriki text", "meaning": "m", "category": "c", "keywords": "k"},
        {"id": "2", "name": "Ade2", "gender": "male", "language": "yoruba",
         "praise_text": "same oriki text", "meaning": "m", "category": "c", "keywords": "k"},
        {"id": "3", "name": "Bola", "gender": "female", "language": "yoruba",
         "praise_text": "different", "meaning": "m", "category": "c", "keywords": "k"},
    ])
    monkeypatch.setattr(oriki, "_SRC", src)
    out = oriki.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 2  # duplicate praise text dropped


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "oriki_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.oriki.db.load_csv", return_value=(100, 100, [])):
        result = oriki.load(csv_path, fake_conn)
    assert result.dataset == "oriki"
    assert result.sampled == 100
    assert result.inserted == 100


def test_committed_oriki_source_is_valid():
    """The real committed oríkì source parses and is all Yoruba praise poetry."""
    assert oriki._SRC.exists()
    import csv as _csv
    with oriki._SRC.open(encoding="utf-8", newline="") as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) > 0
    assert all((r.get("praise_text") or "").strip() for r in rows)
    assert {r["language"] for r in rows} == {"yoruba"}
