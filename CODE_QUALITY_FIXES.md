# CODE QUALITY FIXES - ACTIONABLE REFACTORING GUIDE

## Quick Links to Generated Reports
- **Comprehensive Analysis:** [CODE_QUALITY_ANALYSIS.md](CODE_QUALITY_ANALYSIS.md)
- **Detailed Issues & File Paths:** [CODE_QUALITY_ISSUES_DETAILS.md](CODE_QUALITY_ISSUES_DETAILS.md)

---

## PHASE 1: CRITICAL ISSUES (1-2 Weeks)

### Fix #1: Add Error Boundaries to React Components

**Status:** CRITICAL - Prevents app crashes from propagating  
**Time Estimate:** 2-3 hours

#### Step 1: Create ErrorBoundary Component
```tsx
// harborhomes/components/error-boundary.tsx
'use client';

import React, { ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log to external service (Sentry, etc.)
    console.error('Component error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="flex items-center gap-4 p-8 bg-red-50 border border-red-200 rounded-lg">
          <AlertCircle className="text-red-600" />
          <div>
            <h2 className="font-semibold text-red-900">Something went wrong</h2>
            <p className="text-sm text-red-700">Please refresh the page to continue.</p>
            <button 
              onClick={() => window.location.reload()}
              className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Refresh
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

#### Step 2: Wrap Root Layout
```tsx
// harborhomes/app/layout.tsx
import { ErrorBoundary } from '@/components/error-boundary';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <ErrorBoundary>
          <Providers>{children}</Providers>
        </ErrorBoundary>
      </body>
    </html>
  );
}
```

#### Step 3: Add Error Handling to Auth Pages
```tsx
// harborhomes/app/(site)/auth/sign-in/page.tsx
'use client';

import { useState } from 'react';
import { ErrorBoundary } from '@/components/error-boundary';

export default function SignInPage() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    
    try {
      // Sign-in logic
      const response = await fetch('/api/auth/sign-in', {
        method: 'POST',
        body: new FormData(e.currentTarget),
      });
      
      if (!response.ok) {
        const data = await response.json();
        setError(data.message || 'Sign-in failed');
        return;
      }
      
      // Success handling
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ErrorBoundary>
      <form onSubmit={handleSubmit}>
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded text-red-700">
            {error}
          </div>
        )}
        {/* Form fields */}
        <button disabled={loading} type="submit">
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </ErrorBoundary>
  );
}
```

**Verification:**
```bash
# Test error boundary
npm run test -- ErrorBoundary.spec.tsx
```

---

### Fix #2: Refactor AnalyticsDashboardAPI (1,504 lines)

**Status:** CRITICAL - Violates Single Responsibility Principle  
**Time Estimate:** 3-4 days  
**Approach:** Extract into 4 focused services

#### Step 1: Create Base Analytics Service
```python
# prep/analytics/base_service.py
from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseAnalyticsService(ABC, Generic[T]):
    """Base class for analytics computation."""
    
    def __init__(self, session: AsyncSession, redis: RedisProtocol):
        self.session = session
        self.redis = redis
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def get_cached(self, key: str, model_type: type[T]) -> T | None:
        """Get cached analytics result."""
        try:
            raw = await self.redis.get(key)
            if raw:
                return model_type.model_validate_json(raw)
        except Exception as exc:
            self.logger.warning(f"Cache miss for {key}: {exc}")
        return None
    
    async def set_cache(self, key: str, value: T, ttl: int) -> None:
        """Cache analytics result."""
        try:
            await self.redis.setex(key, ttl, value.model_dump_json())
        except Exception as exc:
            self.logger.warning(f"Failed to cache {key}: {exc}")
    
    @abstractmethod
    async def compute(self, *args, **kwargs) -> T:
        """Implement analytics computation."""
        pass
```

#### Step 2: Create Host Analytics Service
```python
# prep/analytics/host_service.py
from prep.analytics.base_service import BaseAnalyticsService
from prep.models.pydantic_exports import HostOverview, BookingAnalytics

class HostAnalyticsService(BaseAnalyticsService):
    """Analytics for individual hosts."""
    
    async def get_overview(self, host_id: UUID) -> HostOverview:
        cache_key = f"analytics:host:{host_id}:overview"
        cached = await self.get_cached(cache_key, HostOverview)
        if cached:
            return cached
        
        overview = await self._compute_overview(host_id)
        await self.set_cache(cache_key, overview, TTL_HOST)
        return overview
    
    async def get_booking_analytics(
        self, host_id: UUID, timeframe: Timeframe
    ) -> BookingAnalytics:
        cache_key = f"analytics:host:{host_id}:bookings:{timeframe.value}"
        cached = await self.get_cached(cache_key, BookingAnalytics)
        if cached:
            return cached
        
        analytics = await self._compute_booking_analytics(host_id, timeframe)
        await self.set_cache(cache_key, analytics, TTL_HOST)
        return analytics
    
    async def _compute_overview(self, host_id: UUID) -> HostOverview:
        """Business logic extracted from dashboard_api.py"""
        # Implementation here
        pass
    
    async def _compute_booking_analytics(
        self, host_id: UUID, timeframe: Timeframe
    ) -> BookingAnalytics:
        """Business logic extracted from dashboard_api.py"""
        # Implementation here
        pass
