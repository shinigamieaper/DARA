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


def test_download_pulls_all_three_splits_from_github(tmp_path):
    """Download fetches CoNLL TSVs from the upstream GitHub mirror.

    Each split's TSV body is short fixture content with two sentences
    separated by blank lines. The implementation parses CoNLL into
    {tokens, ner_tags, split} dicts."""
    raw_dir = tmp_path / "raw" / "voa_ner"

    fake_bodies = {
        "train_clean.tsv": "ya\tO\nyi\tO\n\nsannu\tB-PER\n",
        "dev.tsv":         "abc\tO\n\nxyz\tO\ndef\tO\n",
        "test.tsv":        "one\tO\ntwo\tO\nthree\tO\n",
    }

    def fake_get(url, *args, **kwargs):
        m = MagicMock()
        m.raise_for_status.return_value = None
        # last path segment of url is the filename
        filename = url.rsplit("/", 1)[-1]
        m.text = fake_bodies[filename]
        return m

    with patch("loaders.voa_ner.requests.get", side_effect=fake_get) as get:
        voa_ner.download(raw_dir.parent)

    assert get.call_count == 3
    out = json.loads((raw_dir / "voa_ner.json").read_text(encoding="utf-8"))
    splits = {row["split"] for row in out}
    assert splits == {"train", "validation", "test"}
    # Each parsed sentence carries tokens and ner_tags arrays of equal length.
    for row in out:
        assert len(row["tokens"]) == len(row["ner_tags"])
        assert row["tokens"]  # non-empty


def test_parse_conll_splits_on_blank_lines():
    text = "a\tO\nb\tO\n\nc\tB-PER\n"
    sentences = voa_ner._parse_conll(text)
    assert sentences == [(["a", "b"], ["O", "O"]), (["c"], ["B-PER"])]


def test_parse_conll_handles_trailing_sentence_with_no_trailing_blank():
    text = "x\tO\ny\tO"  # no trailing blank line
    sentences = voa_ner._parse_conll(text)
    assert sentences == [(["x", "y"], ["O", "O"])]


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "voa_ner_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.voa_ner.db.load_csv", return_value=(750, 750, [])):
        result = voa_ner.load(csv_path, fake_conn)
    assert result.dataset == "voa_ner"
    assert result.sampled == 750
    assert result.inserted == 750
    assert result.dropped_reasons == []


def test_transform_uncapped_keeps_all_unique(tmp_path):
    """cap=None keeps the whole de-duplicated pool."""
    raw_dir = tmp_path / "raw" / "voa_ner"
    raw_dir.mkdir(parents=True)
    entries = [
        {"tokens": ["sentence", str(i)], "ner_tags": [0, 0], "split": "train"}
        for i in range(30)
    ]
    (raw_dir / "voa_ner.json").write_text(json.dumps(entries), encoding="utf-8")

    csv_path = voa_ner.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 30
    assert df["headword"].is_unique
