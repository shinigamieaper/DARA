const { Router } = require('express');
const pool = require('../db');
const requireApiKey = require('../middleware/auth');

const router = Router();

/**
 * @swagger
 * /entries:
 *   get:
 *     summary: List entries
 *     description: >
 *       Returns dictionary entries, ordered alphabetically by headword.
 *       Both `dialect` and `language` filters are optional and can be
 *       combined. Text matching is case-insensitive (`ILIKE`).
 *     tags: [Entries]
 *     parameters:
 *       - in: query
 *         name: dialect
 *         schema:
 *           type: string
 *         required: false
 *         description: Filter by dialect name (e.g. `Ekiti Yoruba`) or numeric dialect ID.
 *         example: Ekiti Yoruba
 *       - in: query
 *         name: language
 *         schema:
 *           type: string
 *         required: false
 *         description: Filter by language name (e.g. `Yoruba`) or ISO 639-3 code (e.g. `yor`).
 *         example: yor
 *     responses:
 *       200:
 *         description: A list of entries.
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Entry'
 *             example:
 *               - entry_id: 42
 *                 headword: omi
 *                 pos: noun
 *                 dialect_id: 3
 *                 dialect_name: Ekiti Yoruba
 *                 language_name: Yoruba
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// GET /api/entries — with optional ?dialect= and ?language= filters
router.get('/', async (req, res) => {
  try {
    const { dialect, language } = req.query;
    const conditions = [];
    const params = [];

    if (dialect) {
      params.push(dialect);
      conditions.push(`(d.name ILIKE $${params.length} OR d.dialect_id::text = $${params.length})`);
    }
    if (language) {
      params.push(language);
      conditions.push(`(l.name ILIKE $${params.length} OR l.iso_code ILIKE $${params.length})`);
    }

    const where = conditions.length ? `WHERE ${conditions.join(' AND ')}` : '';
    const query = `
      SELECT e.*, d.name AS dialect_name, l.name AS language_name
      FROM entries e
      JOIN dialects d ON e.dialect_id = d.dialect_id
      JOIN languages l ON d.language_id = l.language_id
      ${where}
      ORDER BY e.headword
    `;

    const { rows } = await pool.query(query, params);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * @swagger
 * /entries/{id}:
 *   get:
 *     summary: Get a single entry
 *     description: >
 *       Returns a dictionary entry by its numeric ID, including dialect and
 *       language names and any associated metadata (a free-form JSON object).
 *     tags: [Entries]
 *     parameters:
 *       - in: path
 *         name: id
 *         required: true
 *         schema:
 *           type: integer
 *         description: The numeric entry ID.
 *         example: 42
 *     responses:
 *       200:
 *         description: The requested entry with metadata.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/EntryWithMetadata'
 *             example:
 *               entry_id: 42
 *               headword: omi
 *               pos: noun
 *               dialect_id: 3
 *               dialect_name: Ekiti Yoruba
 *               language_name: Yoruba
 *               metadata:
 *                 definition: water
 *                 tone: LH
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
// GET /api/entries/:id — returns single entry with metadata joined
router.get('/:id', async (req, res) => {
  try {
    const { rows } = await pool.query(
      `SELECT e.*, d.name AS dialect_name, l.name AS language_name, m.jsonb_data AS metadata
       FROM entries e
       JOIN dialects d ON e.dialect_id = d.dialect_id
       JOIN languages l ON d.language_id = l.language_id
       LEFT JOIN metadata m ON e.entry_id = m.entry_id
       WHERE e.entry_id = $1`,
      [req.params.id]
    );
    if (rows.length === 0) {
      return res.status(404).json({ error: 'Entry not found' });
    }
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * @swagger
 * /entries:
 *   post:
 *     summary: Create an entry
 *     description: >
 *       Inserts a new dictionary entry. Requires a valid API key in the
 *       `x-api-key` request header.
 *     tags: [Entries]
 *     security:
 *       - ApiKeyAuth: []
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [headword, dialect_id]
 *             properties:
 *               headword:
 *                 type: string
 *                 description: The word or phrase being recorded.
 *                 example: omi
 *               dialect_id:
 *                 type: integer
 *                 description: ID of the dialect this entry belongs to.
 *                 example: 3
 *               pos:
 *                 type: string
 *                 description: Part of speech (e.g. noun, verb). Optional.
 *                 example: noun
 *     responses:
 *       201:
 *         description: Entry created successfully.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Entry'
 *             example:
 *               entry_id: 99
 *               headword: omi
 *               pos: noun
 *               dialect_id: 3
 *       400:
 *         description: Missing required fields.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: headword and dialect_id are required
 *       401:
 *         description: Missing or invalid API key.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: "Unauthorized: invalid or missing API key"
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// POST /api/entries — protected by x-api-key middleware
router.post('/', requireApiKey, async (req, res) => {
  try {
    const { headword, pos, dialect_id } = req.body;
    if (!headword || !dialect_id) {
      return res.status(400).json({ error: 'headword and dialect_id are required' });
    }

    const { rows } = await pool.query(
      'INSERT INTO entries (headword, pos, dialect_id) VALUES ($1, $2, $3) RETURNING *',
      [headword, pos ?? null, dialect_id]
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

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

module.exports = router;
