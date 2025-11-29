# Production Deployment Checklist

This checklist ensures all critical items are verified before deploying the Prep platform to production.

## Pre-Deployment Checklist

### 1. Infrastructure

- [ ] **Database**
  - [ ] PostgreSQL 15+ with PostGIS extension installed
  - [ ] Connection pool sized appropriately (see `prep/database/pool_config.py`)
  - [ ] SSL/TLS enabled for connections
  - [ ] Read replicas configured (if needed)
  - [ ] Automated backups enabled (see `scripts/backup_database.sh`)
  - [ ] Point-in-time recovery tested
  - [ ] Database monitoring enabled

- [ ] **Redis**
  - [ ] Redis 7+ deployed
  - [ ] Persistence configured (AOF recommended)
  - [ ] Memory limits set
  - [ ] Eviction policy configured (allkeys-lru for cache)
  - [ ] Password authentication enabled
  - [ ] TLS enabled

- [ ] **Object Storage (MinIO/S3)**
  - [ ] Bucket created and accessible
  - [ ] CORS configured for frontend access
  - [ ] Access credentials secured
  - [ ] Versioning enabled for critical buckets
  - [ ] Lifecycle policies for cost management

### 2. Security

- [ ] **Secrets Management**
  - [ ] All secrets stored in secure vault (AWS Secrets Manager, HashiCorp Vault, etc.)
  - [ ] No secrets in source code or environment files
  - [ ] `JWT_SECRET` is cryptographically random (min 256 bits)
  - [ ] `STRIPE_SECRET_KEY` is production key
  - [ ] Database credentials are unique and strong

- [ ] **Network Security**
  - [ ] HTTPS enforced (TLS 1.3 preferred)
  - [ ] Valid SSL certificates installed
  - [ ] HSTS headers enabled
  - [ ] CORS configured with specific origins (no wildcards)
  - [ ] Rate limiting enabled (see `middleware/rate_limiter.py`)
  - [ ] WAF/DDoS protection in place

- [ ] **Application Security**
  - [ ] Security headers configured (CSP, X-Frame-Options, etc.)
  - [ ] Input validation enabled (see `middleware/request_validation.py`)
  - [ ] SQL injection prevention verified
  - [ ] XSS prevention verified
  - [ ] CSRF protection enabled
  - [ ] Authentication/authorization tested
  - [ ] Audit logging enabled

### 3. Observability

- [ ] **Logging**
  - [ ] Structured JSON logging enabled (`LOG_FORMAT=json`)
  - [ ] Log level set appropriately (`LOG_LEVEL=INFO` or `WARNING`)
  - [ ] Correlation IDs enabled
  - [ ] Sensitive data masking verified
  - [ ] Log aggregation configured (Loki/ELK)
  - [ ] Log retention policy set

- [ ] **Metrics**
  - [ ] Prometheus metrics exposed at `/metrics`
  - [ ] Custom application metrics configured
  - [ ] Grafana dashboards deployed
  - [ ] SLO/SLI dashboards configured

- [ ] **Alerting**
  - [ ] Prometheus alerting rules deployed (`grafana/alerts/prometheus_rules.yaml`)
  - [ ] Alert notification channels configured (Slack, PagerDuty, etc.)
  - [ ] On-call rotation established
  - [ ] Runbook links in alert annotations

- [ ] **Tracing**
  - [ ] Distributed tracing enabled (if applicable)
  - [ ] Trace sampling rate configured
  - [ ] Trace storage configured

### 4. Health & Resilience

- [ ] **Health Checks**
  - [ ] `/health` endpoint returns dependency status
  - [ ] `/ready` endpoint for Kubernetes readiness
  - [ ] `/live` endpoint for Kubernetes liveness
  - [ ] Health check endpoints excluded from auth

- [ ] **Circuit Breakers**
  - [ ] Circuit breakers configured for external services
  - [ ] Failure thresholds tuned
  - [ ] Recovery timeouts appropriate

- [ ] **Retry Logic**
  - [ ] Exponential backoff configured
  - [ ] Retry budgets prevent retry storms
  - [ ] Idempotent operations properly handled

- [ ] **Graceful Shutdown**
  - [ ] SIGTERM handled correctly
  - [ ] Connection draining enabled
  - [ ] Cleanup hooks registered

