# Operations Handbook

## Purpose

This handbook provides operational procedures, troubleshooting guides, and runbooks for the Prep platform operations team.

---

## Table of Contents

1. [On-Call Procedures](#on-call-procedures)
2. [Incident Response](#incident-response)
3. [Common Issues & Solutions](#common-issues--solutions)
4. [Deployment Procedures](#deployment-procedures)
5. [Database Operations](#database-operations)
6. [Monitoring & Alerts](#monitoring--alerts)
7. [Security Incidents](#security-incidents)
8. [Contact Information](#contact-information)

---

## On-Call Procedures

### Rotation Schedule

- **Primary On-Call**: Handles all alerts
- **Secondary On-Call**: Backup for escalation
- **Rotation**: Weekly, Monday 9am PT to Monday 9am PT
- **Handoff**: 30-minute sync call every Monday morning

### On-Call Checklist

**Start of Shift:**
- [ ] Verify PagerDuty is working (send test alert)
- [ ] Check laptop, phone, internet connection
- [ ] Review open incidents from previous week
- [ ] Check SLO dashboards - any services near error budget?
- [ ] Review scheduled deployments this week

**During Shift:**
- [ ] Respond to alerts within 5 minutes
- [ ] Update incident status in PagerDuty
- [ ] Document all actions in incident timeline
- [ ] Escalate to secondary if needed

**End of Shift:**
- [ ] Write handoff notes for next on-call
- [ ] Ensure all incidents are documented
- [ ] Schedule post-mortems for P0/P1 incidents

---

## Incident Response

### Severity Definitions

| Severity | Response Time | Example |
|----------|--------------|---------|
| **P0** (Critical) | Immediate | Complete platform outage |
| **P1** (High) | < 15 min | Payment processing down |
| **P2** (Medium) | < 1 hour | Elevated error rates |
| **P3** (Low) | < 4 hours | Dashboard slow |
| **P4** (Info) | Next business day | Minor UI bug |

### Incident Response Workflow

1. **Alert Received** → PagerDuty notification
2. **Acknowledge** (< 5 min) → Click "Acknowledge" in PagerDuty
3. **Assess** (< 5 min):
   - What's the user impact?
   - Which services are affected?
   - Is data at risk?
4. **Communicate**:
   - Post in #incidents Slack channel
   - Update status page if customer-facing
5. **Mitigate**:
   - Apply temporary fix to restore service
   - Roll back bad deployment if needed
6. **Resolve**:
   - Apply permanent fix
   - Verify service is healthy
   - Mark incident as resolved
7. **Post-Mortem** (within 48 hours):
   - Blameless write-up
   - Root cause analysis
   - Action items with owners

---

## Common Issues & Solutions

### 1. High Database CPU

**Symptoms**: Database CPU > 90%, slow queries

**Quick Fix**:
```bash
# Restart read replica to offload traffic
docker compose restart postgres-replica

# Check for long-running queries
docker compose exec postgres psql -U postgres -d prepchef -c "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity WHERE state = 'active' ORDER BY duration DESC;"

# Kill long-running query if needed
docker compose exec postgres psql -U postgres -d prepchef -c "SELECT pg_terminate_backend(PID);"
```

**Root Cause**: Usually unoptimized queries or missing indexes

**Permanent Fix**: Add indexes, optimize queries

---

### 2. Payment Failures Spike

**Symptoms**: Payment success rate < 99%

**Quick Fix**:
```bash
# Check Stripe API status
curl https://status.stripe.com/api/v2/status.json

# Check recent payment intents
prepctl payments:recent --failed

# Manual retry for failed payments
prepctl payments:retry --batch-size 10
```

**Root Cause**: Stripe API degradation, network issues, or bad card data

**Permanent Fix**: Improve retry logic, better error handling

---

### 3. Compliance Engine Slow

**Symptoms**: Compliance checks taking > 5 seconds

**Quick Fix**:
```bash
# Check compliance service logs
docker compose logs python-compliance --tail 100

# Restart compliance service
docker compose restart python-compliance

# Check RegEngine cache hit rate
prepctl compliance:stats
```

**Root Cause**: Cache misses, rule evaluation complexity

**Permanent Fix**: Optimize rules, increase caching

---

### 4. Redis Connection Failures

**Symptoms**: "Connection refused" errors, session loss

**Quick Fix**:
```bash
# Check Redis health
docker compose exec redis redis-cli ping

# Restart Redis
docker compose restart redis

# Check connection pool
prepctl redis:pool-stats
```

**Root Cause**: Redis memory full, connection pool exhausted

**Permanent Fix**: Increase Redis memory, tune connection pool

---

### 5. Disk Space Full

**Symptoms**: Services crashing, database writes failing

**Quick Fix**:
```bash
# Check disk usage
df -h

# Find large files
du -sh /var/lib/docker/* | sort -rh | head -10

# Clean Docker volumes (CAREFUL!)
docker system prune -af --volumes
```

**Root Cause**: Log accumulation, unused Docker images

**Permanent Fix**: Set up log rotation, automated cleanup

---

## Deployment Procedures

### Standard Deployment

**Prerequisites**:
- [ ] PR approved by 2 engineers
- [ ] All CI checks passing
- [ ] Staging deployment successful
- [ ] Off-peak hours (if high-risk change)

**Steps**:
```bash
# 1. Pull latest code
git pull origin main

# 2. Run database migrations (if any)
prepctl db:migrate

# 3. Build new containers
docker compose build

# 4. Deploy with zero downtime
docker compose up -d --no-deps --build <service-name>

# 5. Health check
prepctl health:check --all

# 6. Monitor metrics for 15 minutes
# Watch Grafana dashboard for errors/latency spikes
```

### Rollback Procedure

If deployment causes issues:

```bash
# 1. Immediate rollback
git revert <commit-hash>
git push origin main

# 2. Redeploy previous version
docker compose up -d --no-deps --build <service-name>

# 3. Verify rollback
prepctl health:check --all

# 4. Notify team
# Post in #engineering Slack
```

### Emergency Hotfix

For critical production bugs:

```bash
# 1. Create hotfix branch from main
git checkout -b hotfix/critical-bug main

# 2. Make minimal fix
# ... code changes ...

# 3. Fast-track review (1 approver minimum)
gh pr create --title "HOTFIX: Critical bug" --base main

# 4. Deploy immediately after approval
# ... follow deployment steps ...

# 5. Post-mortem within 24 hours
```

---

## Database Operations

### Backup & Restore

**Automated Backups**: Daily at 2am UTC to S3

**Manual Backup**:
```bash
# Create backup
docker compose exec postgres pg_dump -U postgres prepchef > backup-$(date +%Y%m%d).sql

# Restore from backup
docker compose exec -T postgres psql -U postgres prepchef < backup-20251113.sql
```

### Migrations

**Apply Migrations**:
```bash
prepctl db:migrate
```

**Rollback Migration**:
```bash
prepctl db:migrate --target <previous-revision>
```

**Create New Migration**:
```bash
docker compose exec python-compliance alembic revision -m "Add new table"
```

---

## Monitoring & Alerts

### Key Dashboards

1. **Golden Signals**: http://localhost:3001/d/golden-signals
2. **Service Health**: http://localhost:3001/d/service-health
3. **Business Metrics**: http://localhost:3001/d/business-metrics

### Alert Silencing

**During Maintenance**:
```bash
# Silence alerts for 2 hours
prepctl alerts:silence --duration 2h --reason "Planned maintenance"
```

---

## Security Incidents

### Data Breach Response

1. **Immediate Actions**:
   - Isolate affected systems
   - Revoke compromised credentials
   - Notify security team

2. **Investigation**:
   - Review audit logs
   - Identify scope of breach
   - Document timeline

3. **Notification**:
   - Legal team (immediately)
   - Affected users (within 72 hours per GDPR)
   - Regulators (if required)

### Suspected Intrusion

```bash
# Check recent logins
prepctl audit:logins --recent 24h

# Review suspicious activity
prepctl audit:suspicious

# Lock compromised accounts
prepctl users:lock --user-id <id>
```

---

## Contact Information

### Escalation Path

1. **On-Call Engineer** (PagerDuty)
2. **Engineering Lead** (555-0101)
3. **CTO** (555-0102)
4. **CEO** (555-0100)

### External Vendors

- **Stripe Support**: support@stripe.com, 1-888-926-2289
- **AWS Support**: Business Plan, TAM: aws-tam@prep.com
- **Datadog Support**: support@datadoghq.com

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-13
- **Owner**: Operations Team
- **Review Cycle**: Quarterly

---

## Appendix

### Useful Commands

```bash
# Check all service health
prepctl health:check --all

# View recent errors
prepctl logs:errors --tail 50

# Database connection count
prepctl db:connections

# Redis memory usage
prepctl redis:info memory

# Export audit logs
prepctl audit:export --start 2025-01-01 --end 2025-12-31
```

### Emergency Contacts

Keep this list updated and accessible 24/7:

| Role | Name | Phone | Email |
|------|------|-------|-------|
| On-Call Primary | Rotation | PagerDuty | oncall@prep.com |
| Engineering Lead | TBD | 555-0101 | eng-lead@prep.com |
| CTO | TBD | 555-0102 | cto@prep.com |
| Security Lead | TBD | 555-0103 | security@prep.com |
