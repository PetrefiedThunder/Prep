# COMPREHENSIVE CONFIGURATION AUDIT REPORT

**Date:** 2025-11-11
**Scope:** Complete codebase scan of all configuration files
**Total Issues Found:** 40+

---

## EXECUTIVE SUMMARY

Multiple critical and high-severity configuration issues have been identified across the monorepo that will prevent successful builds, compromise security, and introduce runtime errors. The most critical issue is invalid JSON syntax in 8 service `tsconfig.json` files that will cause immediate build failures.

---

## CRITICAL ISSUES (Must Fix Immediately)

### 1. Invalid JSON Syntax in Service TypeScript Configurations

**Severity:** CRITICAL  
**Impact:** Build failures - prevents TypeScript compilation

**Affected Files:**
- `/home/user/Prep/prepchef/services/listing-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/compliance-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/auth-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/audit-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/booking-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/payments-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/pricing-svc/tsconfig.json`
- `/home/user/Prep/prepchef/services/admin-svc/tsconfig.json`

**Issue Description:**
All 8 files have duplicate `compilerOptions` sections and missing commas between properties. Example from listing-svc/tsconfig.json:

```json
{
  "extends": "@prep/tsconfig/tsconfig.base.json",
  "compilerOptions": { "rootDir": "src", "outDir": "dist" },
  "include": ["src/**/*.ts"],
  "exclude": ["src/tests/**"]
  // MISSING COMMA HERE ^^^
  "compilerOptions": {  // DUPLICATE SECTION
    "rootDir": "src",
    "outDir": "dist"
  },
  // ... rest of properties
}
```

**Error Message:** `Expected ',' or '}' after property value in JSON at position 175`

**Fix:** Remove the inline `compilerOptions` on line 3 and the comma, keep only the object version below with proper JSON structure.

---

## HIGH SEVERITY ISSUES

### 2. Hardcoded Credentials in Environment Examples

**Severity:** HIGH  
**Type:** Security - Credentials Exposure
**Impact:** Risk of credential leakage if examples are committed with real values

**Affected File:** `/home/user/Prep/.env.example`

**Issues:**
- Line 7: `MINIO_SECRET_KEY=prep` - Uses default/hardcoded value (should use placeholder)
- Default credentials in development environment

**Example:**
```
MINIO_ACCESS_KEY=prep
MINIO_SECRET_KEY=prep
```

**Recommendation:** Replace all actual default credentials with placeholders:
```
MINIO_ACCESS_KEY=<your-minio-access-key>
MINIO_SECRET_KEY=<your-minio-secret-key>
```

### 3. Incomplete TypeScript Strict Mode Configuration

**Severity:** HIGH  
**Type:** Code Quality
**Impact:** Type safety gaps, runtime errors possible

**Affected Files:**
- `/home/user/Prep/harborhomes/tsconfig.json`
- `/home/user/Prep/apps/harborhomes/tsconfig.base.json`
- `/home/user/Prep/prepchef/packages/tsconfig/tsconfig.base.json`
- `/home/user/Prep/services/prep-connect/tsconfig.json`

**Issues Identified:**
When `strict: true` is set, the following should also be explicitly enabled but are missing:
- `noUnusedLocals`: Missing (should be `true`)
- `noUnusedParameters`: Missing (should be `true`)
- `exactOptionalPropertyTypes`: Missing (should be `true` for strict mode)

**Current State:**
```json
{
  "compilerOptions": {
    "strict": true,
    // BUT these are missing:
    "noUnusedLocals": false,  // Or not set at all
    "noUnusedParameters": false,
    "exactOptionalPropertyTypes": false
  }
}
```

**Impact:** Unused variables and parameters won't cause compilation errors, allowing dead code to accumulate.

**Fix:** Add these options explicitly:
```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "exactOptionalPropertyTypes": true
  }
}
```

### 4. Missing Security Headers in Next.js Configuration

**Severity:** HIGH  
**Type:** Security
**Impact:** Missing security headers on responses

