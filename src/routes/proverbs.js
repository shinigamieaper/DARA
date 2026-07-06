const { Router } = require('express');
const pool = require('../db');
const { buildPagination } = require('../pagination');

const router = Router();

/**
 * @swagger
 * /proverbs:
 *   get:
 *     summary: List proverbs
 *     description: >
 *       Returns dictionary entries whose part of speech is `proverb`,
 *       ordered alphabetically by headword. Both `dialect` and `language`
 *       filters are optional and can be combined. Text matching is
 *       case-insensitive (`ILIKE`).
 *     tags: [Proverbs]
 *     parameters:
 *       - in: query
 *         name: dialect
 *         schema:
 *           type: string
 *         required: false
 *         description: Filter by dialect name (e.g. `Sokoto Hausa`) or numeric dialect ID.
 *         example: Sokoto Hausa
 *       - in: query
 *         name: language
 *         schema:
 *           type: string
 *         required: false
 *         description: Filter by language name (e.g. `Hausa`) or ISO 639-3 code (e.g. `hau`).
 *         example: hau
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           minimum: 1
 *           maximum: 500
 *         required: false
 *         description: >
 *           Maximum number of proverbs to return (page size). Clamped to 500.
 *           Omit to return the full result set.
 *         example: 50
 *       - in: query
 *         name: offset
 *         schema:
 *           type: integer
 *           minimum: 0
 *         required: false
 *         description: Number of proverbs to skip before returning results (for paging).
 *         example: 0
 *     responses:
 *       200:
 *         description: A list of proverbs, including their translation metadata.
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/EntryWithMetadata'
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// GET /api/proverbs — with optional ?dialect=, ?language=, ?limit=, ?offset=
router.get('/', async (req, res) => {
  try {
    const { dialect, language } = req.query;
    const conditions = ["e.pos = 'proverb'"];
    const params = [];

    if (dialect) {
      params.push(dialect);
      conditions.push(`(d.name ILIKE $${params.length} OR d.dialect_id::text = $${params.length})`);
    }
    if (language) {
      params.push(language);
      conditions.push(`(l.name ILIKE $${params.length} OR l.iso_code ILIKE $${params.length})`);
    }

    const where = `WHERE ${conditions.join(' AND ')}`;
    const pagination = buildPagination(req.query, params);
    const query = `
      SELECT e.*, d.name AS dialect_name, l.name AS language_name, m.jsonb_data AS metadata
      FROM entries e
      JOIN dialects d ON e.dialect_id = d.dialect_id
      JOIN languages l ON d.language_id = l.language_id
      LEFT JOIN metadata m ON e.entry_id = m.entry_id
      ${where}
      ORDER BY e.headword${pagination}
    `;

    const { rows } = await pool.query(query, params);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

/**
 * @swagger
 * /proverbs/random:
 *   get:
 *     summary: Get a random proverb
 *     description: >
 *       Returns a single, randomly selected proverb. Both `dialect` and
 *       `language` filters are optional and can be combined. `limit` and
 *       `offset` do not apply to this endpoint.
 *     tags: [Proverbs]
 *     parameters:
 *       - in: query
 *         name: dialect
 *         schema:
 *           type: string
 *         required: false
 *         description: Filter by dialect name (e.g. `Sokoto Hausa`) or numeric dialect ID.
 *         example: Sokoto Hausa
 *       - in: query
 *         name: language
 *         schema:
 *           type: string
 *         required: false
 *         description: Filter by language name (e.g. `Hausa`) or ISO 639-3 code (e.g. `hau`).
 *         example: hau
 *     responses:
 *       200:
 *         description: A single random proverb, including its translation metadata.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/EntryWithMetadata'
 *       404:
 *         description: No proverb matched the given filters.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: No proverb found
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// GET /api/proverbs/random — with optional ?dialect=, ?language=
router.get('/random', async (req, res) => {
  try {
    const { dialect, language } = req.query;
    const conditions = ["e.pos = 'proverb'"];
    const params = [];

    if (dialect) {
      params.push(dialect);
      conditions.push(`(d.name ILIKE $${params.length} OR d.dialect_id::text = $${params.length})`);
    }
    if (language) {
      params.push(language);
      conditions.push(`(l.name ILIKE $${params.length} OR l.iso_code ILIKE $${params.length})`);
    }

    const where = `WHERE ${conditions.join(' AND ')}`;
    const query = `
      SELECT e.*, d.name AS dialect_name, l.name AS language_name, m.jsonb_data AS metadata
      FROM entries e
      JOIN dialects d ON e.dialect_id = d.dialect_id
      JOIN languages l ON d.language_id = l.language_id
      LEFT JOIN metadata m ON e.entry_id = m.entry_id
      ${where}
      ORDER BY RANDOM() LIMIT 1
    `;

    const { rows } = await pool.query(query, params);
    if (rows.length === 0) {
      return res.status(404).json({ error: 'No proverb found' });
    }
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
