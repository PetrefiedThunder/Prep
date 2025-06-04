const express = require('express');
const router = express.Router();
const db = require('../db');

// POST /bookings
router.post('/', async (req, res) => {
  try {
    const { user_id, kitchen_id, start_time, end_time } = req.body;
    const { rows } = await db.query(
      'INSERT INTO bookings (user_id, kitchen_id, start_time, end_time) VALUES ($1,$2,$3,$4) RETURNING *',
      [user_id, kitchen_id, start_time, end_time]
    );
    res.status(201).json(rows[0]);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'Failed to create booking' });
  }
});

module.exports = router;
