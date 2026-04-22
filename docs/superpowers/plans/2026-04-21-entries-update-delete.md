# Entries UPDATE and DELETE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `PATCH /api/entries/:id` and `DELETE /api/entries/:id` to complete CRUD on the entries resource.

**Architecture:** Two new route handlers in the existing entries router. PATCH builds a dynamic parameterized `UPDATE` so only supplied fields are written. DELETE uses a transaction to atomically remove the metadata row and the entry row together, preserving referential integrity.

**Tech Stack:** Node.js 18+, Express 4, `pg` Postgres client, swagger-jsdoc, swagger-ui-express.

**Spec:** `docs/superpowers/specs/2026-04-21-entries-update-delete-design.md`

**Note on testing:** This codebase has no automated test framework set up. Adding Jest + Supertest the night before the presentation is scope creep. Instead, every task includes a precise **manual verification** step using `curl` against a locally-running server — the same pattern the existing codebase relies on.

---

## File Structure

**Only one file is touched.** The plan adds two route handlers to the existing entries router. No new files, no new dependencies, no schema changes.

| File | Responsibility | Change type |
|---|---|---|
| `src/routes/entries.js` | All `/api/entries*` route handlers | Modify — add PATCH and DELETE handlers |

---

## Preconditions (read before starting)

Before Task 1, confirm these are true on your development machine:

1. `.env` contains `DATABASE_URL`, `API_KEY`, and optionally `PORT`.
2. The Postgres database has at least one row in `entries` you are willing to mutate — grab its `entry_id` with:
   ```bash
   psql "$DATABASE_URL" -c "SELECT entry_id, headword, pos, dialect_id FROM entries LIMIT 3;"
   ```
3. `npm install` has completed (dependencies for swagger-jsdoc, swagger-ui-express are already in `package.json`).
4. You can start the server locally with `npm run dev` and `curl http://localhost:3000/api/languages` returns a 200 JSON list.

If any of these fail, fix before proceeding — these tasks assume a working baseline.

---

## Task 1: Add `PATCH /api/entries/:id` handler and Swagger docs

**Files:**
- Modify: `src/routes/entries.js` — append a new route handler below the existing POST handler (before `module.exports = router;`)

- [ ] **Step 1: Open `src/routes/entries.js` and locate the end of the POST handler**

Find the last line of the POST handler, which ends with:
```js
});
```
immediately before
```js
module.exports = router;
```

You will insert the new PATCH handler between these two lines.

- [ ] **Step 2: Insert the PATCH handler with full Swagger JSDoc**

Paste this block immediately before `module.exports = router;`:

```js
/**
 * @swagger
 * /entries/{id}:
 *   patch:
 *     summary: Update an entry
 *     description: >
 *       Partial update of an existing entry. Only the fields supplied in the
 *       request body are changed; omitted fields are left untouched.
 *       Requires a valid `x-api-key` header.
 *     tags: [Entries]
 *     security:
 *       - ApiKeyAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: The numeric entry ID.
 *         example: 42
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             minProperties: 1
 *             properties:
 *               headword:
 *                 type: string
 *                 example: omi
 *               pos:
 *                 type: string
 *                 nullable: true
 *                 example: verb
 *               dialect_id:
 *                 type: integer
 *                 example: 3
 *     responses:
 *       200:
 *         description: Entry updated successfully.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Entry'
 *             example:
 *               entry_id: 42
 *               headword: omi
 *               pos: verb
 *               dialect_id: 3
 *       400:
 *         description: No updatable fields supplied.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: At least one of headword, pos, or dialect_id is required
 *       401:
 *         description: Missing or invalid API key.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: "Unauthorized: invalid or missing API key"
 *       404:
 *         description: No entry found with the given ID.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: Entry not found
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// PATCH /api/entries/:id — protected by x-api-key middleware
router.patch('/:id', requireApiKey, async (req, res) => {
  try {
    const allowed = ['headword', 'pos', 'dialect_id'];
    const sets = [];
    const params = [];

    for (const field of allowed) {
      if (req.body[field] !== undefined) {
        params.push(req.body[field]);
        sets.push(`${field} = $${params.length}`);
      }
    }

    if (sets.length === 0) {
      return res.status(400).json({
        error: 'At least one of headword, pos, or dialect_id is required'
      });
    }

    params.push(req.params.id);
    const query = `
      UPDATE entries
      SET ${sets.join(', ')}
      WHERE entry_id = $${params.length}
      RETURNING *
    `;

    const { rows } = await pool.query(query, params);
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Entry not found' });
    }
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});
```

- [ ] **Step 3: Start the dev server**

Run:
```bash
npm run dev
```
Expected: console prints `Server running on port 3000`. If nodemon was already running, it will auto-reload on save.

- [ ] **Step 4: Verify the Swagger spec still loads**