### 5. Performance

- [ ] **Application**
  - [ ] Worker count optimized for CPU cores
  - [ ] Async operations used where appropriate
  - [ ] Database queries optimized
  - [ ] N+1 queries eliminated
  - [ ] Caching strategy implemented

- [ ] **Resource Limits**
  - [ ] Memory limits set
  - [ ] CPU limits set
  - [ ] Request body size limits enforced
  - [ ] Connection limits configured

### 6. Deployment Configuration

- [ ] **Environment Variables**
  - [ ] All required variables documented
  - [ ] `.env.example` reflects production needs
  - [ ] No development defaults in production

- [ ] **Container Configuration**
  - [ ] Production Dockerfile used
  - [ ] Non-root user configured
  - [ ] Read-only root filesystem (if possible)
  - [ ] Security context configured

- [ ] **Kubernetes (if applicable)**
  - [ ] Resource requests/limits set
  - [ ] PodDisruptionBudget configured
  - [ ] Horizontal Pod Autoscaler configured
  - [ ] Network policies applied
  - [ ] Service mesh configured (if used)

### 7. Testing

- [ ] **Pre-Production Testing**
  - [ ] All unit tests passing
  - [ ] Integration tests passing
  - [ ] E2E tests passing
  - [ ] Performance/load tests completed
  - [ ] Security scan passed (SAST/DAST)
  - [ ] Dependency vulnerability scan passed

- [ ] **Staging Verification**
  - [ ] Staging mirrors production config
  - [ ] Smoke tests pass in staging
  - [ ] No critical errors in logs

### 8. Documentation

- [ ] **Runbooks**
  - [ ] `RUNBOOK.md` up to date
  - [ ] Disaster recovery documented (`docs/DISASTER_RECOVERY_RUNBOOK.md`)
  - [ ] Incident response procedures defined
  - [ ] Escalation paths documented

- [ ] **Architecture**
  - [ ] System architecture documented
  - [ ] Data flow diagrams available
  - [ ] API documentation current

## Deployment Steps

### 1. Pre-Deployment

```bash
# 1. Run tests
make test

# 2. Run security scan
make security-scan

# 3. Build production image
docker build -t prep-api:${VERSION} -f Dockerfile .

# 4. Tag and push
docker tag prep-api:${VERSION} registry.example.com/prep-api:${VERSION}
docker push registry.example.com/prep-api:${VERSION}
```

### 2. Database Migration

```bash
# 1. Backup database
./scripts/backup_database.sh --mode full

# 2. Run migrations
alembic upgrade head

# 3. Verify migration
alembic current
```

### 3. Deployment

```bash
# Kubernetes
kubectl apply -f k8s/

# Or Docker Compose
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Post-Deployment Verification

```bash
# 1. Check health
curl https://api.prep.io/health

# 2. Check readiness
curl https://api.prep.io/ready

# 3. Run smoke tests
./scripts/smoke_tests.sh

# 4. Monitor metrics
open https://grafana.prep.io/d/prep-overview

# 5. Check logs
kubectl logs -f deployment/prep-api
```

## Rollback Procedure

If issues are detected post-deployment:

### 1. Quick Rollback

```bash
# Kubernetes
kubectl rollout undo deployment/prep-api

# Docker Compose
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --scale api=0
# Restore previous image
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Database Rollback (if needed)

```bash
# Downgrade migration
alembic downgrade -1

# Or restore from backup
./scripts/backup_database.sh --mode restore --file backup_20251128.sql.gz
```

## Post-Deployment Monitoring

For the first 24 hours after deployment, monitor:

1. **Error Rate**: Should remain < 1%
2. **Latency**: P95 should be < 500ms
3. **Throughput**: Should match or exceed previous deployment
4. **Resource Usage**: CPU and memory within limits
5. **Business Metrics**: No anomalies in bookings, payments, etc.

## Contacts

| Role | Name | Contact |
|------|------|---------|
| On-Call Engineer | Rotation | #oncall-primary |
| Platform Lead | TBD | platform@prep.io |
| Database Admin | TBD | dba@prep.io |
| Security | TBD | security@prep.io |

---

*Last Updated: November 2025*
