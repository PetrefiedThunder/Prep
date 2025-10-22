# Security Policy

## Reporting a Vulnerability

If you find a vulnerability, please do not open a public issue. Instead, email us at [security@prepchef.com] or use GitHub's private security advisory.

## Credential Management

### Environment Variables
All credentials must be stored as environment variables, never hardcoded in source files.

### Required Environment Variables
- `POSTGRES_USER` - PostgreSQL username
- `POSTGRES_PASSWORD` - PostgreSQL password
- `POSTGRES_DB` - PostgreSQL database name
- `REDIS_PASSWORD` - Redis password
- `MINIO_ROOT_USER` - MinIO root user
- `MINIO_ROOT_PASSWORD` - MinIO root password
- `PGADMIN_DEFAULT_EMAIL` - pgAdmin email
- `PGADMIN_DEFAULT_PASSWORD` - pgAdmin password

### Setup Process
1. Copy `.env.example` to `.env`
2. Update all placeholder values with secure credentials
3. Never commit `.env` files to version control

## Security Best Practices

### Code Review Checklist
- [ ] No hardcoded credentials
- [ ] All secrets use environment variables
- [ ] Configuration files are properly secured
- [ ] Security linting passes
- [ ] Tests cover security scenarios

### Secret Management
- Use `.env.example` for reference configuration
- Never commit actual secrets to version control
- Rotate credentials regularly
- Use strong, randomly generated passwords

We take security seriously and will respond to vulnerability reports within 24 hours.
