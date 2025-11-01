# Incident Response Runbook (J33)

This runbook provides step-by-step procedures for common incidents and emergency scenarios.

## Emergency Contacts

- **On-Call Engineer**: Pager Duty rotation
- **Security Team**: security@prepchef.com
- **Database Team**: dba@prepchef.com
- **CEO**: CEO contact (for major incidents)

## Severity Levels

- **P0 (Critical)**: Service completely down, data loss, security breach
- **P1 (High)**: Major feature unavailable, significant user impact
- **P2 (Medium)**: Minor feature degraded, limited user impact
- **P3 (Low)**: No immediate user impact

## Incident Response Process

1. **Acknowledge** - Acknowledge alert in PagerDuty
2. **Assess** - Determine severity and impact
3. **Communicate** - Post in #incidents Slack channel
4. **Mitigate** - Take immediate action to restore service
5. **Resolve** - Fix root cause
6. **Document** - Write post-mortem (P0/P1 only)

## Synthetic Monitoring & Alerting

- **Coverage**: `perf/synthetics/run_synthetics.py` exercises the San Francisco and Joshua Tree
  `/city/{slug}/requirements` and `/city/{slug}/requirements/estimate` endpoints.
- **SLO**: p95 latency &lt; 200 ms across 5 samples per endpoint (configurable via `SYNTHETIC_THRESHOLD_MS`).
- **CI**: `.github/workflows/synthetics.yml` runs hourly and publishes `perf/synthetics/out/latest.json`
  to GitHub Pages for the status dashboard.
- **Alerting Hooks**:
  - **PagerDuty**: Configure the GitHub Action to call the `OBS_ALERT_WEBHOOK` repository secret on failure.
  - **Slack**: The Pages artifact powers `apps/web/src/pages/StatusPage.tsx`; degraded status is surfaced in
    `#observability` via the existing Grafana webhook (see `modules/observability/alerts.py`).
- **Runbook Linkage**: Incidents displayed on the status page must include a runbook URL in the
  `remediations` array pointing back to the relevant section in this document when available.

## Scheduled Jobs

### Finance payout reconciliation

- **Cadence**: Nightly at 02:00 UTC (`0 2 * * *`)
- **Purpose**: Compares host payout records with GAAP ledger exports and emits a reconciliation summary for finance operations.
- **Alerting**: Missed SLA events trigger the shared observability callback (`modules/observability/alerts.py`) which records a metric and structured log entry for investigation.

---

## Common Incidents

### 1. Database Backup Restore

**When**: Data corruption, accidental deletion, ransomware

**Steps:**

1. **Identify backup to restore:**
```bash
# List available backups
aws s3 ls s3://prepchef-backups/postgres/

# Check backup metadata
aws s3 cp s3://prepchef-backups/postgres/backup-2025-01-20.sql.gz - | gunzip | head -20
```

2. **Stop application servers:**
```bash
kubectl scale deployment node-api --replicas=0 -n prepchef
kubectl scale deployment python-compliance --replicas=0 -n prepchef
```

3. **Restore database:**
```bash
# Download backup
aws s3 cp s3://prepchef-backups/postgres/backup-2025-01-20.sql.gz /tmp/

# Restore to new database first (safety)
createdb prepchef_restore
gunzip < /tmp/backup-2025-01-20.sql.gz | psql prepchef_restore

# Verify restore
psql prepchef_restore -c "SELECT COUNT(*) FROM bookings;"

# If verified, swap databases
psql -c "ALTER DATABASE prepchef RENAME TO prepchef_old;"
psql -c "ALTER DATABASE prepchef_restore RENAME TO prepchef;"
```

4. **Restart application servers:**
```bash
kubectl scale deployment node-api --replicas=2 -n prepchef
kubectl scale deployment python-compliance --replicas=2 -n prepchef
```

5. **Verify application:**
```bash
curl https://api.prepchef.com/health
curl https://prepchef.com
```

**Rollback**: Swap databases back if issues occur.

---

### 2. Revoke Stripe Keys (Compromised)

**When**: Stripe secret key exposed in logs, code, or third-party breach

**Steps:**

1. **Immediately delete compromised key:**
   - Log in to Stripe Dashboard: https://dashboard.stripe.com
   - Navigate to Developers → API Keys
   - Click "Delete" on compromised secret key
   - Confirm deletion

2. **Generate new restricted API key:**
   - Click "Create secret key"
   - Select "Restricted key"
   - Enable only required permissions:
     - Payment Intents: Write
     - Customers: Write
     - Refunds: Write
   - Copy new key

3. **Update secrets in production:**
```bash
# Update Kubernetes secret
kubectl create secret generic prepchef-secrets \
  --from-literal=STRIPE_SECRET_KEY='sk_live_NEW_KEY' \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart
kubectl rollout restart deployment/node-api -n prepchef
kubectl rollout restart deployment/payments-svc -n prepchef
```

4. **Monitor for unauthorized charges:**
   - Review Stripe Dashboard for suspicious activity (last 24 hours)
   - Check application logs for unusual payment patterns
   - Set up alerts for refunds/chargebacks

