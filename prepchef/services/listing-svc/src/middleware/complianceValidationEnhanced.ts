import { PythonShell } from 'python-shell';
import { fetch } from 'undici';

export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info';

export interface ComplianceViolation {
  rule_id: string;
  rule_name: string;
  message: string;
  severity: Severity;
}

export interface SafetyBadge {
  badge_level: string;
  score: number;
  last_verified?: string;
  highlights: string[];
  concerns: string[];
}

export interface ComplianceEngineSuccess {
  status?: 'ok';
  overall_compliance_score: number;
  violations_found: ComplianceViolation[];
  can_accept_bookings: boolean;
  safety_badge?: SafetyBadge;
}

export interface ComplianceEngineFailure {
  status: 'error';
  error: string;
  details?: unknown;
}

export type ComplianceEngineResult = ComplianceEngineSuccess | ComplianceEngineFailure;

export interface LicenseRecord {
  license_number?: string | null;
  license_type?: string | null;
  issue_date?: Date | null;
  expiration_date?: Date | null;
  county_fips?: string | null;
  status?: string | null;
}

export interface InspectionRecord {
  inspection_date: Date;
  overall_score?: number | null;
  violations?: unknown;
  establishment_closed?: boolean | null;
  source?: string | null;
}

export interface CertificationRecord {
  type?: string | null;
  status?: string | null;
  expiration_date?: Date | null;
}

export interface EquipmentRecord {
  type?: string | null;
  commercial_grade?: boolean | null;
  nsf_certified?: boolean | null;
  photo_url?: string | null;
}

export interface InsuranceRecord {
  policy_number?: string | null;
  provider?: string | null;
  expiration_date?: Date | null;
}

export interface PestControlRecord {
  service_date: Date;
  provider?: string | null;
}

export interface CleaningLogRecord {
  date: Date;
  tasks_completed?: string[] | null;
}

export interface KitchenRecord {
  id: string;
  host_id: string;
  compliance_status?: string | null;
  health_score?: number | null;
  last_compliance_check?: Date | null;
  license_number?: string | null;
  county_fips?: string | null;
  license?: LicenseRecord | null;
  inspections?: InspectionRecord[] | null;
  certifications?: CertificationRecord[] | null;
  equipment?: EquipmentRecord[] | null;
  insurance?: InsuranceRecord | null;
  photos?: Array<{ url?: string | null }> | null;
  pest_control_records?: PestControlRecord[] | null;
  cleaning_logs?: CleaningLogRecord[] | null;
}

export interface ComplianceLogEntry {
  kitchen_id: string;
  check_date: Date;
  score: number;
  violations: ComplianceViolation[];
  source?: string;
  raw_report?: ComplianceEngineSuccess;
}

export interface ComplianceDatabase {
  kitchens: {
    findUnique(args: unknown): Promise<KitchenRecord | null>;
    update(args: unknown): Promise<void>;
    findMany(args: unknown): Promise<KitchenRecord[]>;
  };
  kitchen_compliance_log: {
    create(args: unknown): Promise<void>;
    findFirst(args: unknown): Promise<ComplianceLogEntry | null>;
  };
  inspections: {
    upsert(args: unknown): Promise<void>;
  };
}

export interface RequestUser {
  id: string;
  role: string;
}

export interface ComplianceMiddlewareDeps {
  db: ComplianceDatabase;
  pythonScriptPath?: string;
  pythonPath?: string;
  logger?: Pick<Console, 'log' | 'error' | 'warn'>;
}

export interface MiddlewareSuccess<T> {
  ok: true;
  statusCode: number;
  data: T;
}

export interface MiddlewareFailure {
  ok: false;
  statusCode: number;
  error: string;
  type?: string;
  details?: unknown;
}

export type MiddlewareResult<T> = MiddlewareSuccess<T> | MiddlewareFailure;

export interface BookingComplianceData {
  health_score: number;
  verified_at: Date;
}

export interface RefreshStats {
  updated: number;
  errors: number;
  total: number;
}