In a separate terminal:
```bash
curl -s http://localhost:3000/api-docs/swagger-ui-init.js | head -1
```
Expected: a line of JS starting with `var options =`. If it errors, the JSDoc block has a YAML syntax problem — most commonly wrong indentation.

Also open `http://localhost:3000/api-docs` in a browser and confirm **PATCH /entries/{id}** now appears in the "Entries" section with the padlock icon.

- [ ] **Step 5: Manual verification — happy path**

Replace `<KEY>` with your `API_KEY` value and `<ID>` with an existing `entry_id`:
```bash
curl -i -X PATCH http://localhost:3000/api/entries/<ID> \
  -H "Content-Type: application/json" \
  -H "x-api-key: <KEY>" \
  -d '{"pos":"verb"}'
```
Expected: `HTTP/1.1 200 OK` and the response body shows the updated row with `pos` changed and `headword`/`dialect_id` unchanged.

Confirm the change persisted:
```bash
curl -s http://localhost:3000/api/entries/<ID> | jq
```
Expected: the JSON shows the new `pos` value.

- [ ] **Step 6: Manual verification — error paths**

Missing API key:
```bash
curl -i -X PATCH http://localhost:3000/api/entries/<ID> \
  -H "Content-Type: application/json" \
  -d '{"pos":"verb"}'
```
Expected: `HTTP/1.1 401` and `{"error":"Unauthorized: invalid or missing API key"}`.

Empty body:
```bash
curl -i -X PATCH http://localhost:3000/api/entries/<ID> \
  -H "Content-Type: application/json" \
  -H "x-api-key: <KEY>" \
  -d '{}'
```
Expected: `HTTP/1.1 400` and `{"error":"At least one of headword, pos, or dialect_id is required"}`.

Nonexistent entry:
```bash
curl -i -X PATCH http://localhost:3000/api/entries/999999 \
  -H "Content-Type: application/json" \
  -H "x-api-key: <KEY>" \
  -d '{"pos":"verb"}'
```
Expected: `HTTP/1.1 404` and `{"error":"Entry not found"}`.

- [ ] **Step 7: Commit**

```bash
git add src/routes/entries.js
git commit -m "add PATCH /api/entries/:id for partial entry updates

Uses dynamic parameterized UPDATE so only supplied fields are
written. Protected by the existing x-api-key middleware.
Includes Swagger documentation."
```

---

## Task 2: Add `DELETE /api/entries/:id` handler and Swagger docs

**Files:**
- Modify: `src/routes/entries.js` — append a second new route handler directly after the PATCH handler from Task 1

- [ ] **Step 1: Locate the end of the PATCH handler**

Find the closing `});` of the PATCH handler you just added. Insert the DELETE handler immediately below it (still above `module.exports = router;`).

- [ ] **Step 2: Insert the DELETE handler with full Swagger JSDoc**

```js
/**
 * @swagger
 * /entries/{id}:
 *   delete:
 *     summary: Delete an entry
 *     description: >
 *       Permanently deletes an entry and any associated metadata row.
 *       The two deletes run inside a single database transaction so
 *       either both succeed or neither is applied. Requires `x-api-key`.
 *     tags: [Entries]
 *     security:
 *       - ApiKeyAuth: []
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: The numeric entry ID.
 *         example: 42
 *     responses:
 *       204:
 *         description: Entry deleted successfully (no body returned).
 *       401:
 *         description: Missing or invalid API key.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: "Unauthorized: invalid or missing API key"
 *       404:
 *         description: No entry found with the given ID.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: Entry not found
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// DELETE /api/entries/:id — protected by x-api-key middleware
router.delete('/:id', requireApiKey, async (req, res) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    await client.query('DELETE FROM metadata WHERE entry_id = $1', [req.params.id]);
    const { rowCount } = await client.query(
      'DELETE FROM entries WHERE entry_id = $1',
      [req.params.id]
    );

    if (rowCount === 0) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: 'Entry not found' });
    }

    await client.query('COMMIT');
    res.status(204).send();
  } catch (err) {
    await client.query('ROLLBACK');
    res.status(500).json({ error: err.message });
  } finally {
    client.release();
  }
});
```

**Why the transaction:** deleting an entry that has a metadata row would violate the foreign key if we deleted only `entries`. So we delete from `metadata` first, then `entries`. The transaction ensures atomicity — if the second delete fails, the first is rolled back.

**Why `client.connect()` instead of `pool.query()`:** transactions must run on a single connection (so `BEGIN` and `COMMIT` refer to the same session). `pool.connect()` gives us a dedicated client; `finally { client.release(); }` returns it to the pool.

- [ ] **Step 3: Verify the Swagger spec still loads**

With the dev server still running (nodemon auto-reloads), refresh `http://localhost:3000/api-docs` and confirm **DELETE /entries/{id}** now appears with the padlock icon.

