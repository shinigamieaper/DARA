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


def test_download_skips_pcm_and_pulls_three_langs_from_github(tmp_path):
    """Download fetches TSVs from GitHub raw, never touching pcm.

    Each TSV body has the 'tweet\\tlabel' header plus a couple of rows.
    The implementation should fetch yor/ibo/hau across 3 splits each
    (9 calls total) and never hit pcm."""
    raw_root = tmp_path / "raw" / "naijasenti"

    body_for = lambda lang, split: (
        "tweet\tlabel\n"
        f"{lang}_{split}_t1\tpositive\n"
        f"{lang}_{split}_t2\tnegative\n"
    )

    called_urls = []

    def fake_get(url, *args, **kwargs):
        called_urls.append(url)
        # Parse the URL: .../annotated_tweets/<lang>/<file>
        parts = url.rstrip("/").split("/")
        filename = parts[-1]  # train.tsv | dev.tsv | test.tsv
        lang = parts[-2]
        split = {"train.tsv": "train", "dev.tsv": "dev", "test.tsv": "test"}[filename]
        m = MagicMock()
        m.raise_for_status.return_value = None
        m.text = body_for(lang, split)
        return m

    with patch("loaders.naijasenti.requests.get", side_effect=fake_get):
        naijasenti.download(raw_root.parent)

    # 3 langs × 3 splits = 9 fetches; pcm never appears.
    assert len(called_urls) == 9
    assert all("/pcm/" not in u for u in called_urls)
    langs_called = {u.rstrip("/").split("/")[-2] for u in called_urls}
    assert langs_called == {"yor", "ibo", "hau"}

    payload = json.loads((raw_root / "naijasenti.json").read_text(encoding="utf-8"))
    assert "pcm" not in payload
    assert set(payload.keys()) == {"yor", "ibo", "hau"}
    # Each lang has 3 splits × 2 rows = 6 entries
    assert len(payload["yor"]) == 6
    # split names are normalized (dev → validation)
    splits_seen = {row["split"] for row in payload["yor"]}
    assert splits_seen == {"train", "validation", "test"}
    # Sentiment label is preserved as-is (no int2str needed; upstream is already strings)
    assert payload["yor"][0]["sentiment"] in {"positive", "negative", "neutral"}


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "naijasenti_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.naijasenti.db.load_csv", return_value=(1500, 1495, ["empty headword"] * 5)):
        result = naijasenti.load(csv_path, fake_conn)
    assert result.dataset == "naijasenti"
    assert result.sampled == 1500
    assert result.inserted == 1495
    assert len(result.dropped_reasons) == 5
