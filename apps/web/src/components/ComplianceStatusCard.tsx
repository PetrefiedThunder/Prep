import { useState } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  AlertCircle,
  AlertTriangle,
  Building2,
  CheckCircle2,
  ClipboardList,
  FileDown,
  ShieldCheck,
} from 'lucide-react';

function cn(...classes: Array<string | undefined | false | null>) {
  return classes.filter(Boolean).join(' ');
}

export type StatusTone = 'good' | 'warning' | 'critical';

const toneVisuals: Record<StatusTone, { badge: string; icon: typeof CheckCircle2; dot: string }> = {
  good: {
    badge: 'border-green-200 bg-green-50 text-green-700',
    icon: CheckCircle2,
    dot: 'bg-green-500',
  },
  warning: {
    badge: 'border-amber-200 bg-amber-50 text-amber-700',
    icon: AlertTriangle,
    dot: 'bg-amber-500',
  },
  critical: {
    badge: 'border-red-200 bg-red-50 text-red-700',
    icon: AlertCircle,
    dot: 'bg-red-500',
  },
};

export interface BaseStatusDetails {
  tone: StatusTone;
  label: string;
  message?: string | null;
  expiresOn?: string | null;
  lastUpdated?: string | null;
}

export interface SubleaseStatusDetails extends BaseStatusDetails {
  renewalDate?: string | null;
}

export interface CertificateOfInsuranceDetails extends BaseStatusDetails {
  coverageLimit?: string | null;
  broker?: string | null;
}

export interface PermitStatusDetails extends BaseStatusDetails {
  id: string;
  name: string;
  issuedBy?: string | null;
  referenceId?: string | null;
}

export interface ComplianceStatusCardProps {
  kitchenName?: string;
  sublease: SubleaseStatusDetails;
  certificateOfInsurance: CertificateOfInsuranceDetails;
  permits: PermitStatusDetails[];
  pdfEndpoint: string;
  pdfFileName?: string;
  onDownloadStart?: () => void;
  onDownloadComplete?: () => void;
  onDownloadError?: (message: string) => void;
  className?: string;
}

type DownloadState = 'idle' | 'loading' | 'success' | 'error';

function parseFileNameFromContentDisposition(header: string | null): string | null {
  if (!header) {
    return null;
  }

  const filenameMatch = header.match(/filename\*=UTF-8''([^;]+)/);
  if (filenameMatch?.[1]) {
    return decodeURIComponent(filenameMatch[1]);
  }

  const basicMatch = header.match(/filename="?([^";]+)"?/);
  if (basicMatch?.[1]) {
    return basicMatch[1];
  }

  return null;
}

function StatusBadge({ tone, label }: { tone: StatusTone; label: string }) {
  const { badge, icon: Icon } = toneVisuals[tone];
  return (
    <span className={cn('inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium', badge)}>
      <Icon aria-hidden="true" className="h-4 w-4" />
      {label}
    </span>
  );
}

function SectionHeading({
  icon: Icon,
  title,
  description,
  headingId,
}: {
  icon: LucideIcon;
  title: string;
  description?: string | null;
  headingId: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="mt-1 inline-flex h-9 w-9 items-center justify-center rounded-full bg-slate-100 text-slate-600">
        <Icon aria-hidden="true" className="h-5 w-5" />
      </span>
      <div>
        <h3 id={headingId} className="text-base font-semibold text-slate-900">
          {title}
        </h3>
        {description ? <p className="text-sm text-slate-600">{description}</p> : null}
      </div>
    </div>
  );
}

