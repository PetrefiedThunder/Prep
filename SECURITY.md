# Security Policy

**Last Security Audit**: November 19, 2025
**Status**: ✅ 0 HIGH Python Vulnerabilities | ⚠️ 8 Remaining (npm/Node.js - under investigation)

---

## Latest Security Audit Summary

### Python Dependencies (November 19, 2025)
- **Status**: ✅ **All Clear**
- **Tool**: pip-audit 2.9.0
- **Result**: 0 known vulnerabilities
- **Last Fixes**: Resolved 7 vulnerabilities (3 HIGH, 4 MEDIUM)
  - cryptography 41.0.7 → 46.0.3
  - setuptools 68.1.2 → 80.9.0
  - pip 24.0 → 25.3

See [SECURITY_FIXES_2025-11-19.md](./SECURITY_FIXES_2025-11-19.md) for complete details.

### npm/Node.js Dependencies
- **Status**: ⚠️ **Under Investigation**
- **GitHub Alert**: 8 vulnerabilities (2 HIGH, 6 MODERATE)
- **Next Steps**: Full npm audit scheduled for follow-up PR

---

## Reporting a Vulnerability

If you find a vulnerability, please do not open a public issue. Instead, contact the security team through the designated private security channels.

We take security seriously and will respond to vulnerability reports within 24 hours.

## Credential Management

### Environment Variables
All credentials must be stored as environment variables, never hardcoded in source files.

### Required Environment Variables
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - PostgreSQL database name
- `REDIS_PASSWORD` - Redis password (optional, use for production)
- `MINIO_ROOT_USER` - MinIO root user
- `MINIO_ROOT_PASSWORD` - MinIO root password
- `JWT_SECRET` - JWT signing secret (256-bit minimum)
- `STRIPE_SECRET_KEY` - Stripe API secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret
- `STRIPE_PUBLISHABLE_KEY` - Stripe publishable key (frontend)

### Setup Process
1. Copy `.env.example` to `.env`
2. Update all placeholder values with secure credentials
3. Never commit `.env` files to version control
4. Run `scripts/check_secrets.sh` before commits to detect exposed secrets

## Secret Storage

### Development Environment
For local development:
- Use `.env` files (gitignored)
- Never use production secrets in development
- Use Stripe test keys (`sk_test_*`, `pk_test_*`)

### Staging/Production Environments

**Option 1: HashiCorp Vault (Recommended for Production)**
- Store all secrets in Vault
- Use Vault Agent for secret injection
- Enable automatic secret rotation
- Example Vault path structure:
  ```
  secret/app/production/database
  secret/app/production/stripe
  secret/app/production/jwt
  ```

**Option 2: GitHub Secrets (CI/CD)**
- Store secrets in GitHub repository secrets
- Access via `${{ secrets.SECRET_NAME }}` in workflows
- Scope secrets by environment (staging, production)

**Option 3: Kubernetes Secrets**
- Use External Secrets Operator to sync from Vault
- Or create secrets manually:
  ```bash
  kubectl create secret generic app-secrets \
    --from-literal=DATABASE_URL='...' \
    --from-literal=STRIPE_SECRET_KEY='...' \
    -n app
  ```

**Option 4: Cloud Provider Secret Managers**
- AWS Secrets Manager
- Azure Key Vault
- Google Cloud Secret Manager

### Stripe Key Management

#### Key Types
1. **Secret Key** (`sk_test_*` / `sk_live_*`)
   - Server-side only
   - Never expose to frontend
   - Store in backend environment variables
   - Used for API calls

2. **Publishable Key** (`pk_test_*` / `pk_live_*`)
   - Frontend-safe
   - Used in Stripe Elements
   - Can be committed to code or env vars

3. **Webhook Secret** (`whsec_*`)
   - Used to verify webhook signatures
   - Store securely server-side

#### Development vs Production
- **Development**: Use Stripe test mode keys
- **Production**: Use live mode keys
- Never mix test and live keys in same environment