**Affected File:** `/home/user/Prep/harborhomes/next.config.mjs`

**Issue:** No security headers configured, while `/home/user/Prep/apps/harborhomes/next.config.mjs` does have them.

**Current State (Missing):**
```javascript
// No headers() function
// No security headers
```

**Comparison:** `/home/user/Prep/apps/harborhomes/next.config.mjs` has:
```javascript
async headers() {
  return [{
    source: '/(.*)',
    headers: [{
      key: 'Permissions-Policy',
      value: 'interest-cohort=()'
    }]
  }];
}
```

**Recommendation:** Add comprehensive security headers:
```javascript
async headers() {
  return [{
    source: '/(.*)',
    headers: [
      { key: 'X-Content-Type-Options', value: 'nosniff' },
      { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
      { key: 'X-XSS-Protection', value: '1; mode=block' },
      { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
      { key: 'Permissions-Policy', value: 'interest-cohort=()' }
    ]
  }];
}
```

---

## MEDIUM SEVERITY ISSUES

### 5. Dependency Version Conflicts Across Monorepo

**Severity:** MEDIUM  
**Type:** Version Management
**Impact:** Unpredictable behavior, potential compatibility issues

**Conflicts Identified:**

| Package | Versions | Locations |
|---------|----------|-----------|
| `typescript` | `5.4.5` (fixed), `^5.6.2` (6 places), `^5.6.3` (1 place), `^5.4.5` (1 place) | Multiple |
| `lucide-react` | `0.372.0` vs `^0.447.0` | harborhomes vs prepchef |
| `@fastify/jwt` | `^7.0.1` vs `^7.2.1` | common vs services |
| `@types/node` | `20.12.8`, `^20.14.10`, `^20.12.7` | Multiple |
| `zod` | `3.23.8` vs `^3.23.8` | prepchef vs services |

**Recommendation:** Implement strict version pinning strategy:
```json
{
  "name": "prepchef",
  "version": "0.1.0",
  "overrides": {
    "typescript": "5.6.3",
    "zod": "3.23.8",
    "@fastify/jwt": "7.2.1",
    "lucide-react": "0.447.0"
  }
}
```

### 6. Missing Lint Scripts and Stub Implementations

**Severity:** MEDIUM  
**Type:** Code Quality
**Impact:** Linting not enforced, code quality issues not caught

**Affected Files:**
- `/home/user/Prep/prepchef/services/*/package.json` (All services)

**Issue:**
```json
{
  "scripts": {
    "lint": "echo 'lint stub'"  // Not actually linting
  }
}
```

**Example Affected Services:**
- listing-svc
- compliance-svc
- auth-svc
- audit-svc
- booking-svc
- payments-svc
- access-svc
- pricing-svc
- availability-svc
- notif-svc
- admin-svc

**Fix:** Replace with actual linting:
```json
{
  "scripts": {
    "lint": "eslint src/**/*.ts",
    "lint:fix": "eslint src/**/*.ts --fix",
    "typecheck": "tsc --noEmit",
    "test": "node --test --loader tsx src/tests/**/*.test.ts"
  }
}
```

### 7. Inconsistent TypeScript Strict Mode Across Root Configs

**Severity:** MEDIUM  
**Type:** Configuration Consistency
**Impact:** Inconsistent type-checking behavior

**Detailed Analysis:**

| File | strict | noImplicitAny | noUnusedLocals | noImplicitReturns |
|------|--------|---------------|-----------------|------------------|
| `/home/user/Prep/tsconfig.json` | ✓ | ✓ | ✗ | ✓ |
| `/home/user/Prep/tsconfig.node.json` | ✗ | ✗ | ✗ | ✗ |
| `/home/user/Prep/harborhomes/tsconfig.json` | ✓ | ✗ | ✗ | ✗ |

**Issue:** `tsconfig.node.json` has NO strict mode enabled while root tsconfig has full strict mode. This creates type-safety gaps.

---

## LOW SEVERITY ISSUES