```

#### Step 3: Create Platform Analytics Service
```python
# prep/analytics/platform_service.py
class PlatformAnalyticsService(BaseAnalyticsService):
    """Platform-wide analytics."""
    
    async def get_overview(self) -> PlatformOverviewMetrics:
        cache_key = "analytics:platform:overview"
        cached = await self.get_cached(cache_key, PlatformOverviewMetrics)
        if cached:
            return cached
        
        overview = await self._compute_overview()
        await self.set_cache(cache_key, overview, TTL_PLATFORM)
        return overview
    
    # ... other platform-level methods
```

#### Step 4: Update API Routes
```python
# prep/api/analytics_router.py
from prep.analytics.host_service import HostAnalyticsService
from prep.analytics.platform_service import PlatformAnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

@router.get("/hosts/{host_id}/overview")
async def get_host_overview(
    host_id: UUID,
    service: HostAnalyticsService = Depends(),
):
    return await service.get_overview(host_id)

@router.get("/platform/overview")
async def get_platform_overview(
    service: PlatformAnalyticsService = Depends(),
):
    return await service.get_overview()
```

**Verification:**
```bash
# Run tests for new services
pytest tests/analytics/test_host_service.py -v
pytest tests/analytics/test_platform_service.py -v

# Check old API still works (backward compatibility)
pytest tests/api/test_analytics.py -v
```

---

### Fix #3: Add Module Docstrings (8 Files)

**Status:** HIGH - Impacts onboarding  
**Time Estimate:** 4-5 hours

#### Example: /prep/regulatory/writer.py
```python
"""
prep.regulatory.writer
======================

Handles regulatory document writing and persistence.

This module provides the core functionality for writing regulatory
documents to storage and tracking their validation status.

Components:
-----------
RegulatoryWriter
    Main interface for regulatory document persistence.
    
    Methods:
        write_requirement(requirement_id, content)
        write_license(license_id, data)
        write_certification(cert_id, evidence)
    
ValidationEngine
    Validates regulatory documents against requirements.
    
    Methods:
        validate_requirement_data(req_id, data) -> List[Violation]

StorageManager
    Manages persistent storage of documents (S3, database).
    
    Methods:
        store_document(doc_id, content) -> str (location)
        retrieve_document(location) -> bytes

Usage Example:
    >>> writer = RegulatoryWriter(session, storage)
    >>> await writer.write_requirement(req_id, requirement_data)
    >>> violations = await writer.validate(req_id)
    >>> if not violations:
    >>>     await writer.mark_approved(req_id)

Performance Notes:
    - Document validation is async and can be slow for large files
    - Consider using queue for batch processing
    - Cache validation results for 1 hour

Related Modules:
    prep.regulatory.loader - Load regulatory requirements
    prep.regulatory.parser - Parse regulatory documents
"""

from __future__ import annotations
# ... rest of module
```

#### Files to Update:
1. `/prep/regulatory/writer.py` - Document writer purpose and components
2. `/prep/compliance/food_safety_compliance_engine.py` - Compliance violations and pipeline
3. `/prep/compliance/data_validator.py` - Validation stages
4. `/prep/compliance/dol_reg_compliance_engine.py` - DOL requirements
5. `/prep/compliance/lse_impact_simulator.py` - Simulation logic
6. `/prep/compliance/gdpr_ccpa_core.py` - Privacy violations
7. `/prep/api/integrations.py` - Integration endpoints
8. `/prep/platform/schemas.py` - Pydantic model documentation

---

## PHASE 2: HIGH PRIORITY ISSUES (2-3 Weeks)

### Fix #4: Add Test Files for Critical APIs

**Status:** HIGH - 51.9% test coverage gap  
**Priority Files:**

#### 1. Create tests/api/test_kitchens.py (prep/api/kitchens.py: 581 lines)
```python
# tests/api/test_kitchens.py
import pytest
from uuid import uuid4
from prep.api.kitchens import router
from prep.models.orm import Kitchen, User
from fastapi.testclient import TestClient

