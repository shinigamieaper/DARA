const { Router } = require('express');
const pool = require('../db');

const router = Router();

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