### 8. Missing Test Configuration Settings

**Severity:** LOW  
**Type:** Testing
**Impact:** Tests may not run optimally

**Affected File:** `/home/user/Prep/harborhomes/playwright.config.ts`

**Issue:** Missing critical test configuration:
```javascript
export default defineConfig({
  testDir: "./e2e",
  reporter: "list",  // Minimal reporter
  // MISSING:
  // - timeout settings
  // - retries
  // - parallelization
  // - test filtering patterns
  use: {
    baseURL: "http://localhost:3000",
    headless: true
    // Missing: screenshot on failure, trace collection
  }
});
```

**Recommendation:** Add comprehensive test config:
```javascript
export default defineConfig({
  testDir: "./e2e",
  timeout: 30000,
  expect: { timeout: 5000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['html'], ['list']],
  use: {
    baseURL: process.env.PLAYWRIGHT_TEST_BASE_URL || "http://localhost:3000",
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  }
});
```

### 9. Railway.json Configuration - Incomplete Settings

**Severity:** LOW  
**Type:** Deployment
**Impact:** Deployment may not work as expected

**File:** `/home/user/Prep/railway.json`

**Current Config:**
```json
{
  "build": {
    "builder": "NIXPACKS",
    "nixpacksVersion": "latest"
  },
  "deploy": {
    "startCommand": "uvicorn prep.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300
  }
}
```

**Issues:**
- `nixpacksVersion: "latest"` - Using "latest" is not reproducible
- No environment variable configurations
- No scale/resource definitions
- Missing pre-deploy/post-deploy hooks

**Recommendation:**
```json
{
  "build": {
    "builder": "NIXPACKS",
    "nixpacksVersion": "0.42.0"
  },
  "deploy": {
    "startCommand": "uvicorn prep.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "healthcheckInterval": 10,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  },
  "env": {
    "NODE_ENV": {
      "description": "Node environment",
      "value": "production"
    }
  }
}
```

### 10. Missing ESLint Configuration in Service Packages

**Severity:** LOW  
**Type:** Code Quality
**Impact:** No lint enforcement in services

**Affected Services:** All services under `/home/user/Prep/prepchef/services/*/`

**Issue:** No `.eslintrc` files found in service directories (checked listing-svc, auth-svc, etc.)

**Note:** Root ESLint config exists at `/home/user/Prep/eslint.config.js` but services appear to have stub lint commands.

**Recommendation:** Create service-specific `.eslintrc.json` or extend root config.

---

## DATA TYPE AND STRUCTURE ISSUES

### 11. package.json Version Inconsistencies

**Severity:** MEDIUM  
**Type:** Configuration
**Impact:** Confusing versioning strategy

**Issues:**

1. **Version Zero Pattern (Not for production):**
   - `harborhomes`: `0.1.0` (suggests beta/incomplete)
   - `prep-connect`: `0.1.0`
   - `prepchef`: `0.1.0`
   
   **Issue:** Version 0.x indicates pre-release but no clear upgrade path.

2. **Service vs Package Versions:**
   - All services: `1.0.0` (production-ready)
   - Packages: `1.0.0`
   - Root workspace: `0.1.0`

3. **Missing version metadata:**
   - No `engines` field in most packages (except prepchef root)
   - No `repository` field in package.json files
   - No `license` field specified

**Recommendation:** Standardize on semantic versioning with clear intent.

---

## SECURITY CONCERNS

### 12. Default Credentials in Docker/Local Development

**Severity:** MEDIUM  
**Type:** Security
**Impact:** Risk of credential leakage

**File:** `/home/user/Prep/.env.example`

**Hardcoded Defaults:**
```
MINIO_ACCESS_KEY=prep
MINIO_SECRET_KEY=prep
KMS_MASTER_KEY_HEX=0000000000000000000000000000000000000000000000000000000000000000
```

**Risks:**
- Easy to accidentally commit actual environment files
- Default credentials are well-known
- KMS master key is all zeros (obviously test value)

