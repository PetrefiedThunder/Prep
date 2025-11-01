import { useMemo, useState } from 'react';

import DocumentUploadStep from './DocumentUploadStep';
import FeeEstimatorStep from './FeeEstimatorStep';
import RequirementsChecklistStep from './RequirementsChecklistStep';
import type {
  BusinessReadinessResponse,
  CheckoutPaymentResponse,
  DocumentUploadResponse,
} from './types';

type OnboardingFlowProps = {
  businessId: string;
  locale?: string;
};

const stepLabels = ['Requirements', 'Fee estimator', 'Document upload'];

export default function OnboardingFlow({ businessId, locale = 'en-US' }: OnboardingFlowProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [readiness, setReadiness] = useState<BusinessReadinessResponse | null>(null);
  const [estimate, setEstimate] = useState<CheckoutPaymentResponse | null>(null);
  const [upload, setUpload] = useState<DocumentUploadResponse | null>(null);

  const advance = () => setStepIndex((current) => Math.min(current + 1, stepLabels.length - 1));
  const retreat = () => setStepIndex((current) => Math.max(current - 1, 0));

  const heading = useMemo(() => stepLabels[stepIndex] ?? stepLabels[0], [stepIndex]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">Onboarding checklist</p>
        <h1 className="text-2xl font-bold text-slate-900">{heading}</h1>
        <p className="text-sm text-slate-600">
          Progress through each section to unlock bookings, payments, and automated permit reminders for your business.
        </p>
      </header>

      <ol className="flex items-center gap-4 text-xs font-semibold uppercase tracking-wide text-slate-500">
        {stepLabels.map((label, index) => (
          <li
            key={label}
            className={`flex items-center gap-2 ${index === stepIndex ? 'text-indigo-600' : ''}`}
          >
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full border text-sm ${
                index <= stepIndex ? 'border-indigo-600 text-indigo-600' : 'border-slate-300 text-slate-400'
              }`}
            >
              {index + 1}
            </span>
            {label}
          </li>
        ))}
      </ol>

      {stepIndex === 0 && (
        <RequirementsChecklistStep
          businessId={businessId}
          onContinue={advance}
          onLoaded={setReadiness}
        />
      )}

      {stepIndex === 1 && (
        <FeeEstimatorStep
          businessId={businessId}
          readiness={readiness}
          locale={locale}
          onBack={retreat}
          onContinue={(quote) => {
            setEstimate(quote);
            advance();
          }}
        />
      )}

      {stepIndex === 2 && (
        <DocumentUploadStep
          businessId={businessId}
          readiness={readiness}
          estimate={estimate}
          onBack={retreat}
          onFinish={(result) => {
            setUpload(result);
            if (result) {
              // Stay on the final step but surface a success summary below.
            }
          }}
        />
      )}

      {upload && (
        <aside className="rounded-md border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
          <p className="font-semibold">All set!</p>
          <p className="mt-1">
            We stored <strong>{upload.filename}</strong> and kicked off OCR ({upload.ocr_status}). Our compliance team will send
            automated updates as the permit wallet syncs with your readiness score.
          </p>
        </aside>
      )}
    </div>
  );
}
