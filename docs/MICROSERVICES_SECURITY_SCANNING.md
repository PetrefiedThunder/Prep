# Microservices Security Scanning

This document describes the security scanning infrastructure for the Node.js/TypeScript microservices in `prepchef/services/`.

## Overview

The Prep platform includes 11 Node.js microservices that require regular security scanning:

- `access-svc` - Access control service
- `admin-svc` - Administration service
- `audit-svc` - Audit logging service
- `auth-svc` - Authentication service
- `availability-svc` - Kitchen availability service
- `booking-svc` - Booking orchestration service
- `compliance-svc` - Compliance verification service
- `listing-svc` - Kitchen listing service
- `notif-svc` - Notification service
- `payments-svc` - Payment processing service
- `pricing-svc` - Dynamic pricing service

## Scanning Types

### 1. Dependency Vulnerability Scanning (npm audit)

Scans all Node.js dependencies for known security vulnerabilities using `npm audit`.

**What it checks:**
- Known CVEs in direct dependencies
- Known CVEs in transitive dependencies
- Severity levels: critical, high, moderate, low

**Reporting:**
- Generates JSON and text reports for each service
- Fails on moderate or higher severity vulnerabilities
- Provides fix recommendations

### 2. Static Code Security Analysis (ESLint)

Scans TypeScript/JavaScript source code for security anti-patterns.

**Security rules checked:**
- `detect-object-injection` - Potential prototype pollution
- `detect-non-literal-regexp` - ReDoS vulnerabilities
- `detect-unsafe-regex` - Catastrophic backtracking
- `detect-buffer-noassert` - Unsafe buffer operations
- `detect-child-process` - Command injection risks
- `detect-eval-with-expression` - Code injection
- `detect-non-literal-fs-filename` - Path traversal
- `detect-non-literal-require` - Arbitrary module loading
- `detect-possible-timing-attacks` - Timing attack vulnerabilities
- `detect-pseudoRandomBytes` - Weak cryptography

### 3. Docker Image Vulnerability Scanning (Trivy)

Scans Docker images for OS and application vulnerabilities.

**What it checks:**
- OS package vulnerabilities (Alpine Linux)
- Node.js runtime vulnerabilities
- Bundled dependency vulnerabilities
- Misconfigurations in Docker images

**Severity levels:**
- CRITICAL - Immediate action required
- HIGH - Address within 30 days
- MEDIUM - Address within 90 days
- LOW - Address as time permits

## Usage

### Automated Scanning (GitHub Actions)

The `scan-microservices.yml` workflow runs automatically:

- **On Push**: When changes are made to microservices in `main` or `develop` branches
- **On Pull Request**: For PRs targeting `main` or `develop` that modify microservices
- **Weekly**: Every Monday at 2 AM UTC
- **Manual**: Can be triggered via GitHub Actions UI

**Workflow steps:**
1. Scans each microservice independently
2. Runs all three scan types in parallel
3. Uploads results to GitHub Security tab (SARIF format)
4. Generates a summary in the Actions UI
5. Stores detailed results as artifacts (90-day retention)

**Viewing results:**
- Go to the "Security" tab in GitHub
- Navigate to "Code scanning alerts"
- Filter by category (e.g., `trivy-auth-svc`)

### Local Scanning (Script)

Run security scans locally before committing:

```bash
# Scan all microservices
./scripts/scan_microservices.sh

# Or use the Makefile target
make scan-microservices
```

**Output:**
- Console output with color-coded results
- Detailed reports saved to `scan-results/` directory
- Exit code 0 if no vulnerabilities, 1 if issues found

**Results files:**
- `{service}_npm_audit.txt` - Human-readable npm audit results
- `{service}_npm_audit.json` - Machine-readable npm audit results
- `{service}_outdated.json` - Outdated package information
- `{service}_eslint.txt` - ESLint security scan results

### Integration with Development Workflow

1. **Before committing microservice changes:**
   ```bash
   make scan-microservices
   ```

