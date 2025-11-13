# API Versioning Policy

## Purpose

This document defines how we version, deprecate, and maintain our APIs to ensure stability for external consumers while allowing internal iteration.

---

## API Classification

All APIs are classified into one of three categories using decorators/annotations:

### 1. **Public API** (`@public_api`)

**Definition**: Stable, versioned APIs consumed by external parties (partners, customers, integrations).

**Guarantees**:
- ✅ Semantic versioning (v1, v2, etc.)
- ✅ Minimum 6-month deprecation notice
- ✅ Backward compatibility within major versions
- ✅ Comprehensive documentation
- ✅ Published OpenAPI specs
- ✅ Rate limiting and authentication required

**Examples**:
```python
@public_api(version="v1", since="2025-01-01")
@router.get("/api/v1/properties/{property_id}/compliance")
async def get_compliance_status(property_id: str):
    """Get compliance status for a property (Public API)"""
    pass
```

**Breaking changes** (require major version bump):
- Removing or renaming fields
- Changing field types
- Removing endpoints
- Changing authentication requirements
- Changing rate limits (downward)

**Non-breaking changes** (allowed within version):
- Adding new optional fields
- Adding new endpoints
- Adding new query parameters (optional)
- Improving error messages

---

### 2. **Internal Service API** (`@internal_service_api`)

**Definition**: APIs consumed by other Prep platform services (service-to-service communication).

**Guarantees**:
- ✅ Best-effort backward compatibility
- ✅ 2-week deprecation notice (internal communication)
- ⚠️ Can evolve faster than public APIs
- ✅ Internal documentation required
- ✅ Service mesh authentication

**Examples**:
```python
@internal_service_api(service="compliance-engine")
@router.post("/internal/v1/evaluate-rules")
async def evaluate_compliance_rules(request: RuleEvaluationRequest):
    """Evaluate compliance rules (Internal API)"""
    pass
```

**Versioning strategy**:
- Use `/internal/v1/` prefix
- Version bumps coordinated across service deployments
- Use feature flags for gradual rollout

---

### 3. **Experimental API** (`@experimental_api`)

**Definition**: Unstable APIs under active development. No compatibility guarantees.

**Guarantees**:
- ⚠️ **ZERO** backward compatibility guarantees
- ⚠️ Can be removed or changed without notice
- ⚠️ Not documented in public docs
- ✅ Must include "X-Experimental-API: true" header

**Examples**:
```python
@experimental_api(feature="ai-recommendations")
@router.get("/experimental/v1/ai/recommendations")
async def get_ai_recommendations():
    """Experimental AI recommendations (NO GUARANTEES)"""
    pass
```

**Requirements**:
- Must include warning in response headers:
  ```
  X-API-Stability: experimental
  X-API-Warning: This API may change or be removed without notice
  ```
- Must require explicit opt-in via header:
  ```
  X-Experimental-API: true
  ```

---

## Versioning Strategy

### URL-Based Versioning (Preferred)

Public APIs use URL-based versioning for clarity:

```
/api/v1/properties          # Version 1
/api/v2/properties          # Version 2 (breaking changes)
```

### Header-Based Versioning (Internal)

Internal service APIs can use header-based versioning:

```
Accept: application/vnd.prep.v1+json
```

---

## Deprecation Process

### For Public APIs:

1. **T-6 months**: Announce deprecation
   - Add `X-API-Deprecated: true` header to responses
   - Add `X-API-Sunset: 2025-07-01` header
   - Update documentation with deprecation notice
   - Email all known API consumers

2. **T-3 months**: Increase warnings
   - Log deprecation warnings (visible in API consumer dashboards)
   - Add deprecation banner to API documentation

3. **T-1 month**: Final notice
   - Send final email to all API consumers
   - Add rate limiting to deprecated endpoints (soft enforcement)

4. **T-0**: Sunset
   - Return `410 Gone` status code
   - Include link to migration guide in response

### For Internal Service APIs:

1. **T-2 weeks**: Announce in engineering Slack
2. **T-1 week**: Deploy new version alongside old (dual-running)
3. **T-0**: Switch traffic to new version
4. **T+1 week**: Remove old version

### For Experimental APIs:

- Can be removed immediately with no notice
- Best effort: 1-week heads-up in changelog

---

## Version Lifecycle

