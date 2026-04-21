# Design Spec — UPDATE and DELETE for Entries

**Date:** 2026-04-21
**Status:** Approved, ready for implementation
**Scope:** Add `PATCH /api/entries/:id` and `DELETE /api/entries/:id` to complete CRUD on the `entries` resource.

---

## 1. Motivation

The API currently supports Create and Read for `entries` but lacks Update and Delete. Adding them completes the CRUD story for the primary resource, which is the standard expectation for a REST API.

Languages and dialects remain read-only by design — they are reference data that rarely changes, and keeping them immutable removes a class of accidental-damage risk.

---

## 2. Scope

**In scope**
- `PATCH /api/entries/:id` — partial update of an existing entry
- `DELETE /api/entries/:id` — hard delete of an entry and any associated metadata row
- Swagger documentation for both endpoints
- Reuse of the existing `requireApiKey` middleware for authentication

**Out of scope**
- Update/Delete on `languages` or `dialects`
- Soft delete (`deleted_at` column)
- Role-based access control (admin vs contributor keys)
- Bulk operations
- Schema changes

---

## 3. Endpoint Contracts

### 3.1 `PATCH /api/entries/:id`

**Auth:** `x-api-key` header required.

**Path parameter**
- `id` (integer) — the `entry_id` to update.

**Request body (JSON)** — at least one of:
- `headword` (string)
- `pos` (string, nullable)
- `dialect_id` (integer)

Unknown fields are silently ignored.

**Responses**

| Status | Meaning | Body |
|---|---|---|
| `200 OK` | Entry updated | The full updated entry row |
| `400 Bad Request` | Empty body (no mutable fields supplied) | `{ "error": "At least one of headword, pos, or dialect_id is required" }` |
| `401 Unauthorized` | Missing or wrong API key | `{ "error": "Unauthorized: invalid or missing API key" }` |
| `404 Not Found` | No entry with that id | `{ "error": "Entry not found" }` |
| `500 Internal Server Error` | DB or unexpected failure | `{ "error": "<message>" }` |

**SQL approach**

The handler builds the `UPDATE` statement dynamically so only supplied fields are written, mirroring the dynamic-where pattern already used in `GET /api/entries`:

```sql
UPDATE entries
SET headword = $1, pos = $2       -- only the columns present in the body
WHERE entry_id = $N
RETURNING *;
```

All values are parameterized (`$1`, `$2`, …) to preserve the project's SQL-injection-safe pattern.

If `RETURNING *` yields zero rows, respond with 404.

---

### 3.2 `DELETE /api/entries/:id`

**Auth:** `x-api-key` header required.

**Path parameter**
- `id` (integer) — the `entry_id` to delete.

**Responses**

| Status | Meaning | Body |
|---|---|---|
| `204 No Content` | Entry deleted | (empty) |
| `401 Unauthorized` | Missing or wrong API key | `{ "error": "Unauthorized: invalid or missing API key" }` |
| `404 Not Found` | No entry with that id | `{ "error": "Entry not found" }` |
| `500 Internal Server Error` | DB or unexpected failure | `{ "error": "<message>" }` |

**SQL approach — wrapped in a transaction**

Because `metadata.entry_id` references `entries.entry_id`, deleting an entry that has metadata would fail a foreign-key constraint (unless `ON DELETE CASCADE` is configured, which we do not assume). The handler therefore:

```
BEGIN;
  DELETE FROM metadata WHERE entry_id = $1;
  DELETE FROM entries  WHERE entry_id = $1 RETURNING entry_id;
COMMIT;
```

- If the entries-delete returns zero rows, ROLLBACK and respond 404.
- On any error inside the transaction, ROLLBACK and surface a 500.
- The transaction is acquired with `pool.connect()` and released in a `finally` block.

---

## 4. Authentication

Both endpoints reuse the existing `requireApiKey` middleware (`src/middleware/auth.js`) unchanged. No new environment variables, no new secrets. This matches `POST /api/entries`.

Future iteration (not in this spec): split into `API_KEY` (contribute) and `ADMIN_API_KEY` (update/delete) for principle-of-least-privilege.

---

## 5. Swagger Documentation

Both endpoints get full JSDoc `@swagger` blocks in `src/routes/entries.js` following the existing style:
- `summary`, `description`, `tags: [Entries]`
- `security: [{ ApiKeyAuth: [] }]`
- `parameters` for path id
- `requestBody` for PATCH (object with optional fields)
- `responses` for every status code in the tables above, each with a schema reference and a concrete `example`

No changes to `src/swagger.js` — the existing schemas (`Entry`, `Error`) are reused.

---

## 6. Files Touched

| File | Change |
|---|---|
| `src/routes/entries.js` | Add two new route handlers with Swagger JSDoc |

No other file is modified. No new dependencies.

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| FK constraint blocks DELETE when metadata exists | Two-step delete inside a transaction |
| A future SELECT forgets to filter deleted rows | Not applicable — we are using hard delete, not soft delete |
| Unknown fields in PATCH body cause surprise updates | Allow-list the three mutable columns; ignore everything else |
| PATCH with empty body silently no-ops | Validate that at least one allowed field is present; return 400 otherwise |
| `dialect_id` pointed at a non-existent dialect | FK constraint on `entries.dialect_id` will surface a DB error → 500. Acceptable for v1. |

---

## 8. Presentation Talking Points

- "Entries now supports full CRUD — Create, Read, Update, Delete."
- "PATCH is used for updates because it matches the REST convention of partial modification."
- "DELETE uses a database transaction to atomically remove both the entry and its metadata row, preserving referential integrity."
- "All write endpoints share a single API-key authentication layer; the natural evolution is role-based access with separate admin privileges."

---

## 9. Approval

User approved this design on 2026-04-21. Next step: writing-plans skill to produce an implementation plan.