If the page errors, the JSDoc block has a YAML indentation issue — review Step 2.

- [ ] **Step 4: Manual verification — setup a throwaway entry**

Because DELETE is destructive, create a test entry you're willing to throw away:
```bash
curl -i -X POST http://localhost:3000/api/entries \
  -H "Content-Type: application/json" \
  -H "x-api-key: <KEY>" \
  -d '{"headword":"__test_delete__","pos":"noun","dialect_id":<EXISTING_DIALECT_ID>}'
```
Expected: `HTTP/1.1 201` with a body containing the new `entry_id`. Note it — refer to it below as `<TEST_ID>`.

- [ ] **Step 5: Manual verification — missing API key**

```bash
curl -i -X DELETE http://localhost:3000/api/entries/<TEST_ID>
```
Expected: `HTTP/1.1 401` and `{"error":"Unauthorized: invalid or missing API key"}`.
Verify the entry still exists:
```bash
curl -s http://localhost:3000/api/entries/<TEST_ID>
```
Expected: the entry JSON (NOT a 404).

- [ ] **Step 6: Manual verification — nonexistent ID**

```bash
curl -i -X DELETE http://localhost:3000/api/entries/999999 \
  -H "x-api-key: <KEY>"
```
Expected: `HTTP/1.1 404` and `{"error":"Entry not found"}`.

- [ ] **Step 7: Manual verification — happy path**

```bash
curl -i -X DELETE http://localhost:3000/api/entries/<TEST_ID> \
  -H "x-api-key: <KEY>"
```
Expected: `HTTP/1.1 204 No Content` (no body).

Confirm the entry is gone:
```bash
curl -i http://localhost:3000/api/entries/<TEST_ID>
```
Expected: `HTTP/1.1 404` and `{"error":"Entry not found"}`.

- [ ] **Step 8: Manual verification — deleting a second time is a 404 (idempotency check)**

```bash
curl -i -X DELETE http://localhost:3000/api/entries/<TEST_ID> \
  -H "x-api-key: <KEY>"
```
Expected: `HTTP/1.1 404`. The first DELETE removed the entry; a second should cleanly return not-found rather than error.

- [ ] **Step 9: Commit**

```bash
git add src/routes/entries.js
git commit -m "add DELETE /api/entries/:id with transactional metadata cleanup

Deletes the entry and any associated metadata row inside a single
transaction to preserve referential integrity. Returns 204 on
success, 404 if the entry does not exist. Protected by the existing
x-api-key middleware. Includes Swagger documentation."
```

---

## Task 3: Push to GitHub to trigger the Render deploy

**Files:** None modified — deploy-only task.

- [ ] **Step 1: Confirm the working tree is clean and two new commits are ahead of origin**

Run:
```bash
git status && git log --oneline origin/main..HEAD
```
Expected:
- `git status` reports `working tree clean`.
- The log shows exactly two commits: the PATCH commit from Task 1 and the DELETE commit from Task 2.

If either commit is missing, go back and commit before proceeding.

- [ ] **Step 2: Push to GitHub**

```bash
git push origin main
```
Expected output ends with `main -> main`.

- [ ] **Step 3: Watch Render auto-deploy**

Open the Render dashboard → your service → **Events** tab. Within ~30 seconds you should see a new "Deploy started" event triggered by the GitHub push. Wait for it to reach "Deploy live."

- [ ] **Step 4: Smoke-test the live endpoints**

Replace `<KEY>` with your production `API_KEY` (set in Render env vars) and `<ID>` with a real entry id:

```bash
# PATCH — verify the endpoint exists and is protected
curl -i -X PATCH https://dara-ze5e.onrender.com/api/entries/<ID> \
  -H "Content-Type: application/json" \
  -d '{"pos":"noun"}'
```
Expected: `HTTP/1.1 401` (no key sent — proves the endpoint is deployed AND protected).

```bash
# DELETE — same check
curl -i -X DELETE https://dara-ze5e.onrender.com/api/entries/999999
```
Expected: `HTTP/1.1 401` (no key sent).

Also visit `https://dara-ze5e.onrender.com/api-docs` and confirm both **PATCH** and **DELETE** on `/entries/{id}` are visible with padlock icons.

---

## Post-completion sanity check (optional but recommended)

Before your presentation, walk through the Swagger UI at the live URL and click "Try it out" on each endpoint. Seeing them all work in a browser is the most convincing demo to a panel.

Talking points for the panel:
- "Entries now supports full CRUD — Create, Read, Update, Delete."
- "PATCH is used for partial updates, which is the REST convention."
- "DELETE is wrapped in a database transaction so the entry and its metadata are removed atomically."
- "All write operations share the same API-key middleware; role-based access is a future enhancement."
