const express = require('express');
const router = express.Router();
const db = require('../db');

// GET /kitchens
router.get('/', async (req, res) => {
  try {
    const { rows } = await db.query('SELECT * FROM kitchens');
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch kitchens' });
  }
});

// GET /kitchens/:id
router.get('/:id', async (req, res) => {
  try {
    const { rows } = await db.query('SELECT * FROM kitchens WHERE id = $1', [req.params.id]);
    if (rows.length === 0) return res.status(404).json({ error: 'Kitchen not found' });
    res.json(rows[0]);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch kitchen' });
  }
});

module.exports = router;
