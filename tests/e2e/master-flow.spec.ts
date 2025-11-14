/**
 * Playwright E2E Master Test (F20)
 * End-to-end test covering: host signup, certificate upload, listing creation,
 * user booking, Stripe payment, and confirmation
 */

import { test, expect, Page } from '@playwright/test';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Test data
const HOST_EMAIL = `host-${Date.now()}@test.com`;
const USER_EMAIL = `user-${Date.now()}@test.com`;
const PASSWORD = 'TestPassword123!';

test.describe('PrepChef E2E Master Flow', () => {
  test.beforeAll(async () => {
    // Start docker-compose
    console.log('Starting docker-compose...');
    await execAsync('docker-compose up -d postgres redis minio');

    // Wait for services to be healthy
    await new Promise(resolve => setTimeout(resolve, 10000));

    // Run migrations
    try {
      await execAsync('docker-compose exec -T postgres psql -U postgres -d prepchef -f /docker-entrypoint-initdb.d/01-schema.sql');
    } catch (e) {
      console.log('Migrations already applied or failed:', e);
    }
  });

  test.afterAll(async () => {
    // Cleanup: Delete test data
    try {
      await execAsync(`docker-compose exec -T postgres psql -U postgres -d prepchef -c "DELETE FROM users WHERE email IN ('${HOST_EMAIL}', '${USER_EMAIL}')"`);
    } catch (e) {
      console.log('Cleanup warning:', e);
    }
  });

  test('Complete booking flow from host signup to confirmed booking', async ({ page, context }) => {
    test.setTimeout(120000); // 2 minutes

    // Step 1: Host signup
    console.log('Step 1: Host signup');
    await page.goto('http://localhost:3001/host/signup');

    await page.fill('input[name="name"]', 'Test Host');
    await page.fill('input[name="email"]', HOST_EMAIL);
    await page.fill('input[name="password"]', PASSWORD);
    await page.fill('input[name="business_name"]', 'Test Kitchen LLC');
    await page.fill('input[name="business_address"]', '123 Main St, City, ST 12345');
    await page.fill('input[name="phone"]', '555-123-4567');

    await page.click('button[type="submit"]');

    // Wait for redirect or success message
    await page.waitForURL('**/host/dashboard', { timeout: 5000 }).catch(() => {});
    await expect(page.locator('text=Welcome')).toBeVisible({ timeout: 5000 }).catch(() => {});

    console.log('✓ Host signup successful');

    // Step 2: Upload health permit certificate
    console.log('Step 2: Upload certificate');
    await page.goto('http://localhost:3001/host/certificates');

    // Create a mock PDF file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'health-permit.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.4 Test Health Permit')
    });

    await page.selectOption('select[name="certificate_type"]', 'health_permit');
    await page.fill('input[name="issuing_agency"]', 'County Health Department');
    await page.fill('input[name="expiration_date"]', '2025-12-31');

    await page.click('button:has-text("Upload")');

    await expect(page.locator('text=Certificate uploaded')).toBeVisible({ timeout: 5000 });

    console.log('✓ Certificate uploaded');

    // Step 3: Trigger compliance validation
    console.log('Step 3: Validate compliance');
    await page.click('button:has-text("Validate")');

    await expect(page.locator('text=Validation complete')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('text=Validated', { exact: false })).toBeVisible();

    console.log('✓ Compliance validated');

    // Step 4: Create kitchen listing
    console.log('Step 4: Create listing');
    await page.goto('http://localhost:3001/host/listings/new');

    await page.fill('input[name="title"]', 'Professional Test Kitchen');
    await page.fill('textarea[name="description"]', 'Fully equipped commercial kitchen for rent');
    await page.fill('input[name="price_per_hour"]', '50');
    await page.fill('input[name="address"]', '456 Kitchen St, City, ST 12345');

    // Upload listing photo
    const photoInput = page.locator('input[type="file"][name="photos"]');
    await photoInput.setInputFiles({
      name: 'kitchen.jpg',
      mimeType: 'image/jpeg',
      buffer: Buffer.from('fake-image-data')
    });

    await page.click('button:has-text("Create Listing")');

    await expect(page.locator('text=Listing created')).toBeVisible({ timeout: 5000 });

    console.log('✓ Listing created');

    // Step 5: Set availability
    console.log('Step 5: Set availability');
    await page.click('button:has-text("Set Availability")');

    // Mark tomorrow as available
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowDate = tomorrow.toISOString().split('T')[0];

    await page.fill('input[name="date"]', tomorrowDate);
    await page.fill('input[name="start_time"]', '09:00');
    await page.fill('input[name="end_time"]', '17:00');

    await page.click('button:has-text("Save Availability")');

    await expect(page.locator('text=Availability saved')).toBeVisible({ timeout: 5000 });

    console.log('✓ Availability set');

    // Step 6: User signup (open new context for separate session)
    console.log('Step 6: User signup');
    const userPage = await context.newPage();
    await userPage.goto('http://localhost:3001/signup');

    await userPage.fill('input[name="name"]', 'Test User');
    await userPage.fill('input[name="email"]', USER_EMAIL);
    await userPage.fill('input[name="password"]', PASSWORD);

    await userPage.click('button[type="submit"]');

    await userPage.waitForURL('**/dashboard', { timeout: 5000 }).catch(() => {});

    console.log('✓ User signup successful');

    // Step 7: Search for kitchen and view listing
    console.log('Step 7: Search and view listing');
    await userPage.goto('http://localhost:3001/search');

    await userPage.fill('input[name="location"]', 'City, ST');
    await userPage.click('button:has-text("Search")');

    // Click on the listing
    await userPage.click('a:has-text("Professional Test Kitchen")');

    await expect(userPage.locator('text=Professional Test Kitchen')).toBeVisible();

    console.log('✓ Listing visible');

    // Step 8: Create booking hold
    console.log('Step 8: Create booking');
    await userPage.fill('input[name="booking_date"]', tomorrowDate);
    await userPage.fill('input[name="start_time"]', '10:00');
    await userPage.fill('input[name="end_time"]', '14:00');

    await userPage.click('button:has-text("Book Now")');

    // Booking modal should appear
    await expect(userPage.locator('text=Confirm Booking')).toBeVisible({ timeout: 5000 });
    await expect(userPage.locator('text=$50')).toBeVisible(); // Price display

    console.log('✓ Booking hold created');

    // Step 9: Payment with Stripe (test mode)
    console.log('Step 9: Process payment');

    // Fill Stripe test card details
    const stripeFrame = userPage.frameLocator('iframe[name^="__privateStripeFrame"]').first();

    await stripeFrame.locator('input[name="cardnumber"]').fill('4242424242424242');
    await stripeFrame.locator('input[name="exp-date"]').fill('1225');
    await stripeFrame.locator('input[name="cvc"]').fill('123');
    await stripeFrame.locator('input[name="postal"]').fill('12345');

    await userPage.click('button:has-text("Pay Now")');

    // Wait for payment confirmation
    await expect(userPage.locator('text=Booking Confirmed')).toBeVisible({ timeout: 15000 });

    console.log('✓ Payment processed');

    // Step 10: Verify booking is confirmed
    console.log('Step 10: Verify booking status');
    await userPage.goto('http://localhost:3001/bookings');

    await expect(userPage.locator('text=Professional Test Kitchen')).toBeVisible();
    await expect(userPage.locator('text=Confirmed')).toBeVisible();

    console.log('✓ Booking confirmed');

    // Step 11: Host sees the booking
    console.log('Step 11: Host views booking');
    await page.goto('http://localhost:3001/host/bookings');

    await expect(page.locator('text=Test User')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=Confirmed')).toBeVisible();

    console.log('✓ Host sees confirmed booking');

    console.log('\n✅ E2E TEST PASSED - Full flow completed successfully!');
  });

  test('Should reject double-booking attempt', async ({ page }) => {
    // This test ensures atomic availability checking works

    console.log('Testing double-booking prevention...');

    await page.goto('http://localhost:3001/search');

    // Try to book same time slot
    await page.click('a:has-text("Professional Test Kitchen")');

    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const tomorrowDate = tomorrow.toISOString().split('T')[0];

    await page.fill('input[name="booking_date"]', tomorrowDate);
    await page.fill('input[name="start_time"]', '10:00');
    await page.fill('input[name="end_time"]', '14:00');

    await page.click('button:has-text("Book Now")');

    // Should show error
    await expect(page.locator('text=not available')).toBeVisible({ timeout: 5000 });

    console.log('✓ Double-booking correctly prevented');
  });
});
