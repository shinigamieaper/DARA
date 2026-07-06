import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import hausa_dict


def _jsonl(*entries: dict) -> str:
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"


def test_dialect_id_is_8():
    assert hausa_dict._DIALECT_ID == 8


def test_source_tag_matches_config():
    assert hausa_dict.SOURCE_TAG == "Wiktionary Hausa"


def test_download_writes_raw_jsonl(tmp_path):
    raw_dir = tmp_path / "raw"
    body = _jsonl(
        {"word": "gida", "pos": "noun", "lang_code": "ha",
         "senses": [{"glosses": ["house"]}]},
    )
    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.text = body

    with patch("loaders.hausa_dict.requests.get", return_value=fake_resp) as get:
        out = hausa_dict.download(raw_dir)

    get.assert_called_once()
    assert get.call_args.args[0] == hausa_dict._URL
    assert out == raw_dir / "hausa_dict" / "hausa_dict.jsonl"
    assert out.read_text(encoding="utf-8") == body


def test_transform_groups_by_word_and_writes_csv(tmp_path):
    raw_dir = tmp_path / "raw" / "hausa_dict"
    raw_dir.mkdir(parents=True)
    body = _jsonl(
        {"word": "gida", "pos": "noun",
         "senses": [{"glosses": ["house"], "examples": [{"text": "Gida na yana nan."}]}],
         "sounds": [{"ipa": "/gidaː/"}]},
        {"word": "gida", "pos": "verb", "senses": [{"glosses": ["to house"]}]},
        {"word": "rana", "pos": "noun", "senses": [{"glosses": []}]},  # no gloss, dropped
        {"word": ".", "pos": "punctuation", "senses": [{"glosses": []}]},  # dropped
    )
    (raw_dir / "hausa_dict.jsonl").write_text(body, encoding="utf-8")

    csv_path = hausa_dict.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str)

    assert len(df) == 1
    row = df.iloc[0]
    assert row["headword"] == "gida"
    assert row["pos"] == "noun"
    assert row["dialect_id"] == "8"
    jsonb = json.loads(row["jsonb_data"])
    assert jsonb["source"] == "Wiktionary Hausa"
    assert jsonb["license"] == "CC BY-SA"
    assert jsonb["attribution"] == "Wiktionary via kaikki.org"
    assert jsonb["definitions"] == ["house", "to house"]
    assert jsonb["parts_of_speech"] == ["noun", "verb"]
    assert jsonb["ipa"] == ["/gidaː/"]
    assert jsonb["examples"] == ["Gida na yana nan."]
    assert jsonb["dialect_assigned_default"] is True


def test_transform_uncapped_keeps_all_words(tmp_path):
    raw_dir = tmp_path / "raw" / "hausa_dict"
    raw_dir.mkdir(parents=True)
    entries = [
        {"word": f"word_{i}", "pos": "noun", "senses": [{"glosses": [f"gloss {i}"]}]}
        for i in range(30)
    ]
    (raw_dir / "hausa_dict.jsonl").write_text(_jsonl(*entries), encoding="utf-8")

    csv_path = hausa_dict.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 30
    assert df["headword"].is_unique


def test_transform_caps_and_samples_deterministically(tmp_path):
    raw_dir = tmp_path / "raw" / "hausa_dict"
    raw_dir.mkdir(parents=True)
    entries = [
        {"word": f"word_{i}", "pos": "noun", "senses": [{"glosses": [f"gloss {i}"]}]}
        for i in range(30)
    ]
    (raw_dir / "hausa_dict.jsonl").write_text(_jsonl(*entries), encoding="utf-8")

    csv_path = hausa_dict.transform(raw_dir.parent, tmp_path / "clean", cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 10
    assert df["headword"].is_unique


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "hausa_dict_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.hausa_dict.db.load_csv", return_value=(2002, 2002, [])):
        result = hausa_dict.load(csv_path, fake_conn)
    assert result.dataset == "hausa_dict"
    assert result.sampled == 2002
    assert result.inserted == 2002
    assert result.dropped_reasons == []
