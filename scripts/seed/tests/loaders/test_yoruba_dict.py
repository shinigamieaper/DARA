import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import yoruba_dict


def _jsonl(*entries: dict) -> str:
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"


def test_dialect_id_is_1():
    assert yoruba_dict._DIALECT_ID == 1


def test_source_tag_matches_config():
    assert yoruba_dict.SOURCE_TAG == "Wiktionary Yoruba"


def test_download_writes_raw_jsonl(tmp_path):
    raw_dir = tmp_path / "raw"
    body = _jsonl(
        {"word": "ile", "pos": "noun", "lang_code": "yo",
         "senses": [{"glosses": ["house"]}]},
    )
    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.text = body

    with patch("loaders.yoruba_dict.requests.get", return_value=fake_resp) as get:
        out = yoruba_dict.download(raw_dir)

    get.assert_called_once()
    assert get.call_args.args[0] == yoruba_dict._URL
    assert out == raw_dir / "yoruba_dict" / "yoruba_dict.jsonl"
    assert out.read_text(encoding="utf-8") == body


def test_transform_groups_by_word_and_writes_csv(tmp_path):
    raw_dir = tmp_path / "raw" / "yoruba_dict"
    raw_dir.mkdir(parents=True)
    body = _jsonl(
        {"word": "ile", "pos": "noun",
         "senses": [{"glosses": ["house"], "examples": [{"text": "Ile mi dara."}]}],
         "sounds": [{"ipa": "/ile/"}]},
        {"word": "ile", "pos": "verb", "senses": [{"glosses": ["to pound"]}]},
        {"word": "ojo", "pos": "noun", "senses": [{"glosses": []}]},  # no gloss, dropped
        {"word": ".", "pos": "punctuation", "senses": [{"glosses": []}]},  # dropped
    )
    (raw_dir / "yoruba_dict.jsonl").write_text(body, encoding="utf-8")

    csv_path = yoruba_dict.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["headword"] == "ile"
    assert row["pos"] == "noun"
    assert row["dialect_id"] == "1"
    jsonb = json.loads(row["jsonb_data"])
    assert jsonb["source"] == "Wiktionary Yoruba"
    assert jsonb["license"] == "CC BY-SA"
    assert jsonb["attribution"] == "Wiktionary via kaikki.org"
    assert jsonb["definitions"] == ["house", "to pound"]
    assert jsonb["parts_of_speech"] == ["noun", "verb"]
    assert jsonb["ipa"] == ["/ile/"]
    assert jsonb["examples"] == ["Ile mi dara."]
    assert jsonb["dialect_assigned_default"] is True


def test_transform_uncapped_keeps_all_words(tmp_path):
    raw_dir = tmp_path / "raw" / "yoruba_dict"
    raw_dir.mkdir(parents=True)
    entries = [
        {"word": f"word_{i}", "pos": "noun", "senses": [{"glosses": [f"gloss {i}"]}]}
        for i in range(30)
    ]
    (raw_dir / "yoruba_dict.jsonl").write_text(_jsonl(*entries), encoding="utf-8")

    csv_path = yoruba_dict.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 30
    assert df["headword"].is_unique


def test_transform_caps_and_samples_deterministically(tmp_path):
    raw_dir = tmp_path / "raw" / "yoruba_dict"
    raw_dir.mkdir(parents=True)
    entries = [
        {"word": f"word_{i}", "pos": "noun", "senses": [{"glosses": [f"gloss {i}"]}]}
        for i in range(30)
    ]
    (raw_dir / "yoruba_dict.jsonl").write_text(_jsonl(*entries), encoding="utf-8")

    csv_path = yoruba_dict.transform(raw_dir.parent, tmp_path / "clean", cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 10
    assert df["headword"].is_unique


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "yoruba_dict_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.yoruba_dict.db.load_csv", return_value=(4865, 4865, [])):
        result = yoruba_dict.load(csv_path, fake_conn)
    assert result.dataset == "yoruba_dict"
    assert result.sampled == 4865
    assert result.inserted == 4865
    assert result.dropped_reasons == []