**Mitigation:**
- Use truly random placeholder values
- Add `.env` to `.gitignore` (verify)
- Add pre-commit hooks to prevent `.env` commits
- Consider using `.env.vault` or similar encrypted solution

### 13. Missing Environment Variable Validation

**Severity:** MEDIUM  
**Type:** Configuration Management
**Impact:** Runtime errors if required env vars are missing

**Affected Config:** `/home/user/Prep/prepchef/.env.example`

**Missing Validation Schema:**
- No documented required vs optional variables
- No type specifications
- No default value documentation
- No validation during startup

**Recommendation:** Create `env.schema.ts` or similar:
```typescript
import { z } from 'zod';

export const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  REDIS_URL: z.string().url(),
  JWT_SECRET: z.string().min(32),
  NODE_ENV: z.enum(['development', 'production', 'test']),
  // ... etc
});

export const env = envSchema.parse(process.env);
```

### 14. Next.js Public Keys Exposed in Config

**Severity:** LOW  
**Type:** Security
**Impact:** Exposure of public API keys (acceptable but should be documented)

**Affected Files:**
- `/home/user/Prep/harborhomes/.env.example`
- `/home/user/Prep/apps/harborhomes/.env.example`

**Keys Exposed:**
```
MAPBOX_TOKEN=mock
NEXT_PUBLIC_MAPBOX_TOKEN=mock
NEXT_PUBLIC_ANALYTICS_WRITE_KEY=mock
```

**Note:** These are intended to be public (NEXT_PUBLIC_ prefix) but ensure they:
- Have proper rate limiting in API calls
- Are scoped/restricted in the provider's console
- Have IP whitelisting where applicable

---

## PRISMA CONFIGURATION

### 15. Prisma Schema - PostGIS GEOGRAPHY Type Workaround

**Severity:** LOW  
**Type:** Database Design
**Impact:** Reduced geospatial query capabilities

**File:** `/home/user/Prep/prepchef/prisma/schema.prisma`

**Issue (Line 123-124):**
```prisma
// Note: PostGIS GEOGRAPHY type not directly supported, using String for now
location      String?   @db.Text
```

**Problem:**
- Lost geospatial indexing and querying capabilities
- Cannot use PostGIS functions (ST_Contains, ST_Distance, etc.)
- Location-based searches will be slower

**Recommendation:** Use proper geographic type:
```prisma
import postgis from "@prisma/prisma-postgis";

model Venue {
  // ... other fields
  location      postgis.geometry?  @map("location")
  
  @@index([location])
}
```

---

## RECOMMENDATIONS SUMMARY

### Immediate Actions (Critical - Do Today)
1. ✓ Fix all 8 service `tsconfig.json` files - invalid JSON syntax
2. ✓ Add missing security headers to harborhomes next.config.mjs
3. ✓ Replace hardcoded credentials in .env.example files

### Short-term Actions (High Priority - This Week)
4. ✓ Enable remaining TypeScript strict mode options
5. ✓ Implement actual lint scripts in services
6. ✓ Standardize dependency versions across monorepo

### Medium-term Actions (Should Complete)
7. ✓ Add comprehensive Playwright configuration
8. ✓ Fix Railway.json reproducibility settings
9. ✓ Create environment validation schema

### Long-term Improvements
10. ✓ Implement proper PostGIS support in Prisma
11. ✓ Standardize package versioning (1.x for stable)
12. ✓ Add ESLint configs to all service packages

---

## FILE MANIFEST

**Total Configuration Files Scanned:** 45+

**Categories:**
- JSON files: 20+
- TypeScript configs: 15+
- Package manager: 3
- Build tools: 4
- Deployment: 3
- Environment: 14
- Database: 1
- Linting: 2

**Status:**
- Valid JSON: 35
- Invalid JSON: 8 (all TypeScript service configs)
- Warnings: 12+

---

**Report Generated:** 2025-11-11  
**Scan Duration:** Comprehensive full codebase scan
**Recommendation:** Address CRITICAL issues before next deployment
