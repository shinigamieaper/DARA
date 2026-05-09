from unittest.mock import MagicMock, patch
import pytest
import db
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


def test_all_truncate_path_calls_truncate_then_loads_all_in_order(monkeypatch, tmp_path):
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        (tmp_path / f"{ds}_clean.csv").write_text(
            "headword,pos,dialect_id,jsonb_data\n", encoding="utf-8"
        )
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("seed.RAW_DIR", tmp_path)
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)
    truncate = MagicMock()
    monkeypatch.setattr("seed.db.truncate_all", truncate)

    call_order = []
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        monkeypatch.setattr(
            f"loaders.{ds}.download",
            lambda raw, _ds=ds: call_order.append(("download", _ds))
        )
        monkeypatch.setattr(
            f"loaders.{ds}.transform",
            lambda raw, clean, _ds=ds: (call_order.append(("transform", _ds)), tmp_path / f"{_ds}_clean.csv")[1]
        )
        monkeypatch.setattr(
            f"loaders.{ds}.load",
            lambda csv, conn, _ds=ds: (
                call_order.append(("load", _ds)),
                db.LoadResult(dataset=_ds, sampled=100, inserted=100),
            )[1],
        )

    rc = seed.main(["all", "--truncate"])
    assert rc == 0
    truncate.assert_called_once()
    loads = [ds for action, ds in call_order if action == "load"]
    assert loads == ["igbo_api", "yorulect", "voa_ner", "naijasenti"]


def test_all_abort_if_not_empty_refuses_when_table_has_rows(monkeypatch):
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 1)
    rc = seed.main(["all", "--abort-if-not-empty"])
    assert rc == 1


def test_all_stops_on_first_failure(monkeypatch, tmp_path):
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        (tmp_path / f"{ds}_clean.csv").write_text(
            "headword,pos,dialect_id,jsonb_data\n", encoding="utf-8"
        )
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("seed.RAW_DIR", tmp_path)
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)
    monkeypatch.setattr("seed.db.truncate_all", MagicMock())

    called = []
    monkeypatch.setattr("loaders.igbo_api.download", lambda raw: called.append("d_ia"))
    monkeypatch.setattr("loaders.igbo_api.transform",
                        lambda raw, clean: tmp_path / "igbo_api_clean.csv")
    monkeypatch.setattr("loaders.igbo_api.load",
                        lambda csv, conn: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr("loaders.yorulect.download", lambda raw: called.append("d_yl"))

    rc = seed.main(["all", "--truncate"])
    assert rc == 1
    assert "d_ia" in called
    assert "d_yl" not in called


def test_all_summary_includes_underflow_detail(monkeypatch, tmp_path, capsys):
    for ds in ("igbo_api", "yorulect", "voa_ner", "naijasenti"):
        (tmp_path / f"{ds}_clean.csv").write_text(
            "headword,pos,dialect_id,jsonb_data\n", encoding="utf-8"
        )
    monkeypatch.setattr("seed.CLEAN_DIR", tmp_path)
    monkeypatch.setattr("seed.RAW_DIR", tmp_path)
    monkeypatch.setattr("seed.db.connect", lambda: MagicMock())
    monkeypatch.setattr("seed.db.entries_row_count", lambda conn: 0)
    monkeypatch.setattr("seed.db.source_row_count", lambda conn, tag: 0)
    monkeypatch.setattr("seed.db.truncate_all", MagicMock())

    def make_result(ds, underflow=None):
        return db.LoadResult(
            dataset=ds, sampled=100, inserted=100,
            underflow=underflow or {},
        )

    for ds in ("igbo_api", "voa_ner", "naijasenti"):
        monkeypatch.setattr(f"loaders.{ds}.download", lambda raw, _ds=ds: None)
        monkeypatch.setattr(
            f"loaders.{ds}.transform",
            lambda raw, clean, _ds=ds: tmp_path / f"{_ds}_clean.csv",
        )
        monkeypatch.setattr(
            f"loaders.{ds}.load",
            lambda csv, conn, _ds=ds: make_result(_ds),
        )
    monkeypatch.setattr("loaders.yorulect.download", lambda raw: None)
    monkeypatch.setattr(
        "loaders.yorulect.transform",
        lambda raw, clean: tmp_path / "yorulect_clean.csv",
    )
    monkeypatch.setattr(
        "loaders.yorulect.load",
        lambda csv, conn: make_result("yorulect", {"ife": (203, 250)}),
    )

    rc = seed.main(["all", "--truncate"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Underflow detail:" in out
    assert "yorulect / ife" in out
    assert "47 short" in out
