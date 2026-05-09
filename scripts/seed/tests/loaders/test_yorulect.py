from pathlib import Path
from unittest.mock import MagicMock, patch
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