5. **Audit and document:**
   - Log incident in security log
   - Identify how key was compromised
   - Update security procedures to prevent recurrence

**Post-Incident**: Rotate webhook secrets, review IAM permissions.

---

### 3. Disable Payments (Emergency Stop)

**When**: Fraudulent bookings, payment processor outage, critical bug

**Steps:**

1. **Set maintenance mode flag:**
```bash
kubectl set env deployment/payments-svc PAYMENTS_ENABLED=false -n prepchef
```

2. **Update frontend banner:**
```bash
kubectl set env deployment/frontend MAINTENANCE_MESSAGE="Payments temporarily unavailable" -n prepchef
```

3. **Redirect payment endpoint:**
```yaml
# Apply emergency Ingress rule
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: payments-maintenance
  annotations:
    nginx.ingress.kubernetes.io/server-snippet: |
      location /api/payments {
        return 503 "Payments temporarily disabled";
      }
```

4. **Communicate to users:**
   - Post status update: status.prepchef.com
   - Send email to active users with pending bookings
   - Update social media

5. **Investigate root cause:**
   - Check logs: `kubectl logs -l app=payments-svc --since=1h`
   - Review recent deployments
   - Check Stripe Dashboard for errors

**Re-enable:**
```bash
kubectl set env deployment/payments-svc PAYMENTS_ENABLED=true -n prepchef
kubectl delete ingress payments-maintenance -n prepchef
```

---

### 4. High Database Load (CPU > 90%)

**When**: Slow queries, missing indexes, DDoS attack

**Steps:**

1. **Identify slow queries:**
```sql
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds'
ORDER BY duration DESC;
```

2. **Kill long-running queries (if safe):**
```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'active' AND now() - query_start > interval '10 minutes';
```

3. **Enable connection pooling limits:**
```bash
# Reduce max connections temporarily
psql -c "ALTER SYSTEM SET max_connections = 50;"
psql -c "SELECT pg_reload_conf();"
```

4. **Scale read replicas (if available):**
```bash
kubectl scale deployment postgres-read --replicas=3 -n prepchef
```

5. **Add missing indexes:**
```sql
-- Example: bookings table
CREATE INDEX CONCURRENTLY idx_bookings_kitchen_time
ON bookings (kitchen_id, start_time, end_time);
```

**Post-Incident**: Review query performance, add caching (Redis), consider read replicas.

---

### 5. Redis Memory Full

**When**: Redis eviction, OOM errors

**Steps:**

1. **Check memory usage:**
```bash
redis-cli INFO memory
```

2. **Flush expired keys:**
```bash
redis-cli FLUSHALL ASYNC  # Caution: clears all data
# Or more conservative:
redis-cli --scan --pattern "booking:lock:*" | xargs redis-cli DEL
```

3. **Increase memory limit (temporary):**
```bash
kubectl set env deployment/redis REDIS_MAXMEMORY=2gb -n prepchef
```

4. **Configure eviction policy:**
```bash
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

**Long-term**: Upgrade Redis instance size, implement TTLs on all keys.

---

### 6. SSL Certificate Expiration

**When**: Certificate expires, Let's Encrypt renewal fails

**Steps:**

1. **Check certificate expiration:**
```bash
echo | openssl s_client -connect prepchef.com:443 2>/dev/null | openssl x509 -noout -dates
```

2. **Renew with cert-manager:**
```bash
kubectl delete certificaterequest -l app=prepchef -n prepchef
kubectl annotate certificate prepchef-tls cert-manager.io/issue-temporary-certificate="true" -n prepchef
```

3. **Manual renewal (if cert-manager fails):**
```bash
certbot renew --force-renewal --cert-name prepchef.com
kubectl create secret tls prepchef-tls --cert=/etc/letsencrypt/live/prepchef.com/fullchain.pem --key=/etc/letsencrypt/live/prepchef.com/privkey.pem -n prepchef
```

---

## Emergency Communication Template

```
**Incident**: [Brief description]
**Severity**: P0 | P1 | P2 | P3
**Impact**: [User-facing impact]
**Status**: Investigating | Mitigating | Resolved
**ETA**: [Estimated time to resolution]
**Incident Commander**: [Name]
**Updates**: [Link to status page]
```

## Post-Incident Review

Within 48 hours of P0/P1 incidents:

1. Schedule post-mortem meeting
2. Document timeline of events
3. Identify root cause(s)
4. List action items to prevent recurrence
5. Assign owners and deadlines
6. Publish post-mortem (internally)

---

## Useful Commands

**Check service health:**
```bash
curl https://api.prepchef.com/health
```

**View recent logs:**
```bash
kubectl logs -l app=node-api --since=1h -n prepchef | grep ERROR
```

**Scale services:**
```bash
kubectl scale deployment node-api --replicas=5 -n prepchef
```

**Rollback deployment:**
```bash
kubectl rollout undo deployment/node-api -n prepchef
```

**Check resource usage:**
```bash
kubectl top pods -n prepchef
kubectl top nodes
```

---

For unlisted incidents, escalate to on-call engineer immediately.
