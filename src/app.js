require('dotenv').config();
const express = require('express');
const cors = require('cors');
const pool = require('./db');

const languagesRouter = require('./routes/languages');
const dialectsRouter = require('./routes/dialects');
const entriesRouter = require('./routes/entries');

const app = express();

app.use(cors());
app.use(express.json());

app.use('/api/languages', languagesRouter);
app.use('/api/dialects', dialectsRouter);
app.use('/api/entries', entriesRouter);

// GET /api/search?q= — full-text search on headword
app.get('/api/search', async (req, res) => {
  const { q } = req.query;
  if (!q) {
    return res.status(400).json({ error: 'Query parameter q is required' });
  }
  try {
    const { rows } = await pool.query(
      `SELECT e.*, d.name AS dialect_name, l.name AS language_name
       FROM entries e
       JOIN dialects d ON e.dialect_id = d.dialect_id
       JOIN languages l ON d.language_id = l.language_id
       WHERE e.headword ILIKE $1
       ORDER BY e.headword`,
      [`%${q}%`]
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
