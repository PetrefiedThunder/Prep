# Disaster Recovery Runbook

This runbook provides step-by-step procedures for recovering from common production incidents in the Prep application.

## Table of Contents

1. [Emergency Contacts](#emergency-contacts)
2. [Quick Reference](#quick-reference)
3. [Database Recovery](#database-recovery)
4. [Application Recovery](#application-recovery)
5. [Infrastructure Recovery](#infrastructure-recovery)
6. [Security Incidents](#security-incidents)
7. [Data Recovery](#data-recovery)
8. [Post-Incident Procedures](#post-incident-procedures)

---

## Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-Call Engineer | PagerDuty/Slack #oncall | Immediate |
| Database Admin | @db-team | 15 minutes |
| Security Team | @security | Immediate for security incidents |
| Infrastructure Lead | @infra | 30 minutes |

---

## Quick Reference

### Critical Commands

```bash
# Check service status
make health-check

# View logs
docker-compose logs -f --tail=100 python-compliance
docker-compose logs -f --tail=100 node-api

# Restart services
docker-compose restart python-compliance
docker-compose restart node-api

# Emergency shutdown
docker-compose down

# Database backup
./scripts/backup_database.sh --full --upload

# Database restore
./scripts/backup_database.sh --restore backups/backup_YYYYMMDD.sql.gz
```

### Service URLs

| Service | URL | Health Check |
|---------|-----|--------------|
| Python API | http://localhost:8000 | /healthz |
| Node API | http://localhost:3000 | /health |
| PostgreSQL | localhost:5432 | pg_isready |
| Redis | localhost:6379 | redis-cli ping |
| MinIO | localhost:9000 | /minio/health/live |

---

## Database Recovery

### Scenario: Database Unresponsive

**Symptoms:**
- API returns 500 errors
- Logs show "connection refused" or "connection timeout"

**Steps:**

1. **Check PostgreSQL status**
   ```bash
   docker-compose ps postgres
   docker-compose logs --tail=50 postgres
   ```

2. **Check disk space**
   ```bash
   docker exec prepchef-postgres df -h
   ```

3. **Attempt restart**
   ```bash
   docker-compose restart postgres
   ```

4. **If restart fails, check for corruption**
   ```bash
   docker exec prepchef-postgres pg_isready
   ```

5. **If corrupted, restore from backup**
   ```bash
   # Stop dependent services first
   docker-compose stop python-compliance node-api

   # Restore database
   ./scripts/backup_database.sh --restore backups/latest.sql.gz

   # Restart services
   docker-compose up -d
   ```

### Scenario: Database Slow Queries

**Symptoms:**
- API response times > 5 seconds
- Database CPU high

**Steps:**

1. **Identify slow queries**
   ```sql
   SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds';
   ```

2. **Kill long-running queries if necessary**
   ```sql
   SELECT pg_terminate_backend(pid) FROM pg_stat_activity
   WHERE duration > interval '5 minutes';
   ```

3. **Check for missing indexes**
   ```sql
   SELECT schemaname, tablename, indexrelname, idx_scan
   FROM pg_stat_user_indexes
   WHERE idx_scan = 0 AND schemaname = 'public'
   ORDER BY pg_relation_size(indexrelid) DESC;
   ```

### Scenario: Database Out of Connections

**Symptoms:**
- "too many connections" errors
- New requests failing

**Steps:**

1. **Check current connections**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   SELECT max_connections FROM pg_settings WHERE name = 'max_connections';
   ```

2. **Identify connection sources**
   ```sql
   SELECT client_addr, count(*) FROM pg_stat_activity GROUP BY client_addr;
   ```

3. **Terminate idle connections**
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle' AND query_start < now() - interval '10 minutes';
   ```

4. **Scale up connection pool in application config**
   ```python
   # In prep/settings.py
   database_pool_size: int = 20  # Increase from 10
   database_max_overflow: int = 40  # Increase from 20
   ```

---

## Application Recovery

### Scenario: API Service Down

**Symptoms:**
- Health check endpoint returns non-200
- Users cannot access application

**Steps:**

1. **Check service status**
   ```bash
   docker-compose ps
   curl -s http://localhost:8000/healthz
   ```

2. **Check for errors in logs**
   ```bash
   docker-compose logs --tail=100 python-compliance | grep -i error
   ```

3. **Check memory/CPU**
   ```bash
   docker stats prepchef-python-compliance
   ```

4. **Restart the service**
   ```bash
   docker-compose restart python-compliance
   ```

5. **If restart fails, rebuild and redeploy**
   ```bash
   docker-compose build python-compliance
   docker-compose up -d python-compliance
   ```

### Scenario: High Error Rate

**Symptoms:**
- Error rate > 5%
- Grafana alerts firing

**Steps:**

1. **Check error patterns in logs**
   ```bash
   docker-compose logs python-compliance 2>&1 | grep -c "ERROR"
   docker-compose logs python-compliance 2>&1 | grep "ERROR" | tail -20
   ```

2. **Check for recent deployments**
   ```bash
   git log --oneline -5
   ```

3. **If recent deployment caused issues, rollback**
   ```bash
   git revert HEAD
   docker-compose build python-compliance
   docker-compose up -d python-compliance
   ```

4. **Enable debug logging temporarily**
   ```bash
   # Add to environment
   LOG_LEVEL=DEBUG docker-compose up -d python-compliance
   ```

### Scenario: Memory Leak

**Symptoms:**
- Gradual increase in memory usage
- Eventually OOM kill

**Steps:**

1. **Monitor memory**
   ```bash
   docker stats --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
   ```

2. **Take heap dump (if Python)**
   ```python
   # Add to application temporarily
   import tracemalloc
   tracemalloc.start()
   # ... later
   snapshot = tracemalloc.take_snapshot()
   ```

3. **Restart with memory limit**
   ```yaml
   # In docker-compose.yml
   python-compliance:
     deploy:
       resources:
         limits:
           memory: 2G
   ```

4. **Set up periodic restarts**
   ```bash
   # Cron job for scheduled restart
   0 3 * * * docker-compose restart python-compliance
   ```

---

## Infrastructure Recovery

### Scenario: Redis Failure

**Symptoms:**
- Rate limiting not working
- Session issues
- Cache misses

**Steps:**

1. **Check Redis status**
   ```bash
   docker-compose ps redis
   docker exec prepchef-redis redis-cli ping
   ```

2. **Check memory usage**
   ```bash
   docker exec prepchef-redis redis-cli info memory
   ```

3. **Restart Redis**
   ```bash
   docker-compose restart redis
   ```

4. **If data loss occurred, services will rebuild cache automatically**
   - Rate limiting state will reset
   - Sessions may need to be re-established

### Scenario: MinIO/Storage Failure

**Symptoms:**
- File uploads failing
- Document retrieval errors

**Steps:**

1. **Check MinIO status**
   ```bash
   docker-compose ps minio
   curl -s http://localhost:9000/minio/health/live
   ```

2. **Check disk space**
   ```bash
   docker exec prepchef-minio df -h /data
   ```

3. **Restart MinIO**
   ```bash
   docker-compose restart minio
   ```

4. **Verify bucket accessibility**
   ```bash
   docker exec prepchef-minio mc ls local/
   ```

---

## Security Incidents

### Scenario: Suspected Data Breach

**SEVERITY: CRITICAL**

**Immediate Actions:**

1. **Assess scope** (do NOT shut down unless actively ongoing)
   ```bash
   # Check for unusual access patterns
   docker-compose logs python-compliance | grep -E "(401|403|DELETE|admin)" | tail -100
   ```

2. **Preserve evidence**
   ```bash
   # Create full backup
   ./scripts/backup_database.sh --full

   # Export logs
   docker-compose logs > incident_logs_$(date +%Y%m%d_%H%M%S).txt
   ```

3. **Rotate compromised credentials**
   ```bash
   # Generate new JWT secret
   openssl rand -base64 32

   # Update .env and restart
   docker-compose down
   docker-compose up -d
   ```

4. **Notify security team and legal**

5. **Enable enhanced logging**

### Scenario: DDoS Attack

**Symptoms:**
- Massive traffic spike
- Service degradation
- Rate limiting overwhelmed

**Steps:**

1. **Identify attack pattern**
   ```bash
   # Check top IPs
   docker-compose logs node-api | grep -oE '[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | sort | uniq -c | sort -rn | head -20
   ```

2. **Enable aggressive rate limiting**
   ```bash
   # Lower rate limits temporarily
   RATE_LIMIT_DEFAULT=10 RATE_LIMIT_WINDOW=60 docker-compose up -d python-compliance
   ```

3. **Block malicious IPs at infrastructure level**
   - Update cloud firewall rules
   - Enable WAF rules

4. **Scale horizontally if possible**
   ```bash
   docker-compose up -d --scale python-compliance=3
   ```

### Scenario: Exposed Secrets

**Steps:**

1. **Identify exposed secret type**

2. **Rotate immediately**
   ```bash
   # JWT Secret
   export JWT_SECRET=$(openssl rand -base64 32)

   # Database password
   # This requires coordinated update

   # API keys
   # Regenerate through provider dashboards
   ```

3. **Search for unauthorized usage**
   ```bash
   # Check git history
   git log -p --all -S 'SECRET_VALUE'
   ```

4. **Run gitleaks to find other exposures**
   ```bash
   gitleaks detect --source . --verbose
   ```

---

## Data Recovery

### Scenario: Accidental Data Deletion

**Steps:**

1. **Stop write operations immediately**
   ```bash
   # Put app in maintenance mode
   docker-compose stop node-api python-compliance
   ```

2. **Identify time of deletion**
   ```bash
   # Check audit logs
   SELECT * FROM audit_log WHERE event_type LIKE '%DELETE%' ORDER BY created_at DESC LIMIT 10;
   ```

3. **Restore from backup**
   ```bash
   # List available backups
   ./scripts/backup_database.sh --list

   # Restore to point before deletion
   ./scripts/backup_database.sh --restore backups/backup_YYYYMMDD.sql.gz
   ```

4. **Replay any valid transactions that occurred after backup**

---

## Post-Incident Procedures

### Immediate (Within 1 hour)

1. **Document timeline of events**
2. **Verify service restoration**
3. **Notify stakeholders**

### Short-term (Within 24 hours)

1. **Conduct initial post-mortem**
2. **Identify root cause**
3. **Create tickets for permanent fixes**

### Long-term (Within 1 week)

1. **Complete written post-mortem report**
2. **Implement preventive measures**
3. **Update this runbook if needed**
4. **Schedule post-mortem review meeting**

### Post-Mortem Template

```markdown
## Incident Post-Mortem: [Title]

**Date:** YYYY-MM-DD
**Duration:** X hours Y minutes
**Severity:** P1/P2/P3
**Author:**

### Summary
Brief description of what happened.

### Timeline
- HH:MM - First alert
- HH:MM - Investigation started
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - All clear

### Root Cause
Technical explanation of why the incident occurred.

### Impact
- Users affected: X
- Revenue impact: $X
- Data loss: Yes/No

### Resolution
How was the incident resolved?

### Lessons Learned
What went well? What went poorly?

### Action Items
- [ ] Item 1 (Owner, Due date)
- [ ] Item 2 (Owner, Due date)
```

---

## Appendix

### Useful Aliases

Add to your shell profile:

```bash
alias prep-logs='docker-compose logs -f --tail=100'
alias prep-health='curl -s http://localhost:8000/healthz && curl -s http://localhost:3000/health'
alias prep-restart='docker-compose restart'
alias prep-backup='./scripts/backup_database.sh --full --upload'
alias prep-db='docker exec -it prepchef-postgres psql -U postgres prepchef'
```

### Monitoring Dashboards

- Grafana: http://localhost:3001
- Prometheus: http://localhost:9090
- MinIO Console: http://localhost:9001

### Log Locations

| Service | Container Log | Persistent Log |
|---------|--------------|----------------|
| Python API | docker-compose logs python-compliance | /var/log/prep/api.log |
| Node API | docker-compose logs node-api | stdout |
| PostgreSQL | docker-compose logs postgres | /var/lib/postgresql/data/log/ |
| Redis | docker-compose logs redis | stdout |

---

*Last Updated: November 2025*
*Version: 1.0*
