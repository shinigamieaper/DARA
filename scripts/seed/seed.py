"""seed.py — CLI driver for the seed pipeline."""
import argparse
import sys

DATASETS = ("igbo_api", "yorulect", "voa_ner", "naijasenti")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="seed")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preflight", help="Connection + encoding + dialect-map checks")
    sub.add_parser("verify", help="Print breakdown; exit 1 if entries empty")

    for cmd in ("download", "sample", "transform"):
        p = sub.add_parser(cmd)
        p.add_argument("dataset", choices=DATASETS)

    p_load = sub.add_parser("load")
    p_load.add_argument("dataset", choices=DATASETS)
    p_load.add_argument("--abort-if-not-empty", action="store_true",
                        help="Refuse if entries table is non-empty")
    p_load.add_argument("--force", action="store_true",
                        help="Override the source-tag check")

    p_all = sub.add_parser("all")
    grp = p_all.add_mutually_exclusive_group(required=True)
    grp.add_argument("--truncate", action="store_true",
                     help="TRUNCATE entries+metadata before loading")
    grp.add_argument("--abort-if-not-empty", action="store_true",
                     help="Refuse if entries table is non-empty")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    # Dispatch added in Task 14.
    raise NotImplementedError(f"command {args.command} not wired yet")


if __name__ == "__main__":
    sys.exit(main())
