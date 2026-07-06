import csv
import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import oriki


def _write_source(seed_dir, filename, rows):
    fields = ["id", "name", "gender", "language", "praise_text",
              "meaning", "category", "keywords"]
    path = seed_dir / filename
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def test_transform_maps_praise_and_language_to_dialect(tmp_path, monkeypatch):
    seed = tmp_path / "seed_data"
    seed.mkdir()
    _write_source(seed, "oriki_source.csv", [
        {"id": "1", "name": "Ade", "gender": "male", "language": "yoruba",
         "praise_text": "Adé, ọmọ ọlọ́lá,\nAdé ọmọ akín", "meaning": "Child of royalty",
         "category": "royalty", "keywords": "brave;royal"},
    ])
    _write_source(seed, "oriki_source_igbo.csv", [
        {"id": "1", "name": "Chinedu", "gender": "male", "language": "igbo",
         "praise_text": "Nwa amadi ike", "meaning": "Strong child",
         "category": "strength", "keywords": "power"},
    ])
    _write_source(seed, "oriki_source_hausa.csv", [
        {"id": "1", "name": "Musa", "gender": "male", "language": "hausa",
         "praise_text": "Jarumi mai karfi", "meaning": "Strong hero",
         "category": "warrior", "keywords": "strength"},
    ])
    monkeypatch.setattr(oriki, "_SEED_DIR", seed)

    out = oriki.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 3
    assert (df["pos"] == "praise_poetry").all()
    # language -> dialect mapping: yoruba=1, igbo=5, hausa=8
    by_hw = {r["headword"]: r for _, r in df.iterrows()}
    assert by_hw["Ade"]["dialect_id"] == "1"
    assert by_hw["Chinedu"]["dialect_id"] == "5"
    assert by_hw["Musa"]["dialect_id"] == "8"
    j = json.loads(by_hw["Chinedu"]["jsonb_data"])
    assert j["source"] == "Oriki"
    assert j["genre"] == "praise_poetry"
    assert j["language"] == "igbo"
    assert j["praise_text"] == "Nwa amadi ike"
    assert j["keywords"] == ["power"]


def test_transform_dedups_by_praise_text(tmp_path, monkeypatch):
    seed = tmp_path / "seed_data"
    seed.mkdir()
    _write_source(seed, "oriki_source.csv", [
        {"id": "1", "name": "Ade", "gender": "male", "language": "yoruba",
         "praise_text": "same text", "meaning": "m", "category": "c", "keywords": "k"},
        {"id": "2", "name": "Ade2", "gender": "male", "language": "yoruba",
         "praise_text": "same text", "meaning": "m", "category": "c", "keywords": "k"},
        {"id": "3", "name": "Bola", "gender": "female", "language": "yoruba",
         "praise_text": "different", "meaning": "m", "category": "c", "keywords": "k"},
    ])
    monkeypatch.setattr(oriki, "_SEED_DIR", seed)
    out = oriki.transform(tmp_path / "raw", tmp_path / "clean")
    df = pd.read_csv(out, dtype=str, keep_default_na=False)
    assert len(df) == 2


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "oriki_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.oriki.db.load_csv", return_value=(120, 120, [])):
        result = oriki.load(csv_path, fake_conn)
    assert result.dataset == "oriki"
    assert result.sampled == 120
    assert result.inserted == 120


def test_committed_praise_sources_cover_three_languages():
    """The committed oríkì sources parse and span Yoruba, Igbo, and Hausa."""
    files = oriki._source_files()
    assert files, "expected committed oriki_source*.csv files"
    langs = set()
    for src in files:
        with src.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if (r.get("praise_text") or "").strip():
                    langs.add((r.get("language") or "").strip().lower())
    assert {"yoruba", "igbo", "hausa"} <= langs
