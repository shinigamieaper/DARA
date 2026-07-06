import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import yoruba_proverbs


def _jsonl(*entries: dict) -> str:
    return "\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n"


def test_dialect_id_is_1():
    assert yoruba_proverbs._DIALECT_ID == 1


def test_source_tag_matches_config():
    assert yoruba_proverbs.SOURCE_TAG == "Yoruba Proverbs"


def test_download_fetches_both_sources(tmp_path):
    raw_dir = tmp_path / "raw"
    mxronga_body = _jsonl({"yoruba": "Bí a bá tán an", "english": "When it is done"})
    menyo_body = ",English,Yoruba\n0,A stitch in time,Bí a kò bá lọ\n"

    def fake_get(url, *args, **kwargs):
        m = MagicMock()
        m.raise_for_status.return_value = None
        if url == yoruba_proverbs._MXRONGA_URL:
            m.text = mxronga_body
        elif url == yoruba_proverbs._MENYO_URL:
            m.text = menyo_body
        else:
            raise AssertionError(f"unexpected URL {url}")
        return m

    with patch("loaders.yoruba_proverbs.requests.get", side_effect=fake_get) as get:
        out = yoruba_proverbs.download(raw_dir)

    assert get.call_count == 2
    assert out == raw_dir / "yoruba_proverbs"
    assert (out / "mxronga.jsonl").read_text(encoding="utf-8") == mxronga_body
    assert (out / "menyo.csv").read_text(encoding="utf-8") == menyo_body


def test_transform_combines_and_dedups_by_yoruba_text(tmp_path):
    raw_dir = tmp_path / "raw" / "yoruba_proverbs"
    raw_dir.mkdir(parents=True)

    mxronga_body = _jsonl(
        {"yoruba": "Àkàn kìí bí ọmọ tí kò lẹ́sẹ̀", "english": "A crab never bears a footless child"},
        {"yoruba": "Ìlọ kìí burú", "english": "Going never turns out badly"},
    )
    (raw_dir / "mxronga.jsonl").write_text(mxronga_body, encoding="utf-8")

    menyo_body = (
        ",English,Yoruba\n"
        "0,Going never turns out badly (dup),Ìlọ kìí burú\n"
        "1,Patience pays off,Sùúrù ni bàbá ìwà\n"
    )
    (raw_dir / "menyo.csv").write_text(menyo_body, encoding="utf-8")

    csv_path = yoruba_proverbs.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    assert len(df) == 3
    assert df["headword"].is_unique
    assert (df["pos"] == "proverb").all()
    assert (df["dialect_id"] == "1").all()

    dup_row = df[df["headword"] == "Ìlọ kìí burú"].iloc[0]
    jsonb = json.loads(dup_row["jsonb_data"])
    assert jsonb["english_translation"] == "Going never turns out badly"
    assert jsonb["origin"] == yoruba_proverbs._MXRONGA_ORIGIN
    assert jsonb["license"] == "Apache-2.0"

    menyo_only_row = df[df["headword"] == "Sùúrù ni bàbá ìwà"].iloc[0]
    jsonb2 = json.loads(menyo_only_row["jsonb_data"])
    assert jsonb2["origin"] == yoruba_proverbs._MENYO_ORIGIN
    assert jsonb2["license"] == "CC BY-NC 4.0"
    assert jsonb2["source"] == "Yoruba Proverbs"
    assert jsonb2["genre"] == "proverb"
    assert jsonb2["dialect_assigned_default"] is True


def test_transform_skips_empty_yoruba_text(tmp_path):
    raw_dir = tmp_path / "raw" / "yoruba_proverbs"
    raw_dir.mkdir(parents=True)
    mxronga_body = _jsonl(
        {"yoruba": "", "english": "empty, should be skipped"},
        {"yoruba": "Ẹnu ni oògùn ọ̀rọ̀", "english": "The mouth is the medicine of speech"},
    )
    (raw_dir / "mxronga.jsonl").write_text(mxronga_body, encoding="utf-8")
    (raw_dir / "menyo.csv").write_text(",English,Yoruba\n", encoding="utf-8")

    csv_path = yoruba_proverbs.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    assert len(df) == 1
    assert df.iloc[0]["headword"] == "Ẹnu ni oògùn ọ̀rọ̀"


def test_transform_caps_and_samples_deterministically(tmp_path):
    raw_dir = tmp_path / "raw" / "yoruba_proverbs"
    raw_dir.mkdir(parents=True)
    entries = [
        {"yoruba": f"òwe {i}", "english": f"proverb {i}"} for i in range(20)
    ]
    (raw_dir / "mxronga.jsonl").write_text(_jsonl(*entries), encoding="utf-8")
    (raw_dir / "menyo.csv").write_text(",English,Yoruba\n", encoding="utf-8")

    csv_path = yoruba_proverbs.transform(raw_dir.parent, tmp_path / "clean", cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 10
    assert df["headword"].is_unique


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "yoruba_proverbs_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.yoruba_proverbs.db.load_csv", return_value=(3268, 3268, [])):
        result = yoruba_proverbs.load(csv_path, fake_conn)
    assert result.dataset == "yoruba_proverbs"
    assert result.sampled == 3268
    assert result.inserted == 3268
    assert result.dropped_reasons == []
