import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from loaders import igbo_api


FIXTURE = Path(__file__).parent.parent / "fixtures" / "igbo_api_sample.json"


def test_transform_entry_uses_central_default_when_no_dialect():
    raw = {"word": "isi", "wordClass": "noun", "definitions": ["head"],
           "examples": [], "dialects": []}
    headword, pos, dialect_id, jsonb = igbo_api.transform_entry(raw)
    assert headword == "isi"
    assert pos == "noun"
    assert dialect_id == 5
    assert jsonb["source"] == "IgboAPI"
    assert jsonb["definitions"] == ["head"]
    assert jsonb["dialect_variants"] == []


def test_transform_entry_maps_ehugbo_to_6():
    raw = {"word": "ulo", "wordClass": "noun", "definitions": ["house"],
           "examples": [], "dialects": ["Ehugbo"]}
    _, _, dialect_id, jsonb = igbo_api.transform_entry(raw)
    assert dialect_id == 6
    assert jsonb["dialect_variants"] == ["Ehugbo"]


def test_transform_entry_maps_enuani_to_7():
    raw = {"word": "mmiri", "wordClass": "noun", "definitions": ["water"],
           "examples": [], "dialects": ["Enuani"]}
    _, _, dialect_id, _ = igbo_api.transform_entry(raw)
    assert dialect_id == 7


def test_transform_entry_defaults_pos_to_unknown_when_missing():
    raw = {"word": "anya", "definitions": ["eye"], "examples": [], "dialects": []}
    _, pos, _, _ = igbo_api.transform_entry(raw)
    assert pos == "unknown"


def test_transform_keeps_all_minority_and_caps_central(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    # 3 Central, 1 Ehugbo, 1 Enuani; cap=3 means keep 1 Ehugbo + 1 Enuani + sample 1 from 3 Central.
    entries = (
        [{"word": f"central_{i}", "wordClass": "noun", "definitions": [],
          "examples": [], "dialects": []} for i in range(3)]
        + [{"word": "ulo", "wordClass": "noun", "definitions": [],
            "examples": [], "dialects": ["Ehugbo"]}]
        + [{"word": "mmiri", "wordClass": "noun", "definitions": [],
            "examples": [], "dialects": ["Enuani"]}]
    )
    (raw_dir / "igbo_api.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = igbo_api.transform(raw_dir, tmp_path / "clean", cap=3)

    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 3
    assert (df["dialect_id"] == "6").sum() == 1
    assert (df["dialect_id"] == "7").sum() == 1
    assert (df["dialect_id"] == "5").sum() == 1


def test_transform_dedups_by_headword_and_dialect(tmp_path):
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    entries = [
        {"word": "akwa", "wordClass": "noun", "definitions": ["cloth"],
         "examples": [], "dialects": []},
        {"word": "akwa", "wordClass": "noun", "definitions": ["egg"],
         "examples": [], "dialects": []},
        {"word": "akwa", "wordClass": "noun", "definitions": ["different"],
         "examples": [], "dialects": ["Ehugbo"]},
    ]
    (raw_dir / "igbo_api.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = igbo_api.transform(raw_dir, tmp_path / "clean", cap=10)

    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 2
    assert set(df["dialect_id"]) == {"5", "6"}


def test_transform_uses_fixture_file_to_produce_csv():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        raw = td / "raw"
        raw.mkdir()
        (raw / "igbo_api.json").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        csv_path = igbo_api.transform(raw, td / "clean", cap=10)
        df = pd.read_csv(csv_path, dtype=str)
        # akwa/5, akwa/6, ulo/6, mmiri/7, anya/5, isi/5  -> 6 unique (headword, dialect_id) tuples
        assert len(df) == 6
        assert "headword" in df.columns
        assert "pos" in df.columns
        assert "dialect_id" in df.columns
        assert "jsonb_data" in df.columns


def test_download_uses_hf_dataset_first(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_ds = MagicMock()
    fake_ds["train"].to_list.return_value = [{"word": "x", "wordClass": "n",
                                              "definitions": [], "examples": [], "dialects": []}]
    with patch("loaders.igbo_api.hf_load_dataset", return_value=fake_ds) as load_ds:
        igbo_api.download(raw_dir)
    load_ds.assert_called_once_with("nkowaokwu/igbo_api")
    assert (raw_dir / "igbo_api.json").exists()


def test_download_falls_back_to_github_on_hf_failure(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_response = MagicMock()
    fake_response.json.return_value = [{"word": "x", "wordClass": "n",
                                        "definitions": [], "examples": [], "dialects": []}]
    fake_response.raise_for_status.return_value = None
    with patch("loaders.igbo_api.hf_load_dataset", side_effect=RuntimeError("HF down")), \
         patch("loaders.igbo_api.requests.get", return_value=fake_response) as get:
        igbo_api.download(raw_dir)
    assert get.called
    assert (raw_dir / "igbo_api.json").exists()


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "igbo_api_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.igbo_api.db.load_csv", return_value=42) as load_csv:
        result = igbo_api.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 42
