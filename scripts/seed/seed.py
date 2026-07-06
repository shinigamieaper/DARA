"""seed.py — CLI driver for the seed pipeline."""
import argparse
import sys
from pathlib import Path

import db
import preflight as preflight_module
import verify as verify_module
from loaders import igbo_api, yorulect, voa_ner, naijasenti, yoruba_dict, hausa_dict
from config import DATASET_ORDER, SOURCE_TAGS

DATASETS = ("igbo_api", "yorulect", "voa_ner", "naijasenti", "yoruba_dict", "hausa_dict")

CLEAN_DIR = Path(__file__).resolve().parent.parent.parent / "clean"
RAW_DIR = Path(__file__).resolve().parent.parent.parent / "raw"

LOADERS = {
    "igbo_api": igbo_api,
    "yorulect": yorulect,
    "voa_ner": voa_ner,
    "naijasenti": naijasenti,
    "yoruba_dict": yoruba_dict,
    "hausa_dict": hausa_dict,
}


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

    if args.command == "preflight":
        return preflight_module.run()
    if args.command == "verify":
        return verify_module.run()
    if args.command == "download":
        LOADERS[args.dataset].download(RAW_DIR)
        return 0
    if args.command == "sample":
        return _do_sample(args.dataset)
    if args.command == "transform":
        LOADERS[args.dataset].transform(RAW_DIR, CLEAN_DIR)
        return 0
    if args.command == "load":
        return _do_load(args)
    if args.command == "all":
        return _do_all(args)
    raise AssertionError(f"unhandled command: {args.command}")


def _do_load(args) -> int:
    csv_path = CLEAN_DIR / f"{args.dataset}_clean.csv"
    if not csv_path.exists():
        print(f"[load] missing {csv_path}; run `transform {args.dataset}` first",
              file=sys.stderr)
        return 1
    conn = db.connect()
    try:
        if args.abort_if_not_empty and db.entries_row_count(conn) > 0:
            print("[load] refusing: entries table is not empty "
                  "(--abort-if-not-empty was set)", file=sys.stderr)
            return 1
        tag = SOURCE_TAGS[args.dataset]
        if not args.force and db.source_row_count(conn, tag) > 0:
            print(f"[load] refusing: source {tag!r} already has rows. "
                  f"Pass --force to override.", file=sys.stderr)
            return 1
        result = LOADERS[args.dataset].load(csv_path, conn)
        print(f"[load] {result.format_line().strip()}")
        return 0
    finally:
        conn.close()


def _do_sample(dataset: str) -> int:
    """Print one raw entry from raw/<dataset>/ and exit. Read-only."""
    import json as _json
    raw_root = RAW_DIR / dataset
    if dataset == "naijasenti":
        payload = _json.loads((raw_root / "naijasenti.json").read_text(encoding="utf-8"))
        first_lang = next(iter(payload))
        print(f"[sample] naijasenti {first_lang}[0]:")
        print(_json.dumps(payload[first_lang][0], ensure_ascii=False, indent=2))
    elif dataset == "voa_ner":
        rows = _json.loads((raw_root / "voa_ner.json").read_text(encoding="utf-8"))
        print(_json.dumps(rows[0], ensure_ascii=False, indent=2))
    elif dataset == "igbo_api":
        rows = _json.loads((raw_root / "igbo_api.json").read_text(encoding="utf-8"))
        print(_json.dumps(rows[0], ensure_ascii=False, indent=2))
    elif dataset == "yorulect":
        std = RAW_DIR / "yorulect" / "standard"
        first_tsv = sorted(std.glob("*.tsv"))[0]
        print(f"[sample] yorulect standard/{first_tsv.name} (head -3):")
        with open(first_tsv, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i == 3:
                    break
                print(line.rstrip())
    elif dataset in ("yoruba_dict", "hausa_dict"):
        jsonl_path = raw_root / f"{dataset}.jsonl"
        with open(jsonl_path, "r", encoding="utf-8") as f:
            first_line = f.readline()
        print(f"[sample] {dataset} line 0:")
        print(_json.dumps(_json.loads(first_line), ensure_ascii=False, indent=2))
    return 0


def _do_all(args) -> int:
    conn = db.connect()
    try:
        if args.abort_if_not_empty and db.entries_row_count(conn) > 0:
            print("[all] refusing: entries table is not empty", file=sys.stderr)
            return 1
        if args.truncate:
            print("[all] truncating entries and metadata")
            db.truncate_all(conn)

        summary: list[db.LoadResult] = []
        for ds in DATASET_ORDER:
            print(f"\n=== {ds} ===")
            try:
                LOADERS[ds].download(RAW_DIR)
                csv_path = LOADERS[ds].transform(RAW_DIR, CLEAN_DIR)
                result = LOADERS[ds].load(csv_path, conn)
                summary.append(result)
            except Exception as e:
                print(f"[all] {ds} failed: {e}", file=sys.stderr)
                return 1

        print("\n=== Summary ===")
        print(f"Datasets loaded:  {', '.join(r.dataset for r in summary)}")
        print(f"Total entries:    {sum(r.inserted for r in summary)}")
        print()
        print("Per-dataset:")
        for r in summary:
            print(r.format_line())

        # Underflow detail subsection (per spec §9)
        underflow_rows: list[tuple[str, str, int, int]] = []
        for r in summary:
            for name, (avail, target) in r.underflow.items():
                underflow_rows.append((r.dataset, name, avail, target))
        if underflow_rows:
            print()
            print("Underflow detail:")
            for ds, name, avail, target in underflow_rows:
                short = target - avail
                print(f"  {ds} / {name}:   target {target}, available {avail} ({short} short)")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
