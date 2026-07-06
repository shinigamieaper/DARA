import json
from unittest.mock import MagicMock, patch

import pandas as pd

from loaders import hausa_proverbs

# Fabricated fixture mirroring the real OCR text's structure:
# - a running page header ("HAUSA PROVERBS")
# - a page header fused with a page number ("72 Haiisa Proverbs") that must
#   NOT be mistaken for a real numbered proverb (it contains "Proverbs")
# - proverb 1: has a translation AND an explanatory note
# - proverb 2: has a translation, no note
# - proverb 3: immediately followed by proverb 4 with no blank/translation
#   in between -> must be dropped (no English translation)
# - proverb 4: translation + a two-line note
# - the "HAUSA SONGS" section header, after which proverb 5 must be ignored
#   entirely (parsing stops before it is ever reached)
_FIXTURE = """\
HAUSA PROVERBS

1 Kome nisan dawa, gida ake dawowa.

However far the bush is, one returns home.

This proverb encourages travellers to keep their home ties.

72 Haiisa Proverbs

2 Kaza in ta yi kiwo sai ta koma gida.

A hen that forages still returns home in the end.

3 Ruwa a baya-baya shi ke kwarara ba tare da fassara ba.
4 Mai hakuri shi ke cin dorowa.

He who is patient eats the locust bean in the end.

The locust bean tree takes long to bear fruit.
It rewards only the patient farmer.

HAUSA SONGS

5 Wannan ba za a taba karanta ba.

Wannan fassarar ma ba za a taba gani ba.
"""


def test_dialect_id_is_8():
    assert hausa_proverbs._DIALECT_ID == 8


def test_source_tag_matches_config():
    assert hausa_proverbs.SOURCE_TAG == "Hausa Proverbs"


def test_parse_proverbs_extracts_only_valid_blocks_in_order():
    proverbs = hausa_proverbs._parse_proverbs(_FIXTURE)
    assert [p["number"] for p in proverbs] == [1, 2, 4]


def test_parse_proverbs_skips_headers_and_fused_page_numbers():
    proverbs = hausa_proverbs._parse_proverbs(_FIXTURE)
    for p in proverbs:
        assert "proverb" not in p["hausa"].lower()
    assert 72 not in [p["number"] for p in proverbs]


def test_parse_proverbs_drops_block_with_no_translation():
    proverbs = hausa_proverbs._parse_proverbs(_FIXTURE)
    assert 3 not in [p["number"] for p in proverbs]


def test_parse_proverbs_stops_at_hausa_songs_section():
    proverbs = hausa_proverbs._parse_proverbs(_FIXTURE)
    assert 5 not in [p["number"] for p in proverbs]


def test_parse_proverbs_captures_hausa_english_and_note():
    proverbs = hausa_proverbs._parse_proverbs(_FIXTURE)
    first = next(p for p in proverbs if p["number"] == 1)
    assert first["hausa"] == "Kome nisan dawa, gida ake dawowa"
    assert first["english"] == "However far the bush is, one returns home."
    assert first["note"] == "This proverb encourages travellers to keep their home ties."

    second = next(p for p in proverbs if p["number"] == 2)
    assert second["english"] == "A hen that forages still returns home in the end."
    assert second["note"] == ""

    fourth = next(p for p in proverbs if p["number"] == 4)
    assert fourth["english"] == "He who is patient eats the locust bean in the end."
    assert fourth["note"] == ("The locust bean tree takes long to bear fruit. "
                              "It rewards only the patient farmer.")


def test_download_writes_raw_text(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_resp = MagicMock()
    fake_resp.raise_for_status.return_value = None
    fake_resp.text = _FIXTURE

    with patch("loaders.hausa_proverbs.requests.get", return_value=fake_resp) as get:
        out = hausa_proverbs.download(raw_dir)

    get.assert_called_once()
    assert get.call_args.args[0] == hausa_proverbs._SOURCE_URL
    assert out == raw_dir / "hausa_proverbs" / "merrick.txt"
    assert out.read_text(encoding="utf-8") == _FIXTURE


def test_transform_writes_clean_csv_with_expected_columns_and_jsonb(tmp_path):
    raw_dir = tmp_path / "raw" / "hausa_proverbs"
    raw_dir.mkdir(parents=True)
    (raw_dir / "merrick.txt").write_text(_FIXTURE, encoding="utf-8")

    csv_path = hausa_proverbs.transform(raw_dir.parent, tmp_path / "clean", cap=None)
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)

    assert list(df.columns) == ["headword", "pos", "dialect_id", "jsonb_data"]
    assert len(df) == 3
    assert (df["pos"] == "proverb").all()
    assert (df["dialect_id"] == "8").all()

    row = df[df["headword"] == "Kome nisan dawa, gida ake dawowa"].iloc[0]
    jsonb = json.loads(row["jsonb_data"])
    assert jsonb["source"] == "Hausa Proverbs"
    assert jsonb["genre"] == "proverb"
    assert jsonb["proverb_number"] == 1
    assert jsonb["english_translation"] == "However far the bush is, one returns home."
    assert jsonb["note"] == "This proverb encourages travellers to keep their home ties."
    assert jsonb["license"] == "Public Domain"
    assert jsonb["origin"] == hausa_proverbs._ORIGIN
    assert jsonb["dialect_assigned_default"] is True


def test_transform_caps_and_samples_deterministically(tmp_path):
    raw_dir = tmp_path / "raw" / "hausa_proverbs"
    raw_dir.mkdir(parents=True)
    blocks = "\n\n".join(
        f"{i} Magana {i}.\n\nSaying number {i}." for i in range(1, 21)
    )
    (raw_dir / "merrick.txt").write_text(blocks + "\n", encoding="utf-8")

    csv_path = hausa_proverbs.transform(raw_dir.parent, tmp_path / "clean", cap=5)
    df = pd.read_csv(csv_path, dtype=str)
    assert len(df) == 5
    assert df["headword"].is_unique


def test_load_returns_load_result(tmp_path):
    csv_path = tmp_path / "hausa_proverbs_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.hausa_proverbs.db.load_csv", return_value=(330, 330, [])):
        result = hausa_proverbs.load(csv_path, fake_conn)
    assert result.dataset == "hausa_proverbs"
    assert result.sampled == 330
    assert result.inserted == 330
    assert result.dropped_reasons == []