class TestGetKitchen:
    @pytest.mark.asyncio
    async def test_get_kitchen_success(self, async_client, session):
        """Test retrieving a kitchen successfully."""
        # Setup
        user = await create_test_user(session)
        kitchen = await create_test_kitchen(session, host_id=user.id)
        
        # Execute
        response = await async_client.get(f"/api/kitchens/{kitchen.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == str(kitchen.id)
        assert data['host_id'] == str(user.id)
    
    @pytest.mark.asyncio
    async def test_kitchen_not_found(self, async_client):
        """Test 404 when kitchen doesn't exist."""
        response = await async_client.get(f"/api/kitchens/{uuid4()}")
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_kitchen_authorization(self, async_client, session):
        """Test kitchen is only visible to authorized users."""
        # Setup
        owner = await create_test_user(session)
        other_user = await create_test_user(session)
        kitchen = await create_test_kitchen(session, host_id=owner.id, published=False)
        
        # Execute as non-owner
        async_client.headers['Authorization'] = f'Bearer {other_user.token}'
        response = await async_client.get(f"/api/kitchens/{kitchen.id}")
        
        # Assert
        assert response.status_code == 403

class TestCreateKitchen:
    @pytest.mark.asyncio
    async def test_create_kitchen_success(self, async_client, session, authenticated_user):
        """Test creating a kitchen."""
        payload = {
            'name': 'Test Kitchen',
            'city': 'San Francisco',
            'postal_code': '94102',
            'address': '123 Main St',
            'capacity': 50,
        }
        
        response = await async_client.post(
            '/api/kitchens',
            json=payload,
            headers={'Authorization': f'Bearer {authenticated_user.token}'}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data['name'] == 'Test Kitchen'
        
        # Verify in database
        kitchen = await session.get(Kitchen, data['id'])
        assert kitchen is not None

    @pytest.mark.asyncio
    async def test_create_kitchen_validation(self, async_client, authenticated_user):
        """Test validation on kitchen creation."""
        invalid_payload = {
            'name': '',  # Required
            'city': 'San Francisco',
        }
        
        response = await async_client.post(
            '/api/kitchens',
            json=invalid_payload,
            headers={'Authorization': f'Bearer {authenticated_user.token}'}
        )
        
        assert response.status_code == 422
```

#### 2. Create tests/compliance/test_city_compliance_engine.py
```python
# tests/compliance/test_city_compliance_engine.py
import pytest
from prep.compliance.city_compliance_engine import CityComplianceEngine
from prep.models.orm import Kitchen

class TestCityComplianceEngine:
    @pytest.fixture
    def engine(self, session):
        return CityComplianceEngine(session)
    
    @pytest.mark.asyncio
    async def test_validate_san_francisco_kitchen(self, engine, session):
        """Test San Francisco compliance validation."""
        kitchen = await create_test_kitchen(
            session,
            city='San Francisco',
            has_permits=['food_service_permit', 'dbi_license']
        )
        
        violations = await engine.validate(kitchen)
        
        assert len(violations) == 0
    
    @pytest.mark.asyncio
    async def test_detect_missing_permits(self, engine, session):
        """Test detection of missing permits."""
        kitchen = await create_test_kitchen(
            session,
            city='San Francisco',
            has_permits=[]  # Missing permits
        )
        
        violations = await engine.validate(kitchen)
        
        assert len(violations) > 0
        assert any(v.violation_type == 'MISSING_PERMIT' for v in violations)
```

**Test Coverage Target:**
- Unit tests: 80% on critical modules
- Integration tests: 60% on API routes
- Focus on: Error paths, validation, authorization

---

### Fix #5: Replace Excessive `Any` Types

**Status:** HIGH - Type safety impact  
**Files to Update:** 20+

#### Example: /prep/models/orm.py
```python
# BEFORE
def __init__(self, data: Any) -> None:
    self.violations = data.get('violations', [])
    self.metadata = data

# AFTER
from typing import TypedDict

class InspectionDataDict(TypedDict):
    violations: list[str]
    score: float
    inspector_id: str
    timestamp: str

def __init__(self, data: InspectionDataDict) -> None:
    self.violations = data['violations']
    self.metadata = InspectionDataDict(**data)
```

**Tools:**
```bash
# Find all `Any` usages
grep -r "Any" prep/ --include="*.py" | wc -l

# Auto-fix with type narrowing
mypy --strict prep/models/ --show-column-numbers
```

---

## PHASE 3: MEDIUM PRIORITY ISSUES (2-3 Weeks)

### Fix #6: Add Missing Database Indexes

**Status:** MEDIUM - Performance optimization  
**Time Estimate:** 4 hours

```python
# prep/alembic/versions/add_missing_indexes.py
"""Add missing database indexes for query performance."""

from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    # Kitchen table indexes
    op.create_index('ix_kitchen_host_id', 'kitchen', ['host_id'])
    op.create_index('ix_kitchen_city', 'kitchen', ['city'])
    op.create_index('ix_kitchen_created_at', 'kitchen', ['created_at'])
    op.create_index('ix_kitchen_location', 'kitchen', ['city', 'postal_code'])
    
    # Booking table indexes
    op.create_index('ix_booking_kitchen_id', 'booking', ['kitchen_id'])
    op.create_index('ix_booking_user_id', 'booking', ['user_id'])
    op.create_index('ix_booking_status', 'booking', ['status'])
    op.create_index('ix_booking_created_at', 'booking', ['created_at'])
    
    # Review table indexes
    op.create_index('ix_review_kitchen_id', 'review', ['kitchen_id'])
    op.create_index('ix_review_user_id', 'review', ['user_id'])
    op.create_index('ix_review_created_at', 'review', ['created_at'])

def downgrade() -> None:
    op.drop_index('ix_review_created_at')
    op.drop_index('ix_review_user_id')
    # ... etc
```

**Apply Migration:**
```bash
alembic upgrade head
```

---

### Fix #7: Extract Compliance Services

**Time Estimate:** 5-6 days

Create organized compliance module structure:
```
prep/compliance/
├── __init__.py
├── base_engine.py           # Base class
├── food_safety/
│   ├── __init__.py
│   ├── engine.py           # Food safety logic
│   └── validators.py       # Food safety validators
├── city_compliance/
│   ├── __init__.py
│   ├── engine.py           # City compliance
│   └── validators.py
├── aml_kyc/
│   ├── __init__.py
│   └── engine.py           # AML/KYC checks
└── privacy/
    ├── __init__.py
    ├── gdpr.py             # GDPR compliance
    └── ccpa.py             # CCPA compliance
```

---

## PHASE 4: CLEANUP (1 Week)

### Fix #8: Remove Duplicate Imports

Use IDE's import cleanup:
```bash
# VS Code
python -m isort prep/ etl/ jobs/

# Or manually clean files:
# /etl/crawler.py
# /prep/api/middleware/idempotency.py
# etc.
```

### Fix #9: Configure Linting & Type Checking

```bash
# Run linters
ruff check . --fix
black . --line-length=100
mypy --strict prep/ --exclude tests/

# Run tests
pytest --cov=prep --cov-report=html --cov-report=term-missing
```

---

## AUTOMATION & CI/CD

### GitHub Actions Workflow

```yaml
# .github/workflows/code-quality.yml
name: Code Quality

on: [pull_request, push]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install ruff black mypy pytest-cov
      
      - name: Lint with Ruff
        run: ruff check . --select=E,F,W
      
      - name: Format check with Black
        run: black --check .
      
      - name: Type check with mypy
        run: mypy --strict prep/ --exclude tests/
      
      - name: Run tests with coverage
        run: |
          pytest --cov=prep --cov-report=xml --cov-report=term-missing
          coverage report --fail-under=70
```

---

## ROLLOUT CHECKLIST

### Week 1: Critical Fixes
- [ ] Add error boundaries to React components
- [ ] Test error boundary behavior
- [ ] Deploy to staging
- [ ] Test error scenarios

### Week 2: Refactoring
- [ ] Split analytics service
- [ ] Add module docstrings (8 files)
- [ ] Run full test suite
- [ ] Code review

### Week 3-4: Testing
- [ ] Create test_kitchens.py
- [ ] Create test_compliance_engines.py (3 files)
- [ ] Achieve 70% coverage on critical modules
- [ ] Add hook tests (React)

### Week 5-6: Performance & Cleanup
- [ ] Add database indexes
- [ ] Implement eager loading
- [ ] Replace `Any` types (20+ files)
- [ ] Remove duplicate imports
- [ ] Final linting pass

---

## Success Metrics

| Metric | Current | Target | Deadline |
|--------|---------|--------|----------|
| Test Coverage | 48.1% | 70% | Week 4 |
| Documentation Coverage | 45% | 90% | Week 2 |
| Duplicate Imports | 10 files | 0 | Week 6 |
| `Any` Type Usage | 50+ | <10 | Week 5 |
| Missing Error Boundaries | 4 | 0 | Week 1 |
| Long Files (>500 lines) | 18 | <5 | Week 3 |

---

## Commands to Run

```bash
# Run analysis
pytest --cov=prep --cov-report=html
mypy prep/ --strict

# Apply formatting
black prep/ tests/ apps/ --line-length=100
ruff check . --fix
isort prep/ tests/ apps/

# Generate reports
coverage html
pdoc --html --output-dir=docs prep/
```

