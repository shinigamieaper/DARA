import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from loaders import voa_ner


def test_transform_entry_joins_tokens_and_marks_default_dialect():
    raw = {"tokens": ["Sannu", "duniya", "."], "ner_tags": [0, 0, 0], "split": "train"}
    headword, pos, dialect_id, jsonb = voa_ner.transform_entry(raw)
    assert headword == "Sannu duniya ."
    assert pos == "sentence"
    assert dialect_id == 8
    assert jsonb == {"source": "VOA Hausa", "split": "train",
                     "dialect_assigned_default": True}


def test_transform_entry_drops_ner_tags():
    raw = {"tokens": ["a", "b"], "ner_tags": [1, 2], "split": "test"}
    *_, jsonb = voa_ner.transform_entry(raw)
    assert "ner_tags" not in jsonb


def test_transform_dedups_and_caps(tmp_path):
    raw_dir = tmp_path / "raw" / "voa_ner"
    raw_dir.mkdir(parents=True)
    entries = [
        {"tokens": ["sentence", str(i)], "ner_tags": [0, 0], "split": "train"}
        for i in range(20)
    ] + [
        {"tokens": ["dup"], "ner_tags": [0], "split": "train"},
        {"tokens": ["dup"], "ner_tags": [0], "split": "test"},  # duplicate, dropped
    ]
    (raw_dir / "voa_ner.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = voa_ner.transform(raw_dir.parent, tmp_path / "clean", cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 10
    assert df["headword"].is_unique
    assert (df["dialect_id"] == "8").all()


def test_download_pulls_all_three_splits(tmp_path):
    raw_dir = tmp_path / "raw" / "voa_ner"
    fake_ds = {
        "train":      [{"tokens": ["a"], "ner_tags": [0]}],
        "validation": [{"tokens": ["b"], "ner_tags": [0]}],
        "test":       [{"tokens": ["c"], "ner_tags": [0]}],
    }

    def fake_load_dataset(name, split=None):
        m = MagicMock()
        m.to_list.return_value = list(fake_ds[split])
        return m

    with patch("loaders.voa_ner.hf_load_dataset", side_effect=fake_load_dataset):
        voa_ner.download(raw_dir.parent)

    out = json.loads((raw_dir / "voa_ner.json").read_text(encoding="utf-8"))
    splits = {row["split"] for row in out}
    assert splits == {"train", "validation", "test"}


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "voa_ner_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.voa_ner.db.load_csv", return_value=5) as load_csv:
        result = voa_ner.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 5
