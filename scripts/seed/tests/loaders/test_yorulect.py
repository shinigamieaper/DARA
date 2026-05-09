from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import shutil
import pandas as pd
import pytest
from loaders import yorulect


def test_extract_drive_url_from_readme():
    readme = """
    # YorùLect
    Download the data from
    https://drive.google.com/drive/folders/1aBcDeF12345 here.
    """
    url = yorulect.extract_drive_url(readme)
    assert url == "https://drive.google.com/drive/folders/1aBcDeF12345"


def test_extract_drive_url_raises_when_missing():
    with pytest.raises(ValueError, match="No Google Drive"):
        yorulect.extract_drive_url("# README with no link")


def test_download_scrapes_readme_then_calls_gdown(tmp_path):
    raw_dir = tmp_path / "raw"
    fake_resp = MagicMock()
    fake_resp.text = "see https://drive.google.com/drive/folders/XYZ for data"
    fake_resp.raise_for_status.return_value = None
    with patch("loaders.yorulect.requests.get", return_value=fake_resp) as gh, \
         patch("loaders.yorulect.gdown.download_folder") as gd:
        yorulect.download(raw_dir)
    gh.assert_called_once()
    gd.assert_called_once()
    assert "XYZ" in gd.call_args[0][0]


def test_download_falls_back_to_drive_link_txt(tmp_path):
    raw_dir = tmp_path / "raw"
    (raw_dir / "yorulect").mkdir(parents=True)
    (raw_dir / "yorulect" / "DRIVE_LINK.txt").write_text(
        "https://drive.google.com/drive/folders/MANUAL", encoding="utf-8"
    )
    with patch("loaders.yorulect.requests.get", side_effect=RuntimeError("rate limited")), \
         patch("loaders.yorulect.gdown.download_folder") as gd:
        yorulect.download(raw_dir)
    gd.assert_called_once()
    assert "MANUAL" in gd.call_args[0][0]


FIXTURES = Path(__file__).parent.parent / "fixtures" / "yorulect"


def _copy_fixtures(dest: Path):
    shutil.copytree(FIXTURES, dest)


def test_transform_picks_yoruba_column_and_assigns_dialect_from_folder(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["pos"] == "sentence").all()
    standard = df[df["dialect_id"] == "1"]
    ife = df[df["dialect_id"] == "2"]
    assert "Àgbẹ̀ ń gbin iṣu." in standard["headword"].values
    assert "Àgbẹ̀ ǹ gbin iṣu." in ife["headword"].values  # different diacritic


def test_transform_jsonb_carries_domain_and_english(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    row = df[df["headword"] == "Àgbẹ̀ ń gbin iṣu."].iloc[0]
    jsonb = json.loads(row["jsonb_data"])
    assert jsonb["source"] == "YorùLect"
    assert jsonb["domain"] == "farming"
    assert jsonb["english_translation"] == "The farmer plants yam."


def test_transform_cross_file_dedup_keeps_first_alphabetical(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)
    df = pd.read_csv(csv_path, dtype=str)
    # "Ó ní oko." appears in both standard/farming.tsv and standard/cooking.tsv.
    # cooking.tsv sorts before farming.tsv alphabetically, so cooking wins.
    duplicates = df[df["headword"] == "Ó ní oko."]
    assert len(duplicates) == 1
    jsonb = json.loads(duplicates.iloc[0]["jsonb_data"])
    assert jsonb["domain"] == "cooking"


def test_transform_underflow_caps_at_available(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    # ife only has 2 unique sentences in the fixture; cap of 250 means we get 2.
    csv_path = yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=250)
    df = pd.read_csv(csv_path, dtype=str)
    assert (df["dialect_id"] == "2").sum() == 2


def test_transform_aborts_on_missing_dialect_folder(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    raw.mkdir(parents=True)
    # only standard/, no others
    (raw / "standard").mkdir()
    (raw / "standard" / "x.tsv").write_text("english\tyoruba\nhi\tbonjour\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)


def test_transform_aborts_on_missing_columns(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    for sub in ("standard", "ife", "ilaje", "ijebu"):
        (raw / sub).mkdir(parents=True)
        (raw / sub / "bad.tsv").write_text("col1\tcol2\nx\ty\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=10)


def test_load_returns_load_result_no_sidecar(tmp_path):
    csv_path = tmp_path / "yorulect_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.yorulect.db.load_csv", return_value=(950, 950, [])):
        result = yorulect.load(csv_path, fake_conn)
    assert result.dataset == "yorulect"
    assert result.sampled == 950
    assert result.inserted == 950
    assert result.underflow == {}


def test_load_reads_underflow_sidecar(tmp_path):
    csv_path = tmp_path / "yorulect_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    sidecar = tmp_path / "yorulect_underflow.json"
    sidecar.write_text('{"ife": [203, 250]}', encoding="utf-8")
    fake_conn = MagicMock()
    with patch("loaders.yorulect.db.load_csv", return_value=(950, 950, [])):
        result = yorulect.load(csv_path, fake_conn)
    assert result.underflow == {"ife": (203, 250)}


def test_transform_writes_underflow_sidecar(tmp_path):
    raw = tmp_path / "raw" / "yorulect"
    _copy_fixtures(raw)
    yorulect.transform(raw.parent, tmp_path / "clean", per_dialect_cap=250)
    sidecar = tmp_path / "clean" / "yorulect_underflow.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    # ife fixture has 2 unique sentences; with cap=250 it underflows.
    assert data["ife"] == [2, 250]
