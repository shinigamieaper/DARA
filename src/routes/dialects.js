const { Router } = require('express');
const pool = require('../db');

const router = Router();

/**
 * @swagger
 * /dialects:
 *   get:
 *     summary: List dialects
 *     description: >
 *       Returns all dialects, ordered alphabetically by name.
 *       Pass the optional `language` parameter to filter results to dialects
 *       that belong to a specific language (matched case-insensitively against
 *       the language name or ISO 639-3 code).
 *     tags: [Dialects]
 *     parameters:
 *       - in: query
 *         name: language
 *         schema:
 *           type: string
 *         required: false
 *         description: >
 *           Filter by parent language name (e.g. `Yoruba`) or ISO 639-3 code
 *           (e.g. `yor`). Case-insensitive.
 *         example: Yoruba
 *     responses:
 *       200:
 *         description: A list of dialects.
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Dialect'
 *             example:
 *               - dialect_id: 3
 *                 language_id: 3
 *                 name: Ekiti Yoruba
 *               - dialect_id: 4
 *                 language_id: 3
 *                 name: Oyo Yoruba
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// GET /api/dialects — with optional ?language= filter (name or iso_code)
router.get('/', async (req, res) => {
  try {
    const { language } = req.query;

    let query, params;
    if (language) {
      query = `
        SELECT d.*
        FROM dialects d
        JOIN languages l ON d.language_id = l.language_id
        WHERE l.name ILIKE $1 OR l.iso_code ILIKE $1
        ORDER BY d.name
      `;
      params = [language];
    } else {
      query = 'SELECT * FROM dialects ORDER BY name';
      params = [];
    }

    const { rows } = await pool.query(query, params);
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
