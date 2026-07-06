require('dotenv').config();
const express = require('express');
const cors = require('cors');
const swaggerUi = require('swagger-ui-express');
const pool = require('./db');
const swaggerSpec = require('./swagger');
const { buildPagination } = require('./pagination');

const languagesRouter = require('./routes/languages');
const dialectsRouter = require('./routes/dialects');
const entriesRouter = require('./routes/entries');
const proverbsRouter = require('./routes/proverbs');
const praiseRouter = require('./routes/praise');

const app = express();

app.use(cors());
app.use(express.json());

// Swagger UI — available at /api-docs
app.use('/api-docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));

// Redirect root to the API docs
app.get('/', (req, res) => res.redirect('/api-docs'));

app.use('/api/languages', languagesRouter);
app.use('/api/dialects', dialectsRouter);
app.use('/api/entries', entriesRouter);
app.use('/api/proverbs', proverbsRouter);
app.use('/api/praise', praiseRouter);

/**
 * @swagger
 * /search:
 *   get:
 *     summary: Search entries by headword
 *     description: >
 *       Full-text substring search across all entry headwords.
 *       Returns matching entries with their dialect and language names,
 *       ordered alphabetically by headword.
 *     tags: [Search]
 *     parameters:
 *       - in: query
 *         name: q
 *         required: true
 *         schema:
 *           type: string
 *         description: Substring to search for (case-insensitive).
 *         example: omi
 *       - in: query
 *         name: limit
 *         schema:
 *           type: integer
 *           minimum: 1
 *           maximum: 500
 *         required: false
 *         description: Maximum number of matches to return (clamped to 500). Omit to return all matches.
 *         example: 50
 *       - in: query
 *         name: offset
 *         schema:
 *           type: integer
 *           minimum: 0
 *         required: false
 *         description: Number of matches to skip before returning results.
 *         example: 0
 *     responses:
 *       200:
 *         description: List of matching entries.
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
 *       400:
 *         description: Missing required query parameter `q`.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 *             example:
 *               error: Query parameter q is required
 *       500:
 *         description: Database error.
 *         content:
 *           application/json:
 *             schema:
 *               $ref: '#/components/schemas/Error'
 */
// GET /api/search?q= — full-text search on headword
app.get('/api/search', async (req, res) => {
  const { q } = req.query;
  if (!q) {
    return res.status(400).json({ error: 'Query parameter q is required' });
  }
  try {
    const params = [`%${q}%`];
    const pagination = buildPagination(req.query, params);
    const { rows } = await pool.query(
      `SELECT e.*, d.name AS dialect_name, l.name AS language_name
       FROM entries e
       JOIN dialects d ON e.dialect_id = d.dialect_id
       JOIN languages l ON d.language_id = l.language_id
       WHERE e.headword ILIKE $1
       ORDER BY e.headword${pagination}`,
      params
    );
    res.json(rows);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});

module.exports = app;
