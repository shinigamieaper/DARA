const { Router } = require('express');
const pool = require('../db');

const router = Router();

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