#### Accessing Stripe Keys
1. Log in to [Stripe Dashboard](https://dashboard.stripe.com)
2. Navigate to Developers → API Keys
3. Copy keys and store in secret manager
4. For webhook secret: Developers → Webhooks → Add endpoint → Reveal signing secret

## Secret Rotation

### Rotation Schedule
- **JWT_SECRET**: Rotate every 90 days
- **Database passwords**: Rotate every 60 days
- **Stripe keys**: Rotate on security incident or employee offboarding
- **MinIO credentials**: Rotate every 90 days

### Rotation Process

#### 1. JWT Secret Rotation
```bash
# Generate new secret
NEW_SECRET=$(openssl rand -base64 32)

# Update in secret store (Vault example)
vault kv put secret/app/production/jwt secret=$NEW_SECRET

# Rolling restart of services
kubectl rollout restart deployment/node-api -n app
kubectl rollout restart deployment/python-compliance -n app

# Old tokens remain valid until expiry (grace period)
```

#### 2. Database Password Rotation
```bash
# 1. Create new password
NEW_PASSWORD=$(openssl rand -base64 24)

# 2. Update database user
psql -c "ALTER USER app_user WITH PASSWORD '$NEW_PASSWORD';"

# 3. Update secret store
vault kv put secret/app/production/database password=$NEW_PASSWORD

# 4. Rolling restart with zero downtime
kubectl set env deployment/node-api DATABASE_PASSWORD=$NEW_PASSWORD -n prepchef
```

#### 3. Stripe Key Rotation
```bash
# 1. Generate new restricted API key in Stripe Dashboard
# 2. Update both keys temporarily (old + new) for transition
# 3. Update secret store with new key
# 4. Deploy services
# 5. Delete old key from Stripe Dashboard after 24h
```

#### 4. MinIO Credential Rotation
```bash
# Create new access key
mc admin user add myminio newuser newpassword

# Update applications
# Remove old user after migration
mc admin user remove myminio olduser
```

## Revoking Compromised Keys

### Immediate Actions (Within 1 Hour)
1. **Identify scope of compromise**
   - Which key was exposed?
   - What permissions does it have?
   - When was it exposed?

2. **Revoke the key immediately**
   - Stripe: Dashboard → Developers → API Keys → Delete
   - Database: `REVOKE ALL ON DATABASE prepchef FROM compromised_user;`
   - JWT: Force logout all sessions, rotate secret
   - Vault: `vault token revoke <token>`

3. **Generate and deploy new key**
   - Follow rotation process above
   - Use expedited deployment

4. **Audit access logs**
   - Check Stripe logs for unauthorized API calls
   - Review database audit logs
   - Check application logs for suspicious activity

### Stripe Key Revocation Steps
```bash
# 1. Log in to Stripe Dashboard
# 2. Navigate to Developers → API Keys
# 3. Click "Delete" on compromised key
# 4. Confirm deletion
# 5. Generate new restricted key with minimal permissions
# 6. Update environment variables
# 7. Restart services
# 8. Monitor Stripe Dashboard for unauthorized charges
```

### Database Credential Revocation
```sql
-- Revoke all privileges
REVOKE ALL PRIVILEGES ON DATABASE app_db FROM compromised_user;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM compromised_user;

-- Drop user
DROP USER compromised_user;

-- Create new user with proper permissions
CREATE USER app_user WITH PASSWORD 'new_secure_password';
GRANT CONNECT ON DATABASE app_db TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
```

### Post-Incident
1. Document incident in security log
2. Review access controls and permissions
3. Update secret rotation schedule if needed
4. Notify stakeholders if customer data was accessed
5. Conduct post-mortem and implement preventive measures
6. Report to security team through designated channels

## Security Best Practices

### Code Review Checklist
- [ ] No hardcoded credentials
- [ ] All secrets use environment variables or secret manager
- [ ] Configuration files are properly secured
- [ ] Security linting passes (Bandit, Trivy)
- [ ] Tests cover security scenarios
- [ ] Stripe keys are test keys in non-production environments
- [ ] Database queries use parameterized statements (no SQL injection)
- [ ] CORS is properly configured
- [ ] Rate limiting is enabled on API endpoints

### Secret Management
- Use `.env.example` for reference configuration
- Never commit actual secrets to version control
- Rotate credentials regularly (see schedule above)
- Use strong, randomly generated passwords (32+ characters)
- Run `scripts/check_secrets.sh` in pre-commit hooks
- Stripe webhook secrets must be verified on every webhook request
- Use Stripe restricted API keys with minimal permissions

### Automated Secret Detection
Run the secret checker script before every commit:
```bash
./scripts/check_secrets.sh
```

This script will:
- Scan for Stripe secret keys in `.env` files
- Detect hardcoded credentials in source code
- Check for exposed JWT secrets
- Fail CI if secrets are detected in commits

### Monitoring & Alerts
- Enable Stripe webhook signature verification
- Monitor Stripe Dashboard for unusual API activity
- Set up alerts for failed authentication attempts
- Log all secret rotation events
- Enable audit logging for secret access (Vault)

## Incident Response

In case of a security incident:
1. Immediately revoke compromised credentials (see above)
2. Notify security team through designated channels
3. Document incident timeline
4. Assess data exposure
5. Rotate all potentially affected secrets
6. Review and update security procedures

## Compliance

- **PCI-DSS**: Stripe handles card data; we never store, process, or transmit card numbers
- **GDPR/CCPA**: User data encryption at rest and in transit
- **SOC 2**: Secret rotation and access logging for Type II compliance
