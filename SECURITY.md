# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in PrepChef, please report it to the development team immediately. Do not open a public issue.

## Known Issues

### Development Dependency Vulnerabilities

**Status**: Known, Low Risk (Dev Dependencies Only)

#### glob 10.2.0 - 10.4.5 (High Severity)
- **Vulnerability**: Command injection via -c/--cmd executes matches with shell:true
- **Advisory**: [GHSA-5j98-mcp5-4vw2](https://github.com/advisories/GHSA-5j98-mcp5-4vw2)
- **Affected Packages**:
  - `eslint-config-next@14.2.33` (dev dependency)
  - `@next/eslint-plugin-next@14.2.33` (dev dependency)
- **Risk Assessment**: **Low**
  - Only affects development environment (ESLint tooling)
  - Vulnerability is in glob CLI functionality, not library usage
  - Does not affect runtime/production code
  - Application does not directly use glob package
- **Resolution Plan**:
  - Monitor for Next.js 14.x patch updates that address this issue
  - Consider upgrading to Next.js 15+ when evaluating Phase 2 features
  - No immediate action required for MVP production deployment

**To fix (requires breaking changes to Next.js 15+):**
```bash
npm audit fix --force
```

**Note**: This will upgrade Next.js from 14.x to 15+ which may introduce breaking changes. Test thoroughly before applying to production.

## Security Maintenance Notes

- Dependabot is configured to monitor the npm ecosystem only, matching this project's Next.js/TypeScript stack. No Python package managers (pip, Poetry, or Pipenv) are used, so Python ecosystem monitoring is not required.
- No unrelated Dependabot alerts are currently tracked for non-npm ecosystems. Future dependency monitoring should remain scoped to npm unless project languages change.

## Security Best Practices

### Implemented Security Measures

✅ **Row Level Security (RLS)**
- All database tables have RLS policies enabled
- User data is isolated via JWT-based auth
- Owner-only access to kitchen management and bookings
- Renter-only access to personal bookings

✅ **Authentication & Authorization**
- Supabase Auth with JWT tokens
- Email confirmation required for new accounts
- Session refresh on every request via middleware
- Protected routes redirect unauthenticated users

✅ **Payment Security**
- Stripe Connect for secure payment processing
- Webhook signature verification for all Stripe events
- No credit card data stored in application database
- PCI compliance handled by Stripe

✅ **Environment Variables**
- All secrets stored in environment variables
- No secrets committed to repository
- `.env.local` excluded from version control
- Separate keys for development and production

✅ **Input Validation**
- Server-side validation in all server actions
- TypeScript type safety throughout application
- Parameterized queries via Supabase client (SQL injection prevention)
- Form validation for user inputs

✅ **HTTPS Only**
- Supabase requires HTTPS in production
- Stripe webhooks require HTTPS endpoints
- Vercel provides automatic HTTPS for all deployments

✅ **API Security**
- Webhook endpoints verify signatures
- Rate limiting via Vercel's built-in protection
- CORS policies enforced by Next.js

### Production Deployment Checklist

Before deploying to production, ensure:

- [ ] All environment variables set in Vercel (not hardcoded)
- [ ] Production Supabase project created with RLS enabled
- [ ] Production Stripe account configured (not test mode)
- [ ] Stripe webhook endpoint configured with production secret
- [ ] Custom domain configured with HTTPS
- [ ] Email confirmation enabled in Supabase Auth
- [ ] Database backups enabled in Supabase
- [ ] Monitoring configured (Vercel Analytics + Sentry recommended)
- [ ] Error tracking configured for production
- [ ] Rate limiting policies reviewed
- [ ] Security headers configured in next.config.js

### Recommended Security Headers

Add to `next.config.js`:

```javascript
async headers() {
  return [
    {
      source: '/(.*)',
      headers: [
        {
          key: 'X-Frame-Options',
          value: 'DENY',
        },
        {
          key: 'X-Content-Type-Options',
          value: 'nosniff',
        },
        {
          key: 'Referrer-Policy',
          value: 'strict-origin-when-cross-origin',
        },
        {
          key: 'Permissions-Policy',
          value: 'camera=(), microphone=(), geolocation=()',
        },
      ],
    },
  ]
},
```

### Regular Security Maintenance

**Monthly Tasks:**
- [ ] Run `npm audit` and review vulnerabilities
- [ ] Update dependencies with security patches
- [ ] Review Supabase auth logs for suspicious activity
- [ ] Review Stripe dashboard for unusual transactions
- [ ] Check Vercel logs for errors or unusual traffic

**Quarterly Tasks:**
- [ ] Review and update RLS policies
- [ ] Audit user permissions and access controls
- [ ] Review environment variable rotation policy
- [ ] Test disaster recovery procedures
- [ ] Review and update this security policy

**Annual Tasks:**
- [ ] Security audit by third party (recommended for production)
- [ ] Penetration testing (recommended for production)
- [ ] Compliance review (GDPR, CCPA if applicable)
- [ ] Update incident response procedures

## Data Privacy

### Data Collected

The application collects and stores:
- User email addresses (via Supabase Auth)
- User profiles (name, account type)
- Kitchen listings (address, photos, pricing)
- Booking records (times, payment IDs)
- Stripe account IDs (for Connect accounts)

### Data Protection

- All data encrypted at rest (Supabase default)
- All data encrypted in transit (HTTPS)
- Payment data handled exclusively by Stripe (PCI compliant)
- No credit card data stored in application database
- User data isolated via RLS policies

### Data Retention

- User accounts: Retained until user requests deletion
- Booking history: Retained for 7 years (financial records)
- Payment records: Retained per Stripe's retention policy
- Session data: Auto-expires per Supabase Auth configuration

### User Rights

Users can request:
- Access to their personal data
- Correction of inaccurate data
- Deletion of their account and associated data
- Export of their data in machine-readable format

## Incident Response

### In Case of Security Breach

1. **Immediate Actions**
   - Isolate affected systems
   - Notify development team
   - Document the incident (time, scope, impact)

2. **Investigation**
   - Identify attack vector
   - Assess data exposure
   - Review audit logs

3. **Containment**
   - Patch vulnerabilities
   - Rotate compromised credentials
   - Update security policies

4. **User Notification**
   - Notify affected users within 72 hours
   - Provide guidance on protective measures
   - Offer support resources

5. **Post-Incident**
   - Conduct post-mortem analysis
   - Update security procedures
   - Implement additional safeguards

## Contact

For security concerns, contact the development team immediately.

---

**Last Updated**: December 2025
**Version**: 1.0.0 (MVP)
