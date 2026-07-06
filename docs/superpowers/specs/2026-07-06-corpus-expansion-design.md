# Corpus Expansion (Phase 1: Uncap Existing Sources) — Design Spec

**Date:** 2026-07-06
**Status:** Approved for implementation
**Builds on:** `2026-05-09-data-seeding-design.md`

## 1. Motivation

The seeded repository holds 4,500 entries. In real downstream use (the
Oríkì praise-poetry app calling this API word by word), that corpus is
thin enough to look gimmicky: single-word lookups such as *jupụtara* and
*n'ụzọ* return "no dictionary or corpus match." This traces directly to
the "modest corpus size" limitation named in Chapter 5.

The key finding: **the pipeline already downloaded far more verified data
than it loads.** Each loader samples its source down to a small cap and
discards the rest:

| Source | Available on disk (verified) | Loaded today | Discarded |
|--------|------------------------------|--------------|-----------|
| IgboAPI (Igbo dictionary words) | 8,223 | 1,000 | ~7,200 |
| NaijaSenti (yor+ibo+hau tweets) | ~53,000 | 1,750 | ~51,000 |
| YorùLect (Yoruba dialect sentences) | ~6,000 | 1,000 | ~5,000 |
| VOA (Hausa news sentences) | ~5,000 | 750 | ~4,000 |

Loading everything already verified and downloaded raises the corpus from
4,500 to roughly 60,000 entries, and multiplies the Igbo dictionary by
eight — the single change that most directly fixes the blank word
lookups. No new sources, no schema change, no new verification burden.

## 2. Scope

**In scope (Phase 1, data only):**
- Remove the per-source sampling caps so each loader keeps every
  verified, de-duplicated row from the raw data already on disk.
- Keep the deterministic, reproducible pipeline: taking everything is
  trivially repeatable, and `Random(42)` remains for any residual case.
- Make the bulk insert fast enough to reseed ~60k rows to the remote
  database in minutes rather than hours.
- Reseed the live database and verify the new breakdown.
- Regenerate the committed `clean/*.csv` audit artifacts.

**Explicitly out of scope (deferred to Phase 2, separate spec):**
- New data sources (Yoruba dictionary words, Hausa dictionary words,
  dialect-labelled data for the empty Ehugbo / Enuani / Sokoto Hausa
  dialects).
- API changes: word search (`?search=`) and pagination (`?limit=/offset=`)
  on `GET /entries`. The corpus grows here; making a single word
  efficiently retrievable is Phase 2. This is flagged because at 60k rows
  the existing "return everything" endpoint gets heavier, not lighter.
- Any thesis / documentation rewrites (handled separately by the author).

## 3. Design

### 3.1 Uncap mechanism (`config.py` + four loaders)

Introduce a `None` sentinel in `CAPS` meaning "no cap, take all rows":

```python
CAPS = {
    "igbo_api":   {"total": None},
    "yorulect":   {"per_dialect": None},
    "voa_ner":    {"total": None},
    "naijasenti": {"yor": None, "ibo": None, "hau": None},
}
```

Each loader's `transform()` already resolves its cap from `CAPS` when the
caller passes nothing. The change: when the resolved cap is `None`, take
the whole de-duplicated pool and skip `rng.sample`.

- **igbo_api:** keep all minority (Ehugbo, Enuani) rows as today; when
  cap is `None`, keep all Central too. Dedup by `(headword, dialect_id)`
  unchanged.
- **yorulect:** when `per_dialect_cap` is `None`, take every unique
  sentence per dialect. Underflow tracking is moot when uncapped
  (nothing is a shortfall against "all"), so the underflow map stays
  empty. Cross-file dedup unchanged.
- **voa_ner:** when cap is `None`, take the whole de-duplicated pool.
- **naijasenti:** when a language's quota is `None`, take that language's
  whole de-duplicated pool. Per-language dedup unchanged.

Existing loader tests pass explicit numeric caps and are unaffected. New
tests cover the `None` (take-all) branch per loader.

### 3.2 Batched insert (`db.load_csv`)

The current insert loop issues one `cur.execute` per row (one network
round trip each). At 4,500 rows that is fine; at ~60,000 rows against the
remote database it would take hours. Switch to
`psycopg2.extras.execute_batch(cur, _PAIRED_INSERT_SQL, args, page_size=500)`.

- The paired-insert CTE (entries + metadata in one statement, linked by
  `RETURNING entry_id`) is unchanged — it still guarantees each metadata
  row references the correct entry without relying on multi-row
  `RETURNING` ordering.
- Empty-headword rows are still dropped (with reasons counted) before the
  batch is built. `inserted` is the count of rows actually sent.
- The whole load stays inside one `with conn:` transaction: it commits on
  clean exit and rolls back on any error, exactly as before.

`test_db.py` is updated to assert the batched call instead of per-row
`execute` calls.

### 3.3 Reseed procedure

Reseed from the raw data **already on disk** rather than re-downloading.
This avoids the flaky Google Drive fetch for YorùLect and is faithful to
the committed audit trail:

```
# regenerate the uncapped clean CSVs from existing raw/
python scripts/seed/seed.py transform igbo_api
python scripts/seed/seed.py transform yorulect
python scripts/seed/seed.py transform voa_ner
python scripts/seed/seed.py transform naijasenti

python scripts/seed/seed.py preflight           # confirm live DB + dialect map

# truncate + load each (source-tag gate passes once table is empty)
#   (truncate via db.truncate_all, then load each dataset)

python scripts/seed/seed.py verify              # new breakdown, ~60k rows
```

## 4. Success criteria

- `verify` reports roughly 60,000 total entries.
- IgboAPI (Igbo dictionary words) grows from 1,000 to ~8,223, with all
  Ehugbo and Enuani entries retained.
- Full `pytest` suite green.
- `clean/*.csv` regenerated and committed as the new audit record.
- No change to the Node API, the database schema, or the nine dialects.

## 5. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Reseed changes live data mid-run if a load fails | Each dataset loads in its own transaction; a failure rolls that dataset back and the reseed can be re-run. Data is fully reproducible from raw. |
| Larger `GET /entries` payloads at 60k rows | Flagged; word search + pagination is the Phase 2 follow-up. Not a blocker for data-only. |
| Committed CSVs grow large (~tens of MB) | Acceptable: they remain the deterministic, reviewable audit artifact the project relies on. |
| Remote insert still slow | `execute_batch` cuts ~60k round trips to ~120. |
```
