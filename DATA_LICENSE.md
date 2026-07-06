# Data Licence

The linguistic data in this repository — the CSV files under `clean/` and the
hand-curated seed files under `scripts/seed/seed_data/`, together with the
records served by the API — is licensed under the
**Creative Commons Attribution-ShareAlike 4.0 International Licence (CC BY-SA 4.0)**.

Full text: https://creativecommons.org/licenses/by-sa/4.0/legalcode
Summary: https://creativecommons.org/licenses/by-sa/4.0/

CC BY-SA 4.0 is used for the aggregated dataset because some upstream sources
(the Wiktionary-derived dictionaries) are themselves CC BY-SA, whose
share-alike term propagates to any collection that includes them. You are free
to share and adapt the data, including commercially, provided you give
attribution and license your derivatives under the same terms.

> **⚠️ Non-commercial exception.** One source — the **MENYO-20k** Yoruba
> proverbs (part of the `Yoruba Proverbs` source tag) — is licensed
> **CC BY-NC 4.0 (non-commercial)**. Entries derived from it carry
> `"license": "CC BY-NC 4.0"` in their `jsonb_data`. The CC BY-SA 4.0 terms
> above therefore apply to the dataset **for non-commercial use**. For
> commercial reuse, exclude the MENYO-20k-derived rows (filter
> `metadata.jsonb_data->>'license' = 'CC BY-NC 4.0'`); the remaining data is
> commercially reusable under CC BY-SA 4.0. Each entry records its own source
> licence, so this is filterable per row.

> **Note:** The MIT licence in `LICENSE` covers the source code (the Node.js
> API and the Python seeding pipeline). This file covers the data only.

## Attribution of upstream sources

Each entry's `jsonb_data` records the `source` (and, where relevant, the
`license` and `origin`) of that specific entry. The upstream sources and their
licences are:

| Source (metadata `source`) | Provider | Upstream licence |
|---|---|---|
| IgboAPI | Nkọwa okwu / IgboAPI (`github.com/nkowaokwu/igbo_api`) | Apache-2.0 |
| YorùLect | YorùLect project (`github.com/orevaahia/yorulect`) | research / open |
| VOA Hausa | Hausa VOA NER (`uds-lsv/transfer-distant-transformer-african`) | open |
| NaijaSenti | HausaNLP NaijaSenti (`hausanlp/NaijaSenti`) | open |
| Wiktionary Yoruba | Wiktionary via kaikki.org (Wiktextract) | CC BY-SA 3.0 / 4.0 |
| Wiktionary Hausa | Wiktionary via kaikki.org (Wiktextract) | CC BY-SA 3.0 / 4.0 |
| Ehugbo NT | Eze-Mbeyu et al. (2025), *E.hugbo Ka!*; HF `Ukachi/NLP-Ehugbo` | Apache-2.0 |
| Dialect Seed (Enuani) | Nwabudike (2025), *The Peace Weaving Wisdom of Enuani Proverbs*, AJL2C 8(2) | CC BY 4.0 |
| Dialect Seed (Ehugbo) | Aja, Emeka-Nwobia & Onu (2018), *A Lexicostatistical Survey of Afikpo-Igbo Varieties*, WASJ 36(9) | cited academic use |
| Dialect Seed (Sokoto Hausa) | Garba, Modu & Jibir, *Descriptive Analysis of Variations in Three Hausa Dialects*, SLUK | cited academic use |
| Yoruba Proverbs | mxronga `yoruba-proverbs-parallel-corpora` (HF) **+** MENYO-20k (Adelani et al. 2021) | Apache-2.0 **+ CC BY-NC 4.0** (see NC note above) |
| Hausa Proverbs | Merrick, G. (1905). *Hausa Proverbs*. Internet Archive | Public Domain |
| Oriki | DARA Oríkì dataset (project-owned; migrated from the Oríkì generator project) | CC BY-SA 4.0 |

When reusing the data, attribute both this repository and the relevant upstream
source(s) listed above.
