import { describe, it, before, after } from 'node:test';
import assert from 'node:assert';
import { Pool } from 'pg';
import Redis from 'ioredis';
import { BookingService } from '../services/BookingService';
import { AvailabilityService } from '../services/AvailabilityService';

describe('BookingService', () => {
  let db: Pool;
  let redis: Redis;
  let bookingService: BookingService;
  let availabilityService: AvailabilityService;

  const TEST_DB_URL = process.env.TEST_DATABASE_URL || 'postgresql://postgres:postgres@localhost:5432/prepchef_test';
  const TEST_REDIS_URL = process.env.TEST_REDIS_URL || 'redis://localhost:6379/1';

  before(async () => {
    // Initialize test database and Redis
    db = new Pool({ connectionString: TEST_DB_URL });
    redis = new Redis(TEST_REDIS_URL);

    await redis.connect().catch(() => {});

    bookingService = new BookingService(db, redis);
    availabilityService = new AvailabilityService(db, redis);

    // Create test tables
    await db.query(`
      CREATE TABLE IF NOT EXISTS bookings (
        booking_id UUID PRIMARY KEY,
        kitchen_id UUID NOT NULL,
        user_id UUID NOT NULL,
        start_time TIMESTAMP NOT NULL,
        end_time TIMESTAMP NOT NULL,
        status VARCHAR(20) NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
      )
    `);

    // Clear test data
    await db.query('TRUNCATE TABLE bookings CASCADE');
    await redis.flushdb();
  });

  after(async () => {
    // Cleanup
    await db.query('DROP TABLE IF EXISTS bookings CASCADE');
    await db.end();
    await redis.quit();
  });

  describe('createBooking - Success Cases', () => {
    it('should create a booking with status pending', async () => {
      const kitchen_id = '11111111-1111-1111-1111-111111111111';
      const user_id = '22222222-2222-2222-2222-222222222222';
      const start_time = new Date(Date.now() + 24 * 60 * 60 * 1000); // Tomorrow
      const end_time = new Date(start_time.getTime() + 2 * 60 * 60 * 1000); // +2 hours

      const booking = await bookingService.createBooking({
        kitchen_id,
        user_id,
        start_time,
        end_time
      });

      assert.ok(booking.booking_id, 'Booking ID should be generated');
      assert.strictEqual(booking.status, 'pending', 'Status should be pending');
      assert.strictEqual(booking.kitchen_id, kitchen_id);
      assert.strictEqual(booking.user_id, user_id);
      assert.ok(booking.created_at);

      // Verify Redis lock was created
      const lockKey = `booking:lock:${kitchen_id}:${start_time.toISOString()}:${end_time.toISOString()}`;
      const lock = await redis.get(lockKey);
      assert.strictEqual(lock, booking.booking_id, 'Redis lock should be created with booking ID');

      // Cleanup
      await db.query('DELETE FROM bookings WHERE booking_id = $1', [booking.booking_id]);
      await redis.del(lockKey);
    });

    it('should create booking with valid minimum duration (1 hour)', async () => {
      const kitchen_id = '33333333-3333-3333-3333-333333333333';
      const user_id = '44444444-4444-4444-4444-444444444444';
      const start_time = new Date(Date.now() + 48 * 60 * 60 * 1000); // Day after tomorrow
      const end_time = new Date(start_time.getTime() + 60 * 60 * 1000); // Exactly 1 hour

      const booking = await bookingService.createBooking({
        kitchen_id,
        user_id,
        start_time,
        end_time
      });

      assert.ok(booking.booking_id);
      assert.strictEqual(booking.status, 'pending');

      // Cleanup
      await db.query('DELETE FROM bookings WHERE booking_id = $1', [booking.booking_id]);
    });
  });

  describe('createBooking - Double-Book Rejection', () => {
    it('should reject overlapping booking with same start and end time', async () => {
      const kitchen_id = '55555555-5555-5555-5555-555555555555';
      const user_id_1 = '66666666-6666-6666-6666-666666666666';
      const user_id_2 = '77777777-7777-7777-7777-777777777777';
      const start_time = new Date(Date.now() + 72 * 60 * 60 * 1000);
      const end_time = new Date(start_time.getTime() + 3 * 60 * 60 * 1000);

      // Create first booking
      const booking1 = await bookingService.createBooking({
        kitchen_id,
        user_id: user_id_1,
        start_time,
        end_time
      });

      assert.ok(booking1.booking_id);

      // Try to create overlapping booking - should fail
      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id: user_id_2,
            start_time,
            end_time
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('not available'));
          return true;
        },
        'Should reject overlapping booking'
      );

      // Cleanup
      await db.query('DELETE FROM bookings WHERE booking_id = $1', [booking1.booking_id]);
    });

    it('should reject booking that starts during existing booking', async () => {
      const kitchen_id = '88888888-8888-8888-8888-888888888888';
      const user_id_1 = '99999999-9999-9999-9999-999999999999';
      const user_id_2 = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

      const existing_start = new Date(Date.now() + 96 * 60 * 60 * 1000);
      const existing_end = new Date(existing_start.getTime() + 4 * 60 * 60 * 1000);

      // Create first booking
      const booking1 = await bookingService.createBooking({
        kitchen_id,
        user_id: user_id_1,
        start_time: existing_start,
        end_time: existing_end
      });

      // Try to create booking that starts during existing booking
      const new_start = new Date(existing_start.getTime() + 2 * 60 * 60 * 1000); // 2 hours into existing
      const new_end = new Date(existing_end.getTime() + 2 * 60 * 60 * 1000);

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id: user_id_2,
            start_time: new_start,
            end_time: new_end
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('not available'));
          return true;
        },
        'Should reject booking that starts during existing booking'
      );

      // Cleanup
      await db.query('DELETE FROM bookings WHERE booking_id = $1', [booking1.booking_id]);
    });

    it('should reject booking that ends during existing booking', async () => {
      const kitchen_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
      const user_id_1 = 'cccccccc-cccc-cccc-cccc-cccccccccccc';
      const user_id_2 = 'dddddddd-dddd-dddd-dddd-dddddddddddd';

      const existing_start = new Date(Date.now() + 120 * 60 * 60 * 1000);
      const existing_end = new Date(existing_start.getTime() + 4 * 60 * 60 * 1000);

      // Create first booking
      const booking1 = await bookingService.createBooking({
        kitchen_id,
        user_id: user_id_1,
        start_time: existing_start,
        end_time: existing_end
      });

      // Try to create booking that ends during existing booking
      const new_start = new Date(existing_start.getTime() - 2 * 60 * 60 * 1000); // Starts 2 hours before
      const new_end = new Date(existing_start.getTime() + 1 * 60 * 60 * 1000); // Ends 1 hour into existing

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id: user_id_2,
            start_time: new_start,
            end_time: new_end
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('not available'));
          return true;
        },
        'Should reject booking that ends during existing booking'
      );

      // Cleanup
      await db.query('DELETE FROM bookings WHERE booking_id = $1', [booking1.booking_id]);
    });

    it('should reject booking that completely contains existing booking', async () => {
      const kitchen_id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee';
      const user_id_1 = 'ffffffff-ffff-ffff-ffff-ffffffffffff';
      const user_id_2 = '00000000-0000-0000-0000-000000000000';

      const existing_start = new Date(Date.now() + 144 * 60 * 60 * 1000);
      const existing_end = new Date(existing_start.getTime() + 2 * 60 * 60 * 1000);

      // Create first booking
      const booking1 = await bookingService.createBooking({
        kitchen_id,
        user_id: user_id_1,
        start_time: existing_start,
        end_time: existing_end
      });

      // Try to create booking that completely contains existing
      const new_start = new Date(existing_start.getTime() - 1 * 60 * 60 * 1000);
      const new_end = new Date(existing_end.getTime() + 1 * 60 * 60 * 1000);

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id: user_id_2,
            start_time: new_start,
            end_time: new_end
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('not available'));
          return true;
        },
        'Should reject booking that completely contains existing booking'
      );

      // Cleanup
      await db.query('DELETE FROM bookings WHERE booking_id = $1', [booking1.booking_id]);
    });
  });

  describe('createBooking - Invalid Time Ranges', () => {
    it('should reject booking with start time after end time', async () => {
      const kitchen_id = '12345678-1234-1234-1234-123456789012';
      const user_id = '23456789-2345-2345-2345-234567890123';
      const start_time = new Date(Date.now() + 24 * 60 * 60 * 1000);
      const end_time = new Date(start_time.getTime() - 1 * 60 * 60 * 1000); // Before start

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id,
            start_time,
            end_time
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('before end_time'));
          return true;
        },
        'Should reject booking with invalid time range'
      );
    });

    it('should reject booking in the past', async () => {
      const kitchen_id = '34567890-3456-3456-3456-345678901234';
      const user_id = '45678901-4567-4567-4567-456789012345';
      const start_time = new Date(Date.now() - 24 * 60 * 60 * 1000); // Yesterday
      const end_time = new Date(start_time.getTime() + 2 * 60 * 60 * 1000);

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id,
            start_time,
            end_time
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('past'));
          return true;
        },
        'Should reject booking in the past'
      );
    });

    it('should reject booking shorter than minimum duration (1 hour)', async () => {
      const kitchen_id = '56789012-5678-5678-5678-567890123456';
      const user_id = '67890123-6789-6789-6789-678901234567';
      const start_time = new Date(Date.now() + 24 * 60 * 60 * 1000);
      const end_time = new Date(start_time.getTime() + 30 * 60 * 1000); // Only 30 minutes

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id,
            start_time,
            end_time
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('at least 1 hour'));
          return true;
        },
        'Should reject booking shorter than 1 hour'
      );
    });

    it('should reject booking longer than maximum duration (30 days)', async () => {
      const kitchen_id = '78901234-7890-7890-7890-789012345678';
      const user_id = '89012345-8901-8901-8901-890123456789';
      const start_time = new Date(Date.now() + 24 * 60 * 60 * 1000);
      const end_time = new Date(start_time.getTime() + 31 * 24 * 60 * 60 * 1000); // 31 days

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id,
            user_id,
            start_time,
            end_time
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('cannot exceed 30 days'));
          return true;
        },
        'Should reject booking longer than 30 days'
      );
    });

    it('should reject booking with invalid kitchen_id', async () => {
      const user_id = '90123456-9012-9012-9012-901234567890';
      const start_time = new Date(Date.now() + 24 * 60 * 60 * 1000);
      const end_time = new Date(start_time.getTime() + 2 * 60 * 60 * 1000);

      await assert.rejects(
        async () => {
          await bookingService.createBooking({
            kitchen_id: '',
            user_id,
            start_time,
            end_time
          });
        },
        (err: Error) => {
          assert.ok(err.message.includes('Invalid kitchen_id'));
          return true;
        },
        'Should reject booking with invalid kitchen_id'
      );
    });
  });

  describe('AvailabilityService - Concurrent Access', () => {
    it('should handle concurrent booking attempts and allow only one', async () => {
      const kitchen_id = 'aaaabbbb-cccc-dddd-eeee-ffff00001111';
      const user_id_1 = 'bbbbcccc-dddd-eeee-ffff-0000111122222';
      const user_id_2 = 'ccccdddd-eeee-ffff-0000-111122223333';
      const start_time = new Date(Date.now() + 168 * 60 * 60 * 1000);
      const end_time = new Date(start_time.getTime() + 3 * 60 * 60 * 1000);

      // Attempt two concurrent bookings
      const results = await Promise.allSettled([
        bookingService.createBooking({ kitchen_id, user_id: user_id_1, start_time, end_time }),
        bookingService.createBooking({ kitchen_id, user_id: user_id_2, start_time, end_time })
      ]);

      // One should succeed, one should fail
      const successes = results.filter(r => r.status === 'fulfilled');
      const failures = results.filter(r => r.status === 'rejected');

      assert.strictEqual(successes.length, 1, 'Exactly one booking should succeed');
      assert.strictEqual(failures.length, 1, 'Exactly one booking should fail');

      // Cleanup
      if (successes[0].status === 'fulfilled') {
        await db.query('DELETE FROM bookings WHERE booking_id = $1', [successes[0].value.booking_id]);
      }
    });
  });
});
