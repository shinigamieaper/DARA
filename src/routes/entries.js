const { Router } = require('express');
const pool = require('../db');
const requireApiKey = require('../middleware/auth');

const router = Router();

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

module.exports = router;
