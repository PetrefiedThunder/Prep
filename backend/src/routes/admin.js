const express = require('express');
const router = express.Router();
const db = require('../db');

// GET /admin/certs
router.get('/certs', async (req, res) => {
  try {
    const { rows } = await db.query('SELECT id, name, cert_level FROM kitchens');
    res.json(rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to fetch certs' });
  }
});

module.exports = router;
