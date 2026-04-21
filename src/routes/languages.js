const { Router } = require('express');
const pool = require('../db');

const router = Router();

/**
 * @swagger
 * /languages:
 *   get:
 *     summary: List all languages
 *     description: Returns every language in the database, ordered alphabetically by name.
 *     tags: [Languages]
 *     responses:
 *       200:
 *         description: A list of languages.
 *         content:
 *           application/json:
 *             schema:
 *               type: array
 *               items:
 *                 $ref: '#/components/schemas/Language'
 *             example:
 *               - language_id: 1
 *                 name: Hausa
 *                 iso_code: hau
 *               - language_id: 2
 *                 name: Igbo
 *                 iso_code: ibo
 *               - language_id: 3
 *                 name: Yoruba
 *                 iso_code: yor
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// GET /api/languages — returns all languages
router.get('/', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT * FROM languages ORDER BY name');
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
