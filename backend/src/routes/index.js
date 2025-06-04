const express = require('express');
const router = express.Router();

const kitchens = require('./kitchens');
const bookings = require('./bookings');
const admin = require('./admin');

router.use('/kitchens', kitchens);
router.use('/bookings', bookings);
router.use('/admin', admin);

module.exports = router;
