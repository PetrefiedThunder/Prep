import { useMemo, useState } from 'react';

import { DocumentUpload, DocumentUploadFlow } from './DocumentUploadFlow';
import { FeeEstimator, LineItem } from './FeeEstimator';
import { Requirement, RequirementsChecklist } from './RequirementsChecklist';

type OnboardingFlowProps = {
  businessId: string;
  permitId?: string;
  locale?: string;
  className?: string;
};

type Step = {
  id: 'requirements' | 'fees' | 'documents';
  title: string;
  description: string;
};

const translations: Record<string, Step[]> = {
  'es-es': [
    {
      id: 'requirements',
      title: 'Lista de requisitos',
      description: 'Verifica cada hito de cumplimiento para desbloquear la reserva de cocinas.',
    },
    {
      id: 'fees',
      title: 'Estimador de tarifas',
      description: 'Calcula tarifas municipales, depósitos y cobros de plataforma antes de pagar.',
    },
    {
      id: 'documents',
      title: 'Carga de documentos',
      description: 'Sube comprobantes y rastrea el estado del OCR automático.',
    },
  ],
};

const defaultSteps: Step[] = [
  {
    id: 'requirements',
    title: 'Requirements checklist',
    description: 'Confirm health, fire, and operating milestones to reach launch readiness.',
  },
  {
    id: 'fees',
    title: 'Fee estimator',
    description: 'Bundle inspection, subscription, and refundable fees before checkout.',
  },
  {
    id: 'documents',
    title: 'Document upload',
    description: 'Upload compliance packets and monitor OCR progress in real time.',
  },
];

function resolveSteps(locale?: string): Step[] {
  const normalized = (locale ?? 'en-US').toLowerCase();
  return translations[normalized] ?? defaultSteps;
}

export function OnboardingFlow({ businessId, permitId, locale, className }: OnboardingFlowProps) {
  const steps = useMemo(() => resolveSteps(locale), [locale]);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [readinessScore, setReadinessScore] = useState(0);
  const [estimate, setEstimate] = useState<{ totalCents: number; lineItems: LineItem[] }>({ totalCents: 0, lineItems: [] });
  const [uploadedDoc, setUploadedDoc] = useState<DocumentUpload | null>(null);

  const activeStep = steps[activeStepIndex];

  const nextDisabled = useMemo(() => {
    if (activeStep.id === 'requirements') {
      return requirements.length === 0 || readinessScore < 0.5;
    }
    if (activeStep.id === 'fees') {
      return estimate.totalCents <= 0;
    }
    if (activeStep.id === 'documents') {
      return !uploadedDoc;
    }
    return false;
  }, [activeStep.id, estimate.totalCents, readinessScore, requirements.length, uploadedDoc]);

  const goNext = () => {
    setActiveStepIndex((idx) => Math.min(idx + 1, steps.length - 1));
  };

  const goPrevious = () => {
    setActiveStepIndex((idx) => Math.max(idx - 1, 0));
  };

  return (
    <section className={`space-y-4 ${className ?? ''}`}>
      <header className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">Onboarding assistant</h1>
        <p className="mt-1 text-sm text-slate-500">
          Guided workflow to launch your business in the Prep marketplace. Progress is saved as you go.
        </p>
        <ol className="mt-4 flex flex-wrap items-center gap-3 text-sm">
          {steps.map((step, index) => {
            const complete = index < activeStepIndex;
            const current = index === activeStepIndex;
            return (
              <li
                key={step.id}
                className={`flex items-center gap-2 rounded-full px-3 py-1 ${
                  current ? 'bg-emerald-100 text-emerald-700' : complete ? 'bg-slate-100 text-slate-600' : 'bg-white text-slate-400'
                }`}
              >
                <span className="text-xs font-semibold">{index + 1}</span>
                <span className="font-medium">{step.title}</span>
              </li>
            );
          })}
        </ol>
      </header>

      <article className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <header className="mb-4">
          <h2 className="text-lg font-semibold text-slate-900">{activeStep.title}</h2>
          <p className="text-sm text-slate-500">{activeStep.description}</p>
        </header>

        {activeStep.id === 'requirements' && (
          <RequirementsChecklist
            businessId={businessId}
            onStatusChange={(nextRequirements, score) => {
              setRequirements(nextRequirements);
              setReadinessScore(score);
            }}
          />
        )}

        {activeStep.id === 'fees' && (
          <FeeEstimator
            onEstimate={(summary) => {
              setEstimate(summary);
            }}
          />
        )}

        {activeStep.id === 'documents' && (
          <DocumentUploadFlow
            businessId={businessId}
            permitId={permitId}
            requirementKey={requirements[0]?.name.toLowerCase().replace(/\s+/g, '_')}
            onUploaded={(doc) => {
              setUploadedDoc(doc);
            }}
          />
        )}

        <footer className="mt-6 flex items-center justify-between text-sm">
          <button
            type="button"
            onClick={goPrevious}
            disabled={activeStepIndex === 0}
            className="rounded-md border border-slate-200 px-3 py-2 font-medium text-slate-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Back
          </button>
          <button
            type="button"
            onClick={goNext}
            disabled={nextDisabled || activeStepIndex === steps.length - 1}
            className="rounded-md bg-emerald-500 px-4 py-2 font-semibold text-white shadow hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-300"
          >
            Continue
          </button>
        </footer>
      </article>

      <aside className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        <h3 className="text-base font-semibold text-slate-800">Progress summary</h3>
        <dl className="mt-2 grid gap-2 md:grid-cols-2">
          <div>
            <dt className="font-medium text-slate-500">Readiness</dt>
            <dd>{Math.round(readinessScore * 100)}% complete</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-500">Estimated fees</dt>
            <dd>
              {new Intl.NumberFormat(undefined, {
                style: 'currency',
                currency: 'USD',
                maximumFractionDigits: 2,
              }).format(estimate.totalCents / 100)}
            </dd>
          </div>
          <div>
            <dt className="font-medium text-slate-500">Document OCR</dt>
            <dd>{uploadedDoc ? uploadedDoc.ocr_status : 'Pending'}</dd>
          </div>
          <div>
            <dt className="font-medium text-slate-500">Line items</dt>
            <dd>{estimate.lineItems.length}</dd>
          </div>
        </dl>
      </aside>
    </section>
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