export function ComplianceStatusCard({
  kitchenName,
  sublease,
  certificateOfInsurance,
  permits,
  pdfEndpoint,
  pdfFileName = 'compliance-documentation.pdf',
  onDownloadStart,
  onDownloadComplete,
  onDownloadError,
  className,
}: ComplianceStatusCardProps) {
  const [downloadState, setDownloadState] = useState<DownloadState>('idle');
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownload = async () => {
    setDownloadState('loading');
    setDownloadError(null);
    onDownloadStart?.();

    try {
      const response = await fetch(pdfEndpoint, { method: 'GET' });
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      if (!window.URL?.createObjectURL) {
        throw new Error('PDF download is not supported in this browser.');
      }

      const blob = await response.blob();
      const derivedFileName =
        parseFileNameFromContentDisposition(response.headers.get('Content-Disposition')) ?? pdfFileName;
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = derivedFileName;
      link.rel = 'noopener noreferrer';
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(objectUrl);

      setDownloadState('success');
      onDownloadComplete?.();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to download compliance packet.';
      setDownloadState('error');
      setDownloadError(message);
      onDownloadError?.(message);
    }
  };

  const renderStatusDetails = (status: BaseStatusDetails) => {
    const { tone, message, expiresOn, lastUpdated } = status;
    const toneClasses = toneVisuals[tone];

    return (
      <div className="mt-4 space-y-2 text-sm text-slate-600">
        {message ? <p>{message}</p> : null}
        <dl className="flex flex-wrap gap-x-6 gap-y-2">
          {expiresOn ? (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Expires on</dt>
              <dd className="font-medium text-slate-700">{expiresOn}</dd>
            </div>
          ) : null}
          {lastUpdated ? (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Last updated</dt>
              <dd className="font-medium text-slate-700">{lastUpdated}</dd>
            </div>
          ) : null}
          <div className="flex items-center gap-2">
            <span className={cn('h-2.5 w-2.5 rounded-full', toneClasses.dot)} aria-hidden="true" />
            <span className="text-xs uppercase tracking-wide text-slate-500">Status</span>
          </div>
        </dl>
      </div>
    );
  };

  return (
    <section
      aria-label="Compliance overview"
      className={cn(
        'flex flex-col gap-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm',
        className
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-indigo-600">Compliance summary</p>
          <h2 className="mt-1 text-2xl font-semibold text-slate-900">
            {kitchenName ? `${kitchenName} compliance` : 'Kitchen compliance'}
          </h2>
        </div>
        <StatusBadge tone={sublease.tone} label={sublease.label} />
      </div>

      <div className="space-y-6">
        <article aria-labelledby="sublease-status-heading">
          <SectionHeading
            icon={Building2}
            title="Sublease status"
            description="Verify the current kitchen agreement."
            headingId="sublease-status-heading"
          />
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <StatusBadge tone={sublease.tone} label={sublease.label} />
            {renderStatusDetails(sublease)}
            {sublease.renewalDate ? (
              <div className="mt-3 text-sm text-slate-600">
                <span className="font-medium text-slate-700">Renewal deadline:</span> {sublease.renewalDate}
              </div>
            ) : null}
          </div>
        </article>

        <article aria-labelledby="coi-status-heading">
          <SectionHeading
            icon={ShieldCheck}
            title="Certificate of Insurance"
            description="Maintain an up-to-date certificate of insurance on file."
            headingId="coi-status-heading"
          />
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <StatusBadge tone={certificateOfInsurance.tone} label={certificateOfInsurance.label} />
            {renderStatusDetails(certificateOfInsurance)}
            <dl className="mt-3 grid gap-4 text-sm text-slate-600 sm:grid-cols-2">
              {certificateOfInsurance.coverageLimit ? (
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Coverage limit</dt>
                  <dd className="font-medium text-slate-700">{certificateOfInsurance.coverageLimit}</dd>
                </div>
              ) : null}
              {certificateOfInsurance.broker ? (
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Broker</dt>
                  <dd className="font-medium text-slate-700">{certificateOfInsurance.broker}</dd>
                </div>
              ) : null}
            </dl>
          </div>
        </article>

        <article aria-labelledby="permit-status-heading">
          <SectionHeading
            icon={ClipboardList}
            title="Permits & licenses"
            description="Track permit expirations and outstanding requirements."
            headingId="permit-status-heading"
          />
          <div className="mt-4 space-y-4">
            {permits.length === 0 ? (
              <p className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
                No permits are currently on file. Add required documents to remain compliant.
              </p>
            ) : (
              <ul className="space-y-4" aria-label="Permit list">
                {permits.map((permit) => {
                  const visuals = toneVisuals[permit.tone];
                  return (
                    <li key={permit.id} className="rounded-xl border border-slate-200 bg-slate-50 p-4 shadow-sm">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-slate-900">{permit.name}</p>
                          {permit.message ? (
                            <p className="mt-1 text-sm text-slate-600">{permit.message}</p>
                          ) : null}
                          <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-500">
                            {permit.issuedBy ? (
                              <div>
                                <dt className="uppercase tracking-wide">Issued by</dt>
                                <dd className="text-slate-700">{permit.issuedBy}</dd>
                              </div>
                            ) : null}
                            {permit.referenceId ? (
                              <div>
                                <dt className="uppercase tracking-wide">Reference</dt>
                                <dd className="text-slate-700">{permit.referenceId}</dd>
                              </div>
                            ) : null}
                            {permit.expiresOn ? (
                              <div>
                                <dt className="uppercase tracking-wide">Expires on</dt>
                                <dd className="text-slate-700">{permit.expiresOn}</dd>
                              </div>
                            ) : null}
                          </dl>
                        </div>
                        <StatusBadge tone={permit.tone} label={permit.label} />
                      </div>
                      <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
                        <span className={cn('h-2.5 w-2.5 rounded-full', visuals.dot)} aria-hidden="true" />
                        <span>Permit status</span>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </article>
      </div>

      <footer className="flex flex-col gap-3 border-t border-slate-200 pt-4">
        <button
          type="button"
          onClick={handleDownload}
          className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500 disabled:cursor-not-allowed disabled:bg-indigo-300 sm:w-auto"
          disabled={downloadState === 'loading'}
        >
          <FileDown aria-hidden="true" className="h-4 w-4" />
          {downloadState === 'loading' ? 'Preparing PDF…' : 'Download compliance packet'}
        </button>
        <div role="status" aria-live="polite" className="min-h-[1.5rem] text-sm">
          {downloadState === 'success' ? (
            <p className="text-green-600">Compliance packet downloaded.</p>
          ) : null}
          {downloadState === 'error' && downloadError ? (
            <p className="text-red-600">{downloadError}</p>
          ) : null}
        </div>
      </footer>
    </section>
  );
}

export default ComplianceStatusCard;
