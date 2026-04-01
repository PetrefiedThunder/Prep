import assert from 'node:assert'
import { describe, it } from 'node:test'

/**
 * Tests for the Next.js middleware route matcher configuration.
 *
 * The matcher from middleware.ts excludes static assets and image files
 * while matching all other routes for Supabase auth session refresh.
 *
 * Matcher pattern:
 *   /((?!_next/static|_next/image|favicon.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp)$).*)
 */

const MATCHER_PATTERN = /^\/((?!_next\/static|_next\/image|favicon\.ico|.*\.(?:svg|png|jpg|jpeg|gif|webp)$).*)$/

function matchesMiddleware(path: string): boolean {
  return MATCHER_PATTERN.test(path)
}

describe('Middleware route matcher', () => {
  describe('should MATCH (auth refresh needed)', () => {
    it('matches root path /', () => {
      assert.strictEqual(matchesMiddleware('/'), true)
    })

    it('matches /kitchens listing', () => {
      assert.strictEqual(matchesMiddleware('/kitchens'), true)
    })

    it('matches /kitchens/[id] detail', () => {
      assert.strictEqual(matchesMiddleware('/kitchens/abc-123'), true)
    })

    it('matches /bookings', () => {
      assert.strictEqual(matchesMiddleware('/bookings'), true)
    })

    it('matches /owner/kitchens', () => {
      assert.strictEqual(matchesMiddleware('/owner/kitchens'), true)
    })

    it('matches /owner/stripe/return', () => {
      assert.strictEqual(matchesMiddleware('/owner/stripe/return'), true)
    })

    it('matches /admin/compliance', () => {
      assert.strictEqual(matchesMiddleware('/admin/compliance'), true)
    })

    it('matches /auth/callback', () => {
      assert.strictEqual(matchesMiddleware('/auth/callback'), true)
    })

    it('matches /profile', () => {
      assert.strictEqual(matchesMiddleware('/profile'), true)
    })

    it('matches /api/webhooks/stripe', () => {
      assert.strictEqual(matchesMiddleware('/api/webhooks/stripe'), true)
    })

    it('matches /renter path', () => {
      assert.strictEqual(matchesMiddleware('/renter'), true)
    })
  })

  describe('should NOT match (static assets excluded)', () => {
    it('excludes /_next/static/chunks/main.js', () => {
      assert.strictEqual(matchesMiddleware('/_next/static/chunks/main.js'), false)
    })

    it('excludes /_next/static/css/app.css', () => {
      assert.strictEqual(matchesMiddleware('/_next/static/css/app.css'), false)
    })

    it('excludes /_next/image?url=...', () => {
      assert.strictEqual(matchesMiddleware('/_next/image'), false)
    })

    it('excludes /favicon.ico', () => {
      assert.strictEqual(matchesMiddleware('/favicon.ico'), false)
    })

    it('excludes .svg files', () => {
      assert.strictEqual(matchesMiddleware('/logo.svg'), false)
    })

    it('excludes .png files', () => {
      assert.strictEqual(matchesMiddleware('/hero.png'), false)
    })

    it('excludes .jpg files', () => {
      assert.strictEqual(matchesMiddleware('/photo.jpg'), false)
    })

    it('excludes .jpeg files', () => {
      assert.strictEqual(matchesMiddleware('/image.jpeg'), false)
    })

    it('excludes .gif files', () => {
      assert.strictEqual(matchesMiddleware('/animation.gif'), false)
    })

    it('excludes .webp files', () => {
      assert.strictEqual(matchesMiddleware('/optimized.webp'), false)
    })

    it('excludes nested image paths', () => {
      assert.strictEqual(matchesMiddleware('/images/kitchen/photo.png'), false)
    })
  })
})
