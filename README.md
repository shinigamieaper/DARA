# DARA — Dialect-Aware Digital Repository and API for Indigenous Nigerian Languages

DARA is a REST API and linguistic repository for Yoruba, Hausa, and Igbo, built to make dialect-labelled data for these languages queryable in one place instead of scattered across separate, single-purpose datasets. It pairs normalized relational tables (languages, dialects, entries) with a JSONB metadata field per entry, so source-specific detail — sentiment labels, tonal marks, definitions, corpus splits — is preserved without forcing every dataset into the same fixed columns.

The repository holds **80,080 verified entries** across **9 dialects** in the 3 languages, drawn from 10 open-licensed sources, and runs live at:

- **API:** https://dara-ze5e.onrender.com/api
- **Interactive docs (Swagger UI):** https://dara-ze5e.onrender.com/api-docs

## Features

- Language and dialect listing, with dialect filtering by name or ID
- Entry retrieval and headword search across all three languages
- Praise-poetry (`/praise`) and proverbs (`/proverbs`) endpoints, each with a `/random` variant
- API-key-protected write operations (create, update, delete)
- Swagger/OpenAPI documentation generated from source annotations
- A Python seeding pipeline (download → transform → load → verify) that rebuilds the database from the cleaned source CSVs

## Tech stack

| Layer | Technology |
|---|---|
| API | Node.js, Express |
| Database | PostgreSQL (hybrid relational + JSONB, GIN + B-tree indexes) |
| Docs | swagger-jsdoc, swagger-ui-express |
| Data pipeline | Python, pandas, psycopg2, datasets, gdown |
| Hosting | API on Render, database on Railway, edge/CDN via Cloudflare |

## API overview

All routes are mounted under `/api`. Read endpoints are open; write endpoints require an `x-api-key` header.

| Endpoint | Method | Description |
|---|---|---|
| `/languages` | GET | List the three languages with ISO 639-3 codes |
| `/dialects` | GET | List all dialects; optional `language` filter |
| `/entries` | GET | List entries; optional `language` / `dialect` filters |
| `/entries/{id}` | GET | Get one entry with its JSONB metadata |
| `/entries` | POST 🔒 | Create an entry |
| `/entries/{id}` | PATCH 🔒 | Update an entry |
| `/entries/{id}` | DELETE 🔒 | Delete an entry |
| `/search?q=` | GET | Headword substring search across all languages |
| `/praise` | GET | Praise poetry (language filter, `q` search) |
| `/praise/random` | GET | One random praise poem |
| `/proverbs` | GET | Proverbs with translations (language filter, `q` search) |
| `/proverbs/random` | GET | One random proverb |

🔒 = requires a valid `x-api-key` header.

## Getting started

### Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (only needed if you're rebuilding the dataset yourself)
- A PostgreSQL instance (local or managed, e.g. Railway)

### Installation

```bash
git clone https://github.com/shinigamieaper/DARA.git
cd DARA
npm install
```

Create a `.env` file in the project root (never commit this file):

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
API_KEY=<a secure random string>
PORT=3000
```

> If you ever find real credentials committed to a repo or shared file, rotate them immediately and remove them from history — don't reuse a leaked value.

Start the API:

```bash
npm start        # production
npm run dev      # with nodemon, auto-restart on changes
```

The service will be available at `http://localhost:3000/api`, with docs at `http://localhost:3000/api-docs`.

### Rebuilding the dataset (optional)

The `clean/` folder ships the full cleaned corpus as 10 CSV files (one per source). To reload it into a fresh database:

```bash
pip install -r requirements.txt
python scripts/seed/<pipeline-entrypoint>.py   # download → transform → load → verify
```

The pipeline guards against double-loading and includes a verify step that checks row counts against the source files.

## Data model

Four tables:

- **languages** — name, ISO 639-3 code
- **dialects** — name, region, `language_id` foreign key
- **entries** — headword (`TEXT`), part-of-speech, `dialect_id` foreign key
- **metadata** — one JSONB record per entry for source-specific fields (definitions, sentiment labels, corpus splits, tonal/morphological notes, etc.)

Entries assigned to a language's principal dialect by default (rather than a verified dialect label) carry a `dialect_assigned_default` flag in their metadata, so verified and default labels stay distinguishable.

## Licensing

- **Source code** (this API and the Python seeding pipeline): MIT — see [`LICENSE`](./LICENSE).
- **Linguistic data** (CSV files under `clean/`, seed files, and API-served records): CC BY-SA 4.0, **with one exception** — entries derived from the MENYO-20k Yoruba proverbs are CC BY-NC 4.0 (non-commercial only). Each entry records its own source license in `jsonb_data.license`, so NC rows are filterable for commercial use cases. Full details, including per-source upstream licenses and required attribution, are in [`DATA_LICENSE.md`](./DATA_LICENSE.md).

## Limitations

- Text only — no audio, pronunciation, or phonetic data.
- A data service, not a language model — it does not translate, tag, or generate text.
- Fixed scope: Yoruba, Igbo, and Hausa, and the 9 dialects currently modelled.
- Dialect labelling depth follows the source data: Yoruba is labelled at dialect level; Igbo and Hausa material that only resolves to the language level is assigned to that language's principal dialect and flagged accordingly.
- API-first: no consumer-facing web or mobile front end is shipped.

## Contributors

Bello Jamiu Muhammad, Babalola Hamid Taiwo, and Oyekola AbdulSalam Obajuwon — Department of Mathematical and Computer Sciences, Fountain University, Osogbo.

Built as an undergraduate final-year project, supervised by Dr. (Mrs) M. A. Ogunrinde.
