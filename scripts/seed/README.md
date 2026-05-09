# Seed Pipeline Runbook

Python sub-project that loads four upstream datasets into the Railway
Postgres `entries` and `metadata` tables. See the design spec at
[../../docs/superpowers/specs/2026-05-09-data-seeding-design.md](../../docs/superpowers/specs/2026-05-09-data-seeding-design.md)
and the implementation plan at
[../../docs/superpowers/plans/2026-05-09-data-seeding.md](../../docs/superpowers/plans/2026-05-09-data-seeding.md).

## First-time setup

Run from the repo root (`nigerian-languages-api/`):

```powershell
python -m venv .venv
.\.venv\Scripts\activate              # Windows; source .venv/bin/activate on POSIX
pip install -r requirements.txt
python scripts/seed/seed.py preflight
```

Preflight checks:
- `DATABASE_URL` is set in `.env` and the connection works.
- `client_encoding` is `UTF8`.
- The `dialects` table matches the 9-row map in `config.DIALECT_MAP`.
- Prints current `entries` and `metadata` row counts.

Exit 0 if all checks pass. Exit non-zero if any check fails.

## One-at-a-time first run

`--abort-if-not-empty` checks the *whole* `entries` table, so it only
fits on the first dataset loaded. Subsequent loads rely on the always-on
source-tag gate (refuses if this dataset's `SOURCE_TAG` already has rows
in `metadata`) to prevent double-loading.

```powershell
# Dataset 1: validates the table starts empty.
python scripts/seed/seed.py download igbo_api
python scripts/seed/seed.py sample   igbo_api          # eyeball one raw entry
python scripts/seed/seed.py transform igbo_api
python scripts/seed/seed.py load     igbo_api --abort-if-not-empty

# Datasets 2-4: source-tag gate is always on; --abort-if-not-empty
# would now refuse because igbo_api just inserted rows.
python scripts/seed/seed.py download yorulect
python scripts/seed/seed.py sample   yorulect
python scripts/seed/seed.py transform yorulect
python scripts/seed/seed.py load     yorulect

python scripts/seed/seed.py download voa_ner
python scripts/seed/seed.py sample   voa_ner
python scripts/seed/seed.py transform voa_ner
python scripts/seed/seed.py load     voa_ner

python scripts/seed/seed.py download naijasenti
python scripts/seed/seed.py sample   naijasenti
python scripts/seed/seed.py transform naijasenti
python scripts/seed/seed.py load     naijasenti

python scripts/seed/seed.py verify
```

## Re-run from scratch

```powershell
python scripts/seed/seed.py all --truncate
python scripts/seed/seed.py verify
```

`all --truncate` runs `TRUNCATE entries, metadata RESTART IDENTITY CASCADE`,
then loops `download → transform → load` for each of the four datasets in
order: igbo_api, yorulect, voa_ner, naijasenti. If any dataset fails, the
run halts (no partial subsequent loads).

## When things break

1. **`gdown` failure on YorùLect.** The Drive link printed in the error
   is the same one the README scrapes. Open it in a browser, download
   the folder manually into `raw/yorulect/`, then re-run
   `python scripts/seed/seed.py transform yorulect`. The download step
   is the only one that touches Drive; everything downstream reads from
   `raw/`. If the GitHub README itself is unreachable, write the Drive
   URL into `raw/yorulect/DRIVE_LINK.txt` and re-run download — it
   falls back to that file.

2. **Mid-dataset INSERT failure.** The whole dataset's transaction
   rolls back, so the DB is in the state it was in before the dataset
   started. Read the printed psycopg2 error and the offending row, fix
   the underlying cause (usually a malformed JSONB or an unexpected
   character in `headword`), then re-run `load <dataset>` for just
   that dataset — the prior datasets stay intact.

3. **Dialect ID mismatch.** Preflight printed a diff between the map in
   `config.py` and the `dialects` table. If the table is wrong, fix it
   in Railway. If the map is wrong, edit `config.py` and re-run
   preflight. Do **not** transform or load until preflight passes
   cleanly.

## Subcommand reference

| Subcommand | Purpose |
|------------|---------|
| `preflight` | Connection + UTF8 + dialect map + row counts |
| `download <dataset>` | Pull raw data into `raw/<dataset>/` |
| `sample <dataset>` | Print one raw entry; read-only |
| `transform <dataset>` | Read `raw/`, write `clean/<dataset>_clean.csv` |
| `load <dataset> [--abort-if-not-empty] [--force]` | Insert the clean CSV in one transaction |
| `all --truncate` | TRUNCATE + run all four datasets in order |
| `all --abort-if-not-empty` | Refuse if non-empty + run all four |
| `verify` | Print breakdown; exit 1 if entries empty |

`<dataset>` is one of: `igbo_api`, `yorulect`, `voa_ner`, `naijasenti`.

## Determinism

All sampling uses `random.Random(42)`. The four CSVs in `clean/` are
the deterministic, reproducible record of what was loaded. Re-running
the pipeline against the same upstream data produces byte-identical
CSVs. The `clean/` directory is committed; `raw/` is gitignored.

## Tests

```powershell
python -m pytest scripts/seed/tests/ -v
```

72 unit tests covering: config constants, db.connect/load_csv with the
CTE-based paired insert, preflight, verify, and all four loaders'
download / transform / load functions. All network and DB calls are
mocked in unit tests; the pipeline against the real Railway DB is
exercised by the manual one-at-a-time or `all --truncate` flows above.