export class ComplianceError extends Error {
  constructor(
    message: string,
    public readonly type: string,
    public readonly details: unknown = undefined
  ) {
    super(message);
    this.name = 'ComplianceError';
  }
}

function toIsoString(value?: Date | string | null): string | undefined {
  if (!value) return undefined;
  if (value instanceof Date) return value.toISOString();
  return value;
}

function formatKitchenForCompliance(kitchen: KitchenRecord): Record<string, unknown> {
  return {
    license_info: kitchen.license
      ? {
          license_number: kitchen.license.license_number ?? undefined,
          license_type: kitchen.license.license_type ?? undefined,
          issue_date: toIsoString(kitchen.license.issue_date),
          expiration_date: toIsoString(kitchen.license.expiration_date),
          county_fips: kitchen.license.county_fips ?? kitchen.county_fips ?? undefined,
          status: kitchen.license.status ?? undefined,
        }
      : {},
    inspection_history:
      kitchen.inspections?.map(inspection => ({
        inspection_date: toIsoString(inspection.inspection_date) ?? undefined,
        overall_score: inspection.overall_score ?? undefined,
        violations: inspection.violations ?? [],
        establishment_closed: inspection.establishment_closed ?? false,
      })) ?? [],
    certifications:
      kitchen.certifications?.map(certification => ({
        type: certification.type ?? undefined,
        status: certification.status ?? undefined,
        expiration_date: toIsoString(certification.expiration_date),
      })) ?? [],
    equipment:
      kitchen.equipment?.map(equipment => ({
        type: equipment.type ?? undefined,
        commercial_grade: equipment.commercial_grade ?? undefined,
        nsf_certified: equipment.nsf_certified ?? undefined,
        photo_url: equipment.photo_url ?? undefined,
      })) ?? [],
    insurance: kitchen.insurance
      ? {
          policy_number: kitchen.insurance.policy_number ?? undefined,
          provider: kitchen.insurance.provider ?? undefined,
          expiration_date: toIsoString(kitchen.insurance.expiration_date),
        }
      : {},
    photos: kitchen.photos?.map(photo => ({ url: photo.url ?? undefined })) ?? [],
    pest_control_records:
      kitchen.pest_control_records?.map(record => ({
        service_date: toIsoString(record.service_date) ?? undefined,
        provider: record.provider ?? undefined,
      })) ?? [],
    cleaning_logs:
      kitchen.cleaning_logs?.map(log => ({
        date: toIsoString(log.date) ?? undefined,
        tasks_completed: log.tasks_completed ?? [],
      })) ?? [],
    license_number: kitchen.license_number ?? kitchen.license?.license_number ?? undefined,
    county_fips: kitchen.county_fips ?? kitchen.license?.county_fips ?? undefined,
  };
}

