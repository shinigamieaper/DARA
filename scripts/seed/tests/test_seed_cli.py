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