2. **Fix any vulnerabilities:**
   ```bash
   cd prepchef/services/{service-name}
   npm audit fix
   # or manually update package.json
   npm install
   ```

3. **Re-scan to verify:**
   ```bash
   make scan-microservices
   ```

4. **Commit and push** - CI will run the full scan suite

## Fixing Vulnerabilities

### Dependency Vulnerabilities

1. Review the audit report in `scan-results/{service}_npm_audit.txt`
2. Try automatic fixes first:
   ```bash
   cd prepchef/services/{service}
   npm audit fix
   ```
3. For vulnerabilities requiring breaking changes:
   ```bash
   npm audit fix --force
   # Test thoroughly after this!
   ```
4. For vulnerabilities without fixes:
   - Check if a patch/minor version update is available
   - Consider alternative packages
   - Document why vulnerable version is acceptable (if necessary)

### Code Security Issues

1. Review ESLint output in `scan-results/{service}_eslint.txt`
2. Fix high-severity issues immediately (eval, command injection, etc.)
3. Address warnings in order of risk
4. Use `// eslint-disable-next-line security/rule-name` sparingly with justification

### Docker Image Vulnerabilities

1. Update base image to latest patch version:
   ```dockerfile
   FROM node:20-alpine  # becomes
   FROM node:20.10.0-alpine3.19  # pinned version
   ```
2. Rebuild and re-scan:
   ```bash
   docker build -t test-image prepchef/services/{service}
   trivy image test-image
   ```
3. If vulnerabilities persist, wait for upstream fixes or use a different base image

## Best Practices

### Dependency Management

- **Pin versions** in `package.json` (avoid `^` and `~` for production)
- **Regular updates**: Review and update dependencies monthly
- **Audit before updates**: Always run `npm audit` before upgrading
- **Test thoroughly**: Run full test suite after dependency updates

### Secure Coding

- **Input validation**: Always validate and sanitize user input
- **Parameterized queries**: Never concatenate SQL/NoSQL queries
- **Cryptography**: Use crypto library, not Math.random()
- **File operations**: Validate and sanitize file paths
- **Child processes**: Avoid spawning processes with user input

### Docker Security

- **Non-root user**: Always use `USER nodejs` in Dockerfiles
- **Minimal base image**: Use Alpine Linux for smaller attack surface
- **Pin versions**: Lock Node.js version (e.g., `node:20.10.0-alpine3.19`)
- **Multi-stage builds**: Separate build and runtime dependencies
- **No secrets**: Never bake secrets into images

## Troubleshooting

### Script fails with "Node.js not installed"

Install Node.js 20+:
```bash
# macOS
brew install node@20

# Ubuntu
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

### "npm ci" fails with missing package-lock.json

Generate lockfile:
```bash
cd prepchef/services/{service}
npm install
git add package-lock.json
git commit -m "Add package-lock.json"
```

### ESLint plugin not found

The script auto-installs ESLint plugins. If it fails:
```bash
cd prepchef/services/{service}
npm install --save-dev eslint eslint-plugin-security
```

### Trivy scan hangs or times out

Increase timeout in workflow:
```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@0.20.0
  timeout-minutes: 10  # Add this line
```

## Maintenance

### Weekly Tasks

- Review security scan results from weekly automated runs
- Triage new vulnerabilities by severity
- Create tickets for remediation work

### Monthly Tasks

- Review and update dependencies across all services
- Check for new ESLint security rules
- Review Trivy findings and update base images

### Quarterly Tasks

- Audit security scanning coverage
- Review and update security policies
- Evaluate new security scanning tools

## Related Documentation

- [Security Policy](../SECURITY.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
- [Development Onboarding](../DEVELOPER_ONBOARDING.md)
- [Operations Handbook](./OPS_HANDBOOK.md)

## Support

For questions or issues:
1. Check [Troubleshooting](#troubleshooting) section above
2. Review scan results in `scan-results/` directory
3. Check GitHub Actions logs for detailed error messages
4. Open an issue with the `security` label if needed
