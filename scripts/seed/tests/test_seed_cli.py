from unittest.mock import MagicMock, patch
import pytest
import seed


def test_parser_accepts_preflight():
    args = seed.build_parser().parse_args(["preflight"])
    assert args.command == "preflight"


def test_parser_accepts_verify():
    args = seed.build_parser().parse_args(["verify"])
    assert args.command == "verify"


def test_parser_per_dataset_subcommands():
    for sub in ("download", "sample", "transform", "load"):
        args = seed.build_parser().parse_args([sub, "igbo_api"])
        assert args.command == sub
        assert args.dataset == "igbo_api"


def test_parser_load_accepts_flags():
    args = seed.build_parser().parse_args(["load", "voa_ner", "--abort-if-not-empty", "--force"])
    assert args.abort_if_not_empty is True
    assert args.force is True


def test_parser_load_rejects_truncate_flag():
    parser = seed.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["load", "igbo_api", "--truncate"])


def test_parser_all_requires_one_of_truncate_or_abort():
    parser = seed.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["all"])


def test_parser_all_accepts_truncate():
    args = seed.build_parser().parse_args(["all", "--truncate"])
    assert args.truncate is True
    assert args.abort_if_not_empty is False


def test_parser_all_accepts_abort_if_not_empty():
    args = seed.build_parser().parse_args(["all", "--abort-if-not-empty"])
    assert args.abort_if_not_empty is True
    assert args.truncate is False


def test_parser_all_rejects_both_flags():
    parser = seed.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["all", "--truncate", "--abort-if-not-empty"])


def test_load_dispatch_aborts_if_table_non_empty(monkeypatch, tmp_path):
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 5)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)

    rc = seed.main(["load", "igbo_api", "--abort-if-not-empty"])
    assert rc == 1


def test_load_dispatch_aborts_if_source_already_loaded(monkeypatch):
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 100)

    rc = seed.main(["load", "igbo_api"])
    assert rc == 1


def test_load_dispatch_force_overrides_source_check(monkeypatch, tmp_path):
    csv_path = tmp_path / "igbo_api_clean.csv"
    csv_path.write_text("headword,pos,dialect_id,jsonb_data\n", encoding="utf-8")
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 100)
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("loaders.igbo_api.load", MagicMock(return_value=0))

    rc = seed.main(["load", "igbo_api", "--force"])
    assert rc == 0
