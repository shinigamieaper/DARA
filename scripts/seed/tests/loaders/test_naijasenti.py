import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pandas as pd
from loaders import naijasenti


def test_transform_entry_yor_maps_to_dialect_1():
    raw = {"tweet": "Mo nife re", "sentiment": "positive", "split": "train"}
    headword, pos, dialect_id, jsonb = naijasenti.transform_entry(raw, lang="yor")
    assert headword == "Mo nife re"
    assert pos == "sentence"
    assert dialect_id == 1
    assert jsonb == {"source": "NaijaSenti", "type": "tweet", "sentiment": "positive",
                     "split": "train", "dialect_assigned_default": True}


def test_transform_entry_ibo_maps_to_5():
    _, _, dialect_id, _ = naijasenti.transform_entry(
        {"tweet": "x", "sentiment": "neutral", "split": "test"}, lang="ibo"
    )
    assert dialect_id == 5


def test_transform_entry_hau_maps_to_8():
    _, _, dialect_id, _ = naijasenti.transform_entry(
        {"tweet": "y", "sentiment": "negative", "split": "validation"}, lang="hau"
    )
    assert dialect_id == 8


def test_transform_applies_per_language_quotas(tmp_path):
    raw_root = tmp_path / "raw" / "naijasenti"
    raw_root.mkdir(parents=True)
    payload = {
        "yor": [{"tweet": f"yor_{i}", "sentiment": "positive", "split": "train"}
                for i in range(800)],
        "ibo": [{"tweet": f"ibo_{i}", "sentiment": "neutral", "split": "train"}
                for i in range(800)],
        "hau": [{"tweet": f"hau_{i}", "sentiment": "negative", "split": "train"}
                for i in range(800)],
    }
    (raw_root / "naijasenti.json").write_text(json.dumps(payload), encoding="utf-8")

    csv_path = naijasenti.transform(
        raw_root.parent, tmp_path / "clean",
        quotas={"yor": 50, "ibo": 50, "hau": 75},
    )
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["dialect_id"] == "1").sum() == 50
    assert (df["dialect_id"] == "5").sum() == 50
    assert (df["dialect_id"] == "8").sum() == 75


def test_transform_dedups_within_language(tmp_path):
    raw_root = tmp_path / "raw" / "naijasenti"
    raw_root.mkdir(parents=True)
    payload = {
        "yor": [{"tweet": "same", "sentiment": "positive", "split": "train"},
                {"tweet": "same", "sentiment": "neutral", "split": "test"},
                {"tweet": "different", "sentiment": "positive", "split": "train"}],
        "ibo": [],
        "hau": [],
    }
    (raw_root / "naijasenti.json").write_text(json.dumps(payload), encoding="utf-8")

    csv_path = naijasenti.transform(
        raw_root.parent, tmp_path / "clean",
        quotas={"yor": 10, "ibo": 10, "hau": 10},
    )
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["dialect_id"] == "1").sum() == 2


def test_download_skips_pcm_and_resolves_int_labels(tmp_path):
    raw_root = tmp_path / "raw" / "naijasenti"

    class FakeFeatures:
        def __init__(self, label_names):
            self.label_names = label_names
            self.label = MagicMock()
            self.label.int2str = lambda i: label_names[i]
        def __getitem__(self, k):
            return self.label

    def fake_load_dataset(name, lang):
        assert lang in ("yor", "ibo", "hau")  # not pcm
        ds = MagicMock()
        ds.keys.return_value = ["train"]
        feats = FakeFeatures(["negative", "neutral", "positive"])

        def fake_split_iter():
            return iter([{"tweet": f"{lang}_t1", "label": 2},
                         {"tweet": f"{lang}_t2", "label": 0}])

        ds.__getitem__.return_value.features = feats
        ds.__getitem__.return_value.__iter__ = lambda _self: fake_split_iter()
        return ds

    with patch("loaders.naijasenti.hf_load_dataset", side_effect=fake_load_dataset) as load_ds:
        naijasenti.download(raw_root.parent)

    called_langs = [call.kwargs.get("lang") or call.args[1] for call in load_ds.call_args_list]
    assert "pcm" not in called_langs
    assert set(called_langs) == {"yor", "ibo", "hau"}
    payload = json.loads((raw_root / "naijasenti.json").read_text(encoding="utf-8"))
    assert "pcm" not in payload
    assert payload["yor"][0]["sentiment"] == "positive"


def test_load_delegates_to_db_load_csv(tmp_path):
    csv_path = tmp_path / "naijasenti_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.naijasenti.db.load_csv", return_value=9) as load_csv:
        result = naijasenti.load(csv_path, fake_conn)
    load_csv.assert_called_once_with(csv_path, fake_conn)
    assert result == 9
