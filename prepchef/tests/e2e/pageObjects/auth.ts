import { Page, expect } from '@playwright/test';

type Role = 'admin' | 'host' | 'renter' | 'compliance';

const ROLE_LOGIN_PATH: Record<Role, string> = {
  admin: '/admin/login',
  host: '/login',
  renter: '/login',
  compliance: '/compliance/login',
};

export class AuthPage {
  constructor(private readonly page: Page) {}

  async goto(role: Role) {
    await this.page.goto(ROLE_LOGIN_PATH[role]);
    await expect(this.page.locator('[data-testid="login-form"]')).toBeVisible();
  }

  async login(email: string, password: string) {
    await this.page.fill('[data-testid="email"]', email);
    await this.page.fill('[data-testid="password"]', password);
    await this.page.click('[data-testid="login-submit"]');
  }

  async expectSuccessfulLogin(redirectPath: string) {
    await expect(this.page).toHaveURL(new RegExp(`${redirectPath}(/|$)`));
  }

  async expectErrorMessage(message: string) {
    await expect(this.page.locator('[role="alert"]')).toContainText(message);
  }
}
