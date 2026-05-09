# Data Seeding Pipeline — Design Spec

**Date:** 2026-05-09
**Status:** Approved for implementation planning

## 1. Goal

Seed real linguistic data into the Railway PostgreSQL database used by
the Dialect-Aware Repository API. Four upstream datasets feed three
languages (Yoruba, Igbo, Hausa) across nine pre-seeded dialects, with a
total target of 4500 entries.

The pipeline is a Python sub-project that lives alongside the existing
Node/Express API in this repo. It does not change the API code or the
database schema.

## 2. Database contract

The schema is defined in Railway and is treated as fixed by this spec:

```
entries(entry_id SERIAL PK, headword VARCHAR, pos VARCHAR, dialect_id INT)
metadata(meta_id SERIAL PK, entry_id INT FK -> entries, jsonb_data JSONB)
dialects(dialect_id INT PK, name VARCHAR, language_id INT FK -> languages)
languages(language_id INT PK, name VARCHAR, ...)
```

**Dialect ID map** (must match the `dialects` table exactly; the
preflight check stops the pipeline if it doesn't):

| ID | Name | Language |
|----|------|----------|
| 1 | Standard Yoruba | Yoruba |
| 2 | Ife | Yoruba |
| 3 | Ilaje | Yoruba |
| 4 | Ijebu | Yoruba |
| 5 | Central Igbo | Igbo |
| 6 | Ehugbo | Igbo |
| 7 | Enuani | Igbo |
| 8 | Standard Hausa | Hausa |
| 9 | Sokoto Hausa | Hausa |

`DATABASE_URL` is read from `.env` at the repo root via `python-dotenv`.

## 3. Datasets and volume caps

| Dataset | Source | Languages | Target rows |
|---------|--------|-----------|-------------|
| IgboAPI | HF `nkowaokwu/igbo_api` (GitHub raw JSON fallback) | Igbo (Central / Ehugbo / Enuani) | 1000 |
| YorùLect | Google Drive folder linked from `github.com/orevaahia/yorulect` README | Yoruba (Standard / Ife / Ilaje / Ijebu) | 1000 |
| VOA NER | HF `UdS-LSV/hausa_voa_ner` | Hausa (Standard) | 750 |
| NaijaSenti | HF `HausaNLP/NaijaSenti-Twitter`, configs `hau`, `ibo`, `yor` | Hausa, Igbo, Yoruba | 1750 (500 yor + 500 ibo + 750 hau) |

**Per-language totals (target):** Yoruba 1500, Igbo 1500, Hausa 1500.
**NaijaSenti `pcm` (Pidgin) is skipped entirely.**

Sampling is deterministic in every dataset: `random.Random(42)`. Same
inputs produce the same `clean/` CSVs every run. This is a hard
requirement for reproducibility of the capstone results.

## 4. Repository layout

```
nigerian-languages-api/
├── scripts/
│   └── seed/
│       ├── seed.py                    # CLI driver
│       ├── config.py                  # DB URL, dialect map, caps, RNG seed (42)
│       ├── db.py                      # psycopg2 connect + insert helper
│       ├── preflight.py               # connectivity, encoding, dialect-map, row-count checks
│       ├── verify.py                  # final breakdown query
│       ├── README.md                  # runbook (see §10)
│       └── datasets/
│           ├── igbo_api.py
│           ├── yorulect.py
│           ├── voa_ner.py
│           └── naijasenti.py
├── raw/                               # gitignored — downloaded source data
├── clean/                             # COMMITTED — four CSVs as audit artifacts
├── requirements.txt                   # pandas, datasets, psycopg2-binary, python-dotenv, gdown, requests
└── .gitignore                         # adds raw/, .venv/, __pycache__/, *.pyc
```

`clean/*.csv` is committed because the deterministic seed makes it a
reproducible, reviewable record of exactly what was loaded. `raw/` is
not committed.

## 5. CLI surface

```
python scripts/seed/seed.py preflight
    # connects, prints SHOW client_encoding, prints dialect map vs DB,
    # prints row counts in entries and metadata.
    # Exit 0 if all checks pass. Exit non-zero if connection fails,
    # client_encoding != UTF8, or dialect map doesn't match the DB.

python scripts/seed/seed.py download <dataset>
python scripts/seed/seed.py sample   <dataset>      # prints one raw entry, exits
python scripts/seed/seed.py transform <dataset>     # writes clean/<dataset>_clean.csv
python scripts/seed/seed.py load     <dataset> [--abort-if-not-empty] [--force]

python scripts/seed/seed.py all      ( --truncate | --abort-if-not-empty )
                                     # required: one of the two flags

python scripts/seed/seed.py verify
    # runs the breakdown SQL; exit 0 if entries has rows, exit 1 if empty
```

`<dataset>` is one of: `igbo_api`, `yorulect`, `voa_ner`, `naijasenti`.

**Flag rules:**

- `all` requires exactly one of `--truncate` or `--abort-if-not-empty`.
  No silent default.
  - `--truncate`: `TRUNCATE entries, metadata RESTART IDENTITY CASCADE` then load.
  - `--abort-if-not-empty`: refuse if `entries` has any rows; otherwise load.
- Per-dataset `load`:
  - `--abort-if-not-empty` is opt-in (refuses if `entries` is non-empty).
  - `--truncate` is **not** valid on per-dataset `load` (would wipe other
    datasets you already loaded).
  - Without `--force`, refuses if `metadata.jsonb_data->>'source'` already
    has rows for this dataset's `SOURCE_TAG`. Pass `--force` to override.

**Gate checks live in the CLI wrapper, not in `load()`.** Each dataset
module exposes a `SOURCE_TAG` constant (`"IgboAPI"`, `"YorùLect"`,
`"VOA Hausa"`, `"NaijaSenti"`). `seed.py` performs both gate checks
before opening any transaction, then calls `dataset.load(csv, conn)`,
which only does inserts.

## 6. Per-dataset transformations

Every dataset module exposes the same three functions:
`download(raw_dir)`, `transform(raw_dir, clean_dir) -> Path`,
`load(csv_path, conn)`. All file I/O uses `encoding='utf-8'` explicitly.

### 6.1 IgboAPI

- Source: `datasets.load_dataset("nkowaokwu/igbo_api")`. On HF failure,
  fall back to GitHub raw JSON (URL recorded in `igbo_api.py`).
- **Dialect mapping:** if `"Ehugbo"` appears in the entry's `dialects`
  array → `dialect_id=6`; elif `"Enuani"` → `7`; else `5` (Central
  default).
- `headword = word`; `pos = wordClass or "unknown"`.
- `jsonb_data = {source: "IgboAPI", definitions, examples, dialect_variants}`
  where `dialect_variants` is the entry's original `dialects` array.
- **Sampling rule:** keep every Ehugbo entry, keep every Enuani entry,
  then fill the remainder up to 1000 by sampling Central with
  `Random(42)`. Minority dialects are never truncated to fit the cap —
  if Ehugbo + Enuani together exceed 1000 (not expected from the known
  IgboAPI distribution), Central contributes zero and the total may
  slightly exceed 1000. Minority coverage takes priority over hitting
  exactly 1000.
- **Dedup:** by the tuple `(headword, dialect_id)`. Cross-dialect
  spelling overlaps are preserved (e.g., the same string appearing in
  Central and Ehugbo entries is kept as two rows).

### 6.2 YorùLect

- Source: Google Drive folder linked from the project README. The
  download step fetches the README via `requests.get`, regex-extracts
  the first Drive folder URL, and runs `gdown --folder` into
  `raw/yorulect/`.
- **Expected layout:** `raw/yorulect/<dialect>/<domain>.tsv` where
  `<dialect> ∈ {standard, ife, ilaje, ijebu}`. The transform step
  prints the actual layout it finds and aborts non-zero if it doesn't
  match.
- **Column choice:** the Yoruba column goes into `headword`. The
  aligned English column goes into JSONB as `english_translation`. If a
  .tsv doesn't have both columns, the transform step prints the columns
  it found and aborts.
- `pos = "sentence"`, `dialect_id` from folder name (standard→1, ife→2,
  ilaje→3, ijebu→4).
- `jsonb_data = {source: "YorùLect", domain: <filename without .tsv>, english_translation: <aligned EN>}`.
- **Sampling rule:** per dialect, pool sentences across all `.tsv`
  files, dedup by sentence text, take 250 via `Random(42)`. If a
  dialect has fewer than 250 unique sentences, take all of them, log a
  warning, and record the underflow in the summary (see §9). No
  backfill from another dialect.

### 6.3 VOA NER

- Source: `datasets.load_dataset("UdS-LSV/hausa_voa_ner")` — three
  splits (`train`, `validation`, `test`).
- Each row has `tokens` (list of strings) and `ner_tags` (list of ints).
- `headword = " ".join(tokens)`; `pos = "sentence"`; `dialect_id = 8`.
- `jsonb_data = {source: "VOA Hausa", split, dialect_assigned_default: true}`.
  **`ner_tags` is intentionally dropped** — outside the spec's JSONB
  shape and `pos="sentence"` collapses the row to a sentence-level
  entry.
- **Sampling rule:** pool train+validation+test, dedup by full sentence
  string, sample 750 via `Random(42)`.

### 6.4 NaijaSenti

- Source: `datasets.load_dataset("HausaNLP/NaijaSenti-Twitter", <config>)`
  for each config in `["hau", "ibo", "yor"]`. Config `pcm` is skipped.
- Per config: pool all splits, dedup by tweet text, then sample via
  `Random(42)`. **Per-language quotas:** `yor` → 500, `ibo` → 500,
  `hau` → 750. (Hausa gets the larger slice because VOA NER alone only
  contributes 750 and the per-language target is 1500.)
- Mapping: `yor → 1`, `ibo → 5`, `hau → 8`.
- `headword =` tweet text; `pos = "sentence"`.
- `jsonb_data = {source: "NaijaSenti", type: "tweet", sentiment: <label name>, split, dialect_assigned_default: true}`.
- **Sentiment label resolution:** the HF dataset stores labels as
  integers; the human-readable name comes from `dataset.features["label"].int2str(...)`.

## 7. Insert path and transactional integrity

**Connection management.** `db.connect()` reads `DATABASE_URL` via
`python-dotenv`, returns a `psycopg2.connect()` handle with
`autocommit=False`. Caller wraps with `with conn:` so the transaction
commits on clean exit and rolls back on any exception.

**Single-statement paired insert** (one round-trip per row):

```python
with conn:
    with conn.cursor() as cur:
        for row in df.itertuples(index=False):
            cur.execute(
                """
                WITH new_entry AS (
                  INSERT INTO entries (headword, pos, dialect_id)
                  VALUES (%s, %s, %s)
                  RETURNING entry_id
                )
                INSERT INTO metadata (entry_id, jsonb_data)
                SELECT entry_id, %s::jsonb FROM new_entry
                """,
                (row.headword, row.pos, int(row.dialect_id), row.jsonb_data),
            )
```

The CTE ensures each `metadata` row references the correct `entry_id`
without relying on `RETURNING` ordering across multi-row inserts.

**CSV format.** `clean/<dataset>_clean.csv` has exactly four columns:
`headword`, `pos`, `dialect_id`, `jsonb_data`. The `jsonb_data` column
is a JSON-encoded string. CSVs are written with
`pd.to_csv(..., encoding='utf-8', index=False)` and read back with
`pd.read_csv(..., dtype=str, encoding='utf-8')`. This makes the load
step a pure CSV → DB operation, decoupled from the upstream sources.

**Encoding posture.** All `pd.read_csv`, `pd.to_csv`, and raw `.tsv`
`open()` calls pass `encoding='utf-8'` explicitly. Preflight runs
`SHOW client_encoding` and aborts if the result is not `UTF8`.

**Dropped-row policy.** When a sampled row fails insert preconditions
(NULL or empty `headword`, JSONB serialization failure), the row is
dropped with a warning and the dataset's final count is the lower
number. **No backfill from the sample pool.** This preserves
seeded-random reproducibility — the rows that survive are the same on
every run.

## 8. Failure modes

| Failure | Response |
|---------|----------|
| Network error during HF download | Retry once with backoff; on second failure exit non-zero with the URL. |
| `gdown` fails on YorùLect | Exit non-zero with the Drive link. User can manually download into `raw/yorulect/` and re-run `transform`. |
| Fetch of YorùLect GitHub README fails (rate limit, network) | Exit non-zero with the README URL. User opens the URL, copies the Drive link into `raw/yorulect/DRIVE_LINK.txt`, and re-runs `download yorulect`, which reads from that file as a fallback. |
| Dialect IDs in DB don't match the map | Preflight prints the diff and exits 1. No transform happens. |
| INSERT fails mid-dataset | `with conn` rolls back the whole dataset. The offending row and the psycopg2 error are printed. `seed.py all` does **not** continue to the next dataset. |
| CSV row has missing `headword` | Drop the row with a warning before insert. No NULL headwords ever inserted. |
| JSONB serialization fails for a row | Drop the row with a warning, keep going. |
| `client_encoding` is not UTF8 | Preflight aborts with the actual value before any download or insert. |
| Per-dataset `load` invoked when its source already has rows | Refuse with message; pass `--force` to override. |

## 9. Summary and verification output

**`load <dataset>` output (success):**

```
[igbo_api] inserted 1000 rows
[igbo_api] dialect breakdown: {5: 873, 6: 64, 7: 63}
[igbo_api] sample joined rows:
  entry_id=1241 | Igbo / Central Igbo | "akwa" (noun) | source=IgboAPI
  entry_id=1242 | Igbo / Ehugbo       | "ulo"  (noun) | source=IgboAPI
  entry_id=1243 | Igbo / Enuani       | "mmiri" (n.)  | source=IgboAPI
```

**`verify` output:**

Plain-text table from the canonical breakdown query, plus `entries` and
`metadata` row counts to confirm they're in sync.

```sql
SELECT l.name AS language, d.name AS dialect, COUNT(e.entry_id) AS total
FROM entries e
JOIN dialects d ON e.dialect_id = d.dialect_id
JOIN languages l ON d.language_id = l.language_id
GROUP BY l.name, d.name
ORDER BY l.name, d.name;
```

Exit code 0 if `entries` has any rows; exit 1 if empty.

**`all` final summary** (printed after the verification table):

Underflow and drops are reported separately because they're different
failure modes:

- **Sampled** = how many rows the deterministic sample produced.
- **Inserted** = how many rows actually landed in the DB.
- **Dropped** = sampled minus inserted, due to row-level failures
  (NULL headword, JSONB error). Listed with reasons.
- **Underflow** = source had fewer unique rows than the cap. Reported
  per-dialect, never silently rolled into the dropped count.

```
=== Summary ===
Datasets loaded:  igbo_api, yorulect, voa_ner, naijasenti
Total entries:    4448

Per-dataset:
  igbo_api:    sampled 1000, inserted 1000 (0 dropped, 0 underflow)
  yorulect:    sampled 953,  inserted 953  (0 dropped, 47 underflow on ife)
  voa_ner:     sampled 750,  inserted 750  (0 dropped, 0 underflow)
  naijasenti:  sampled 1750, inserted 1745 (5 dropped: NULL tweet text, 0 underflow)

Underflow detail:
  yorulect / ife:   target 250, available 203 (47 short)
```

The numbers above are illustrative; the real summary is computed at
runtime.

## 10. Runbook (`scripts/seed/README.md`)

The README documents three flows:

**First-time setup:**
```
python -m venv .venv
.\.venv\Scripts\activate              # Windows; source .venv/bin/activate on POSIX
pip install -r requirements.txt
python scripts/seed/seed.py preflight
```

**One-at-a-time first run** (the pattern used while validating each
dataset for the capstone):
```
python scripts/seed/seed.py download igbo_api
python scripts/seed/seed.py sample   igbo_api          # eyeball one raw entry
python scripts/seed/seed.py transform igbo_api
python scripts/seed/seed.py load     igbo_api --abort-if-not-empty
# repeat for yorulect, voa_ner, naijasenti
python scripts/seed/seed.py verify
```

**Re-run from scratch:**
```
python scripts/seed/seed.py all --truncate
python scripts/seed/seed.py verify
```

**When things break:**

1. **`gdown` failure on YorùLect.** The Drive link printed in the error
   is the same one the README scrapes. Open it in a browser, download
   the folder manually into `raw/yorulect/`, then re-run
   `python scripts/seed/seed.py transform yorulect`. The download step
   is the only one that touches Drive; everything downstream reads from
   `raw/`.

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

## 11. Stopping rules

The pipeline halts on any of these conditions without writing data:

- Dataset URL unreachable after one retry.
- `dialects` table doesn't match the dialect ID map.
- `client_encoding` is not UTF8.
- An insert fails — the dataset's transaction rolls back, the error is
  printed, and `all` does not continue to subsequent datasets.

The pipeline never fabricates data: missing source fields are left
NULL or omitted from JSONB.

## 12. Out of scope

- Schema changes or migrations. The DB schema is fixed by Railway.
- New API endpoints. The Node API is unchanged.
- Adding more dialects beyond the nine pre-seeded.
- Pidgin (NaijaSenti `pcm`).
- Token-level NER tags from VOA NER (intentionally dropped).
- Any English-only or non-Nigerian-language rows.
- Cross-run delta loading. The pipeline is whole-dataset, not
  incremental.
