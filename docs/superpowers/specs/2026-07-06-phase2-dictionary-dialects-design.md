# Phase 2: Dictionary Words + Dialect Seed Sets — Design Spec

**Date:** 2026-07-06
**Status:** Approved for implementation planning
**Builds on:** `2026-07-06-corpus-expansion-design.md` (Phase 1)

## 1. Goal

Close the two gaps Phase 1 could not: languages with no dictionary words,
and dialects with no entries at all. Constrained by three decisions the
author made after the Phase 2 research:

1. **Open licenses only.** No non-commercial (NC) sources. This removes
   the gated multi-dialectal IgboAPI dataset (CC BY-NC-SA), which was the
   only source that could have filled Ehugbo automatically, and removes
   the Igbo enrichment set. Igbo stays at its current open ~8k.
2. **No audio this phase.** No schema change; no object storage.
3. **Hand-build the empty dialects.** Ehugbo, Enuani, and Sokoto Hausa
   get small, hand-curated seed sets sourced from real, citable, openly
   accessible references. No fabrication: every seed word traces to a
   named source recorded in its metadata.

## 2. Scope

**In scope:**
- **Yoruba dictionary loader** — kaikki.org Wiktextract of Yoruba
  Wiktionary. CC BY-SA. ~4,865 words with parts of speech, English
  glosses, and IPA/tone. Assigned to Standard Yoruba (dialect_id 1).
- **Hausa dictionary loader** — kaikki.org Wiktextract of Hausa
  Wiktionary. CC BY-SA. ~2,002 words. Assigned to Standard Hausa
  (dialect_id 8).
- **Dialect seed sets** — small hand-curated, cited wordlists for
  Ehugbo (6), Enuani (7), Sokoto Hausa (9). Volume is intentionally
  small (tens to low hundreds each) and every row cites its source.
  Where no openly accessible source can be verified for a dialect, that
  dialect stays empty and the gap is documented — an honest finding, not
  a fabricated fill.
- Wire all new sources into `config.py`, `seed.py`, reseed, verify.

**Out of scope:**
- Non-commercial sources (NaijaVoices audio, gated IgboAPI, arXiv
  2405.00997 multi-dialectal set).
- Audio and any schema change.
- API changes (search/pagination still deferred).
- Igbo dictionary enrichment (only available under NC / gated access).

## 3. Data sources (verified 2026-07-06)

| Source | URL | License | Size | Notes |
|--------|-----|---------|------|-------|
| Yoruba Wiktextract | `https://kaikki.org/dictionary/Yoruba/kaikki.org-dictionary-Yoruba.jsonl` | CC BY-SA | 6,273 lines / 4,865 words | JSONL; deprecated per-language file, raw pipeline is the durable fallback |
| Hausa Wiktextract | `https://kaikki.org/dictionary/Hausa/kaikki.org-dictionary-Hausa.jsonl` | CC BY-SA | ~2,002 words | JSONL; same deprecation note |

**Durability risk:** kaikki marks the per-language JSONL "deprecated,
will be removed." Mitigation: the downloaded raw JSONL is kept in `raw/`
(already the pattern) and the resulting `clean/*.csv` is committed, so the
data survives even if the upstream file disappears. If the URL 404s at
build time, fall back to the kaikki raw-data pipeline (filter the full
Wiktextract dump by `lang_code`).

**kaikki JSONL shape (confirmed):** top-level `word`, `pos`, `lang_code`,
`senses[]` (each with `glosses[]`, `tags[]`, optional `examples[]`),
`sounds[]` (each with `ipa`), `forms[]`.

## 4. Transformations

### 4.1 Dictionary loaders (Yoruba, Hausa)

Both follow the existing loader contract exactly:
`download(raw_root)`, `transform(raw_root, clean_dir, cap=None)`,
`load(csv_path, conn)`, plus a `SOURCE_TAG` constant.

- **Grouping:** group all JSONL lines by `word` into ONE entry per word
  (a word may appear on several lines, one per part of speech). This
  keeps headwords unique and gives a clean dictionary entry.
- **headword** = `word`.
- **pos** = the first line's `pos`; the full distinct set goes into JSONB
  as `parts_of_speech`.
- **dialect_id** = 1 (Yoruba) or 8 (Hausa) — standard variety.
- **jsonb_data** =
  `{source, license: "CC BY-SA", attribution: "Wiktionary via kaikki.org",
    definitions: [all glosses], parts_of_speech: [...], ipa: [all ipa],
    examples: [any sense examples], dialect_assigned_default: true}`.
- **Filtering:** keep a word only if it has at least one non-empty gloss.
  Drop `pos` values that are not lexical entries (`character`,
  `punctuation`, `symbol`) when they carry no real gloss.
- **Dedup:** by `headword` within the language (grouping already enforces
  one row per word). Cross-source overlap with existing Standard-Yoruba /
  Standard-Hausa sentence rows is fine — the source tag distinguishes
  dictionary words from sentences.
- **Cap:** honours the `None` = take-all convention from Phase 1.

### 4.2 Dialect seed sets

Not an automated download. A committed, reviewed CSV per dialect:
`clean/dialect_seed_<dialect>.csv` with the standard four columns. Each
row's `jsonb_data` carries
`{source: "<dialect> seed", origin: "<full citation>", ...}` naming the
exact reference the word came from. A single small loader
(`dialect_seeds.py`) reads these committed CSVs and loads them — it does
NOT fetch anything, so the provenance is auditable in git.

Sourcing rule (hard): a word enters a seed CSV only if it is transcribed
from a real, openly accessible, citable document. Anything that cannot be
sourced is omitted; a dialect with no accessible source stays empty and
is documented.

## 5. Config and CLI wiring

- `config.py`: add to `SOURCE_TAGS`
  (`yoruba_dict → "Wiktionary Yoruba"`, `hausa_dict → "Wiktionary Hausa"`,
  `dialect_seeds → "Dialect Seed"`), add `None` caps, extend
  `DATASET_ORDER`.
- `seed.py`: add the new modules to `DATASETS` and `LOADERS`.
- Reseed with the full ordered load; `verify` shows the new breakdown
  with dictionary words under Standard Yoruba / Standard Hausa and any
  successfully seeded dialects no longer at zero.

## 6. Success criteria

- Yoruba gains ~4,800 dictionary words (with definitions + IPA) under
  Standard Yoruba; single-word Yoruba lookups start returning definitions.
- Hausa gains ~2,000 dictionary words under Standard Hausa.
- Every dialect that has a verifiable open source is no longer empty;
  every dialect that does not is documented as a sourced-out gap.
- Full `pytest` green, including new loader tests.
- `clean/*.csv` (including the committed dialect seed CSVs) regenerated
  and committed. Live DB reseeded and verified.
- No NC-licensed data, no audio, no schema change.

## 7. Risks

| Risk | Mitigation |
|------|------------|
| kaikki per-language JSONL removed upstream | raw JSONL kept in `raw/`, clean CSV committed; raw-pipeline fallback documented |
| Hand-built seed sets risk fabrication | Hard rule: every row cites a real accessible source; unsourced dialects stay empty and documented |
| Dictionary words collide with sentence rows on the same dialect_id | Acceptable; `source` tag distinguishes them; dedup is per-source |
| Small dialect seed volume looks token | Honest framing: a verified seed proving the pipeline fills the modelled dialect, not a claim of coverage |