| Version | Status | Support Level | Breaking Changes Allowed? |
|---------|--------|---------------|---------------------------|
| **v1** (current) | Active | Full support + bug fixes | ❌ No |
| **v0** (deprecated) | Deprecated | Security fixes only | ❌ Frozen |
| **v-1** (sunsetted) | Sunset | No support | N/A (removed) |

### Lifecycle Stages:

1. **Active**: Current version, receives new features and bug fixes
2. **Maintenance**: Previous version, receives bug fixes only (6 months)
3. **Deprecated**: No new features, security fixes only (6 months)
4. **Sunset**: Removed, returns `410 Gone`

---

## Implementation Guidelines

### Python (FastAPI)

```python
from prep.api.decorators import public_api, internal_service_api, experimental_api

@public_api(version="v1", since="2025-01-01")
@router.get("/api/v1/compliance/status")
async def get_compliance_status():
    """Public API for compliance status"""
    pass

@internal_service_api(service="compliance-engine")
@router.post("/internal/v1/evaluate")
async def evaluate_rules():
    """Internal service API"""
    pass

@experimental_api(feature="ai-compliance-copilot")
@router.get("/experimental/v1/copilot/suggest")
async def ai_suggest():
    """Experimental AI feature"""
    pass
```

### TypeScript (Express/NestJS)

```typescript
import { PublicApi, InternalApi, ExperimentalApi } from '@prep/api-decorators';

@PublicApi({ version: 'v1', since: '2025-01-01' })
@Get('/api/v1/compliance/status')
async getComplianceStatus() {
  // Public API implementation
}

@InternalApi({ service: 'compliance-engine' })
@Post('/internal/v1/evaluate')
async evaluateRules() {
  // Internal API implementation
}

@ExperimentalApi({ feature: 'ai-compliance-copilot' })
@Get('/experimental/v1/copilot/suggest')
async aiSuggest() {
  // Experimental API implementation
}
```

---

## Monitoring & Metrics

Track these metrics per API classification:

| Metric | Public API Alert Threshold | Internal API Alert Threshold |
|--------|---------------------------|------------------------------|
| Error rate | > 0.5% | > 2% |
| P95 latency | > 500ms | > 1000ms |
| Deprecated API usage | > 10% of total traffic | N/A |
| Breaking change violations | 0 (strict) | 0 (strict) |

---

## OpenAPI Spec Generation

Public APIs must have OpenAPI 3.1 specs auto-generated:

```bash
# Generate OpenAPI spec for public APIs only
poetry run python -m prep.api.generate_openapi \
  --output openapi.yaml \
  --include public_api

# Validate no breaking changes between versions
poetry run python -m prep.api.validate_compatibility \
  --old openapi-v1.yaml \
  --new openapi-v2.yaml
```

---

## Breaking Change Detection (CI/CD)

Automated checks in CI pipeline:

```yaml
# .github/workflows/api-validation.yml
- name: Detect Breaking Changes
  run: |
    poetry run python -m prep.api.breaking_changes \
      --base origin/main \
      --head HEAD \
      --fail-on-breaking
```

This fails CI if breaking changes are detected in Public APIs without version bump.

---

## Migration Guides

When introducing breaking changes, provide migration guides:

```markdown
# Migration Guide: v1 → v2

## Breaking Changes

### 1. Field Renames
- `property_id` → `id`
- `compliance_status` → `status`

### 2. Removed Fields
- `legacy_field` (removed, no replacement)

### 3. New Required Fields
- `jurisdiction_code` (ISO 3166-2 code)

## Migration Steps

1. Update property ID references:
   ```diff
   - const id = response.property_id
   + const id = response.id
   ```

2. Add jurisdiction codes:
   ```diff
   {
     "property_id": "123",
   + "jurisdiction_code": "US-CA-SF"
   }
   ```

## Automated Migration Tool

```bash
prep-migrate v1-to-v2 --input api-calls.json --output migrated.json
```
```

---

## Exceptions & Overrides

**Security vulnerabilities**: Can be fixed in any API version immediately, even if breaking.

**Process**:
1. Fix vulnerability in all active versions
2. Publish security advisory
3. Notify all API consumers within 24 hours
4. Provide upgrade path or workaround

---

## Document Metadata

- **Version**: 1.0
- **Last Updated**: 2025-11-13
- **Owner**: Platform Engineering + Product
- **Approval Required**: CTO for Public API breaking changes
- **Review Cycle**: Quarterly

---

## Related Documents

- [Product Spine](./PRODUCT_SPINE.md)
- [Architecture Overview](./architecture.md)
- [OpenAPI Specification](../openapi.yaml)
