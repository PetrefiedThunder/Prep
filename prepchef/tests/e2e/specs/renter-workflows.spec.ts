import { test } from '@playwright/test';
import { AuthPage } from '../pageObjects/auth';
import { RenterExperiencePage } from '../pageObjects/renterExperience';
import { hostUser, renterUser } from '../fixtures/users';
import { demoKitchen } from '../fixtures/kitchens';
import { KitchenPayload, TestDataApiClient } from '../utils/testDataApi';

test.describe('Renter workflows', () => {
  let renterAccount: typeof renterUser;
  let hostAccount: typeof hostUser;
  let availableKitchen: KitchenPayload;

  test.beforeEach(async ({ page, request }, testInfo) => {
    const api = new TestDataApiClient(request);
    const uniqueSuffix = `${testInfo.workerIndex}-${Date.now()}`;

    renterAccount = {
      ...renterUser,
      email: `renter+${uniqueSuffix}@prepchef.com`,
      name: `Renter ${uniqueSuffix}`,
    };

    hostAccount = {
      ...hostUser,
      email: `host-provider+${uniqueSuffix}@prepchef.com`,
      name: `Host Provider ${uniqueSuffix}`,
    };

    availableKitchen = {
      ...demoKitchen,
      name: `${demoKitchen.name} ${uniqueSuffix}`,
      slug: `${demoKitchen.slug}-${uniqueSuffix}`,
    };

    await api.ensureUser(hostAccount);
    await api.ensureUser(renterAccount);
    await api.seedKitchen(availableKitchen, hostAccount.email);

    const authPage = new AuthPage(page);
    await authPage.goto('renter');
    await authPage.login(renterAccount.email, renterAccount.password);
    await authPage.expectSuccessfulLogin('/dashboard');
  });

  test('renter can search and view kitchen details', async ({ page }) => {
    const renterExperience = new RenterExperiencePage(page);
    await renterExperience.searchForKitchen(availableKitchen.name);
    await renterExperience.openKitchenDetails(availableKitchen.slug);
  });

  test('renter can book a kitchen time slot', async ({ page }) => {
    const renterExperience = new RenterExperiencePage(page);
    await renterExperience.searchForKitchen(availableKitchen.name);
    await renterExperience.openKitchenDetails(availableKitchen.slug);
    await renterExperience.bookTimeslot({
      start: availableKitchen.availability.start,
      end: availableKitchen.availability.end,
    });
  });

  test('renter can submit a review after booking', async ({ page, request }) => {
    const renterExperience = new RenterExperiencePage(page);
    const api = new TestDataApiClient(request);

    await api.createBooking({
      kitchenSlug: availableKitchen.slug,
      renterEmail: renterAccount.email,
      start: availableKitchen.availability.start,
      end: availableKitchen.availability.end,
    });

    await renterExperience.searchForKitchen(availableKitchen.name);
    await renterExperience.openKitchenDetails(availableKitchen.slug);
    await renterExperience.submitReview({ rating: 5, review: 'Fantastic kitchen and host!' });
  });
});