export async function runComplianceEngine(
  kitchenData: Record<string, unknown>,
  deps: ComplianceMiddlewareDeps
): Promise<ComplianceEngineResult> {
  const options = {
    mode: 'text' as const,
    pythonPath: deps.pythonPath ?? process.env.PYTHON_PATH ?? 'python3',
    pythonOptions: ['-u'],
    scriptPath: deps.pythonScriptPath ?? './prep/compliance',
    args: [JSON.stringify(kitchenData)],
    timeout: 30_000,
  };

  try {
    const output = await PythonShell.run('run_compliance_check.py', options);
    if (output.length === 0) {
      return { status: 'error', error: 'No output from compliance engine' };
    }

    const payload = output.join('');
    try {
      return JSON.parse(payload) as ComplianceEngineResult;
    } catch (parseError) {
      const message = parseError instanceof Error ? parseError.message : 'Invalid JSON output';
      deps.logger?.error?.(`Failed to parse compliance engine output: ${message}`);
      return { status: 'error', error: 'Invalid JSON output from compliance engine', details: message };
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    deps.logger?.error?.(`Compliance engine execution failed: ${message}`);
    return { status: 'error', error: message };
  }
}

function mapEngineFailure(error: ComplianceEngineFailure): MiddlewareFailure {
  return {
    ok: false,
    statusCode: 400,
    error: 'Compliance engine failed',
    type: 'ENGINE_ERROR',
    details: error,
  };
}

export async function validateKitchenCompliance(
  kitchenId: string,
  user: RequestUser,
  deps: ComplianceMiddlewareDeps
): Promise<MiddlewareResult<{ complianceResult: ComplianceEngineSuccess; canAcceptBookings: boolean }>> {
  const start = Date.now();
  try {
    const kitchen = await deps.db.kitchens.findUnique({
      where: { id: kitchenId },
      include: {
        license: true,
        inspections: { orderBy: { inspection_date: 'desc' }, take: 5 },
        certifications: true,
        equipment: true,
        insurance: true,
        photos: true,
        pest_control_records: true,
        cleaning_logs: true,
      },
    });

    if (!kitchen) {
      return { ok: false, statusCode: 404, error: 'Kitchen not found', type: 'NOT_FOUND' };
    }

    if (kitchen.host_id !== user.id && user.role !== 'admin') {
      return { ok: false, statusCode: 403, error: 'Unauthorized access', type: 'UNAUTHORIZED' };
    }

    const complianceData = formatKitchenForCompliance(kitchen);
    const result = await runComplianceEngine(complianceData, deps);

    if ('status' in result && result.status === 'error') {
      return mapEngineFailure(result);
    }

    await deps.db.kitchen_compliance_log.create({
      data: {
        kitchen_id: kitchenId,
        check_date: new Date(),
        score: Math.round(result.overall_compliance_score * 100),
        violations: result.violations_found,
        source: 'prepchef_engine',
        raw_report: result,
      },
    });

    const canAcceptBookings = result.can_accept_bookings;

    await deps.db.kitchens.update({
      where: { id: kitchenId },
      data: {
        compliance_status: canAcceptBookings ? 'verified' : 'flagged',
        health_score: Math.round(result.overall_compliance_score * 100),
        last_compliance_check: new Date(),
      },
    });

    deps.logger?.log?.(
      `Compliance check for kitchen ${kitchenId} completed in ${Date.now() - start}ms`
    );

    return {
      ok: true,
      statusCode: 200,
      data: { complianceResult: result, canAcceptBookings },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    deps.logger?.error?.('Compliance validation error', error);
    return {
      ok: false,
      statusCode: 500,
      error: 'Compliance validation failed',
      type: 'INTERNAL_ERROR',
      details: message,
    };
  }
}

export async function validateBookingCompliance(
  kitchenId: string,
  deps: ComplianceMiddlewareDeps
): Promise<MiddlewareResult<BookingComplianceData>> {
  try {
    const latestCompliance = await deps.db.kitchen_compliance_log.findFirst({
      where: { kitchen_id: kitchenId },
      orderBy: { check_date: 'desc' },
      select: {
        score: true,
        check_date: true,
        violations: true,
      },
    });

    if (!latestCompliance) {
      return {
        ok: false,
        statusCode: 400,
        error: 'Kitchen compliance not verified',
        type: 'MISSING_COMPLIANCE',
      };
    }

    const daysSinceCheck = Math.floor(
      (Date.now() - latestCompliance.check_date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (daysSinceCheck > 30) {
      return {
        ok: false,
        statusCode: 400,
        error: 'Compliance verification expired',
        type: 'STALE_COMPLIANCE',
      };
    }

    const criticalViolations = latestCompliance.violations.filter(
      violation => violation.severity === 'critical'
    );

    if (criticalViolations.length > 0) {
      return {
        ok: false,
        statusCode: 403,
        error: 'Kitchen not available for booking',
        type: 'CRITICAL_VIOLATIONS',
        details: criticalViolations,
      };
    }

    const kitchen = await deps.db.kitchens.findUnique({
      where: { id: kitchenId },
      select: { compliance_status: true },
    });

    if (kitchen?.compliance_status === 'suspended') {
      return {
        ok: false,
        statusCode: 403,
        error: 'Kitchen suspended',
        type: 'SUSPENDED',
      };
    }

    return {
      ok: true,
      statusCode: 200,
      data: {
        health_score: latestCompliance.score,
        verified_at: latestCompliance.check_date,
      },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    deps.logger?.error?.('Booking compliance validation error', error);
    return {
      ok: false,
      statusCode: 500,
      error: 'Failed to validate booking compliance',
      type: 'INTERNAL_ERROR',
      details: message,
    };
  }
}

export async function refreshCountyComplianceData(
  deps: ComplianceMiddlewareDeps
): Promise<RefreshStats> {
  const start = Date.now();
  const stats: RefreshStats = { updated: 0, errors: 0, total: 0 };

  try {
    deps.logger?.log?.('Starting county compliance data refresh...');
    const kitchens = await deps.db.kitchens.findMany({
      where: {
        license_number: { not: null },
        county_fips: { not: null },
        compliance_status: { in: ['verified', 'pending'] },
      },
      include: { license: true },
    });

    stats.total = kitchens.length;
    deps.logger?.log?.(`Refreshing compliance for ${kitchens.length} kitchens...`);

    const batchSize = 10;
    for (let i = 0; i < kitchens.length; i += batchSize) {
      const batch = kitchens.slice(i, i + batchSize);
      const results = await Promise.allSettled(
        batch.map(kitchen => processKitchenCompliance(kitchen, deps))
      );

      for (const result of results) {
        if (result.status === 'fulfilled') {
          stats.updated += result.value.updated ? 1 : 0;
          stats.errors += result.value.errors ? 1 : 0;
        } else {
          stats.errors += 1;
          deps.logger?.error?.('Batch processing error', result.reason);
        }
      }
    }

    deps.logger?.log?.(
      `Compliance refresh complete in ${Date.now() - start}ms: ${JSON.stringify(stats)}`
    );
    return stats;
  } catch (error) {
    deps.logger?.error?.('County compliance refresh failed', error);
    return { ...stats, errors: stats.total };
  }
}

export interface ProcessResult {
  updated: boolean;
  errors: boolean;
}

async function processKitchenCompliance(
  kitchen: KitchenRecord,
  deps: ComplianceMiddlewareDeps
): Promise<ProcessResult> {
  try {
    const countyData = await fetchCountyInspectionData(
      kitchen.license_number ?? kitchen.license?.license_number ?? '',
      kitchen.county_fips ?? kitchen.license?.county_fips ?? '',
      deps
    );

    if (countyData?.latest_inspection) {
      await deps.db.inspections.upsert({
        where: {
          kitchen_id_inspection_date: {
            kitchen_id: kitchen.id,
            inspection_date: new Date(countyData.latest_inspection.inspection_date),
          },
        },
        update: {
          overall_score: countyData.latest_inspection.overall_score,
          violations: countyData.latest_inspection.violations,
          establishment_closed: countyData.latest_inspection.establishment_closed,
        },
        create: {
          kitchen_id: kitchen.id,
          inspection_date: new Date(countyData.latest_inspection.inspection_date),
          overall_score: countyData.latest_inspection.overall_score,
          violations: countyData.latest_inspection.violations,
          establishment_closed: countyData.latest_inspection.establishment_closed,
          source: 'county_api',
        },
      });

      const kitchenData = await deps.db.kitchens.findUnique({
        where: { id: kitchen.id },
        include: {
          inspections: { orderBy: { inspection_date: 'desc' }, take: 5 },
          certifications: true,
          equipment: true,
          insurance: true,
          license: true,
        },
      });

      if (kitchenData) {
        const complianceData = formatKitchenForCompliance(kitchenData);
        const result = await runComplianceEngine(complianceData, deps);
        if ('status' in result && result.status === 'error') {
          throw new Error(result.error);
        }

        await deps.db.kitchens.update({
          where: { id: kitchen.id },
          data: {
            health_score: Math.round(result.overall_compliance_score * 100),
            last_compliance_check: new Date(),
            compliance_status: result.can_accept_bookings ? 'verified' : 'flagged',
          },
        });

        return { updated: true, errors: false };
      }
    }

    return { updated: false, errors: false };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    deps.logger?.error?.(`Error processing kitchen ${kitchen.id}: ${message}`);
    return { updated: false, errors: true };
  }
}

export interface CountyInspectionResponse {
  latest_inspection?: {
    inspection_date: string;
    overall_score: number;
    violations: unknown;
    establishment_closed: boolean;
  };
  license_status?: string;
}

export async function fetchCountyInspectionData(
  licenseNumber: string,
  countyFips: string,
  deps: ComplianceMiddlewareDeps
): Promise<CountyInspectionResponse | null> {
  if (!licenseNumber || !countyFips) {
    return null;
  }

  const apiUrl = process.env.DATA_INTELLIGENCE_API_URL;
  const apiKey = process.env.DATA_INTELLIGENCE_API_KEY;

  if (!apiUrl || !apiKey) {
    deps.logger?.warn?.('Data Intelligence API not configured - skipping county data fetch');
    return null;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  try {
    const response = await fetch(`${apiUrl}/v1/inspections/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${apiKey}`,
      },
      body: JSON.stringify({ license_number: licenseNumber, county_fips: countyFips }),
      signal: controller.signal,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API returned ${response.status}: ${errorText}`);
    }

    return (await response.json()) as CountyInspectionResponse;
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    deps.logger?.error?.('County API fetch error', message);
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getKitchenSafetyBadge(
  kitchenId: string,
  deps: ComplianceMiddlewareDeps
): Promise<MiddlewareResult<SafetyBadge & { can_accept_bookings: boolean }>> {
  try {
    const latestCompliance = await deps.db.kitchen_compliance_log.findFirst({
      where: { kitchen_id: kitchenId },
      orderBy: { check_date: 'desc' },
    });

    if (!latestCompliance) {
      return { ok: false, statusCode: 404, error: 'No compliance data available' };
    }

    const kitchen = await deps.db.kitchens.findUnique({
      where: { id: kitchenId },
      include: {
        inspections: { orderBy: { inspection_date: 'desc' }, take: 1 },
        certifications: true,
      },
    });

    if (!kitchen) {
      return { ok: false, statusCode: 404, error: 'Kitchen not found' };
    }

    let badge: SafetyBadge;

    if (latestCompliance.raw_report?.safety_badge) {
      badge = latestCompliance.raw_report.safety_badge;
    } else {
      const score = latestCompliance.score;
      let badge_level: SafetyBadge['badge_level'];
      if (score >= 95) badge_level = 'gold';
      else if (score >= 85) badge_level = 'silver';
      else if (score >= 70) badge_level = 'bronze';
      else badge_level = 'needs_improvement';

      const highlights: string[] = [];
      const latestInspection = kitchen.inspections?.[0];
      if ((latestInspection?.overall_score ?? 0) >= 90) {
        highlights.push(`Excellent health score: ${latestInspection?.overall_score}/100`);
      }

      const hasServSafe = kitchen.certifications?.some(cert =>
        (cert.type ?? '').toLowerCase().includes('servsafe') && cert.status === 'active'
      );
      if (hasServSafe) {
        highlights.push('ServSafe certified staff');
      }

      const criticalViolations = latestCompliance.violations.filter(
        violation => violation.severity === 'critical'
      );
      if (criticalViolations.length === 0) {
        highlights.push('No critical violations');
      }

      const concerns = latestCompliance.violations
        .filter(violation => violation.severity === 'critical' || violation.severity === 'high')
        .map(violation => violation.message);

      badge = {
        badge_level,
        score,
        last_verified: latestCompliance.check_date.toISOString(),
        highlights,
        concerns,
      };
    }

    return {
      ok: true,
      statusCode: 200,
      data: { ...badge, can_accept_bookings: kitchen.compliance_status === 'verified' },
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    deps.logger?.error?.('Error generating safety badge', message);
    return {
      ok: false,
      statusCode: 500,
      error: 'Failed to generate safety badge',
      type: 'INTERNAL_ERROR',
      details: message,
    };
  }
}
