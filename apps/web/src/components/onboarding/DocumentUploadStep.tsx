import { FormEvent, useMemo, useState } from 'react';

import type {
  BusinessReadinessResponse,
  CheckoutPaymentResponse,
  DocumentUploadResponse,
} from './types';

type DocumentUploadStepProps = {
  businessId: string;
  readiness: BusinessReadinessResponse | null;
  estimate: CheckoutPaymentResponse | null;
  onBack: () => void;
  onFinish: (upload: DocumentUploadResponse | null) => void;
};

const documentOptions = [
  { value: 'business_license', label: 'Business license or registration' },
  { value: 'health_permit', label: 'Health permit' },
  { value: 'fire_certificate', label: 'Fire inspection certificate' },
  { value: 'insurance_certificate', label: 'Certificate of insurance' },
];

export default function DocumentUploadStep({
  businessId,
  readiness,
  estimate,
  onBack,
  onFinish,
}: DocumentUploadStepProps) {
  const [documentType, setDocumentType] = useState(documentOptions[0]?.value ?? 'business_license');
  const [file, setFile] = useState<File | null>(null);
  const [notes, setNotes] = useState('');
  const [upload, setUpload] = useState<DocumentUploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const readinessScore = readiness ? Math.round(readiness.readiness_score * 100) : null;
  const totalDue = useMemo(() => (estimate ? estimate.total_amount : 0), [estimate]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError('Select a document to upload.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        business_id: readiness?.business_id ?? businessId,
        document_type: documentType,
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        storage_bucket: 'onboarding-uploads',
        storage_key: `${businessId}/${Date.now()}-${file.name}`,
        metadata: {
          size: file.size,
          original_last_modified: file.lastModified,
          source: 'onboarding_document_flow',
        },
        notes: notes || undefined,
      };
      const response = await fetch('/api/v1/platform/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }
      const data: DocumentUploadResponse = await response.json();
      setUpload(data);
      onFinish(data);
    } catch (err) {
      console.error(err);
      setError('We were unable to store this document. Please retry or reach out to support@prep.cooking.');
      onFinish(null);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <header className="space-y-2">
        <h2 className="text-xl font-semibold">Step 3: Upload compliance documents</h2>
        <p className="text-sm text-slate-600">
          Your files are encrypted at rest and routed through our OCR service so we can fast-track verification.
        </p>
      </header>

      <section className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700">Readiness score</h3>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {readinessScore !== null ? `${readinessScore}%` : '—'}
          </p>
          {readiness && (
            <p className="mt-2 text-xs text-slate-500">
              Last evaluated {new Date(readiness.last_evaluated_at).toLocaleString()}
            </p>
          )}
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-700">Estimated payment</h3>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {estimate ? `$${totalDue.toFixed(2)}` : 'Pending quote'}
          </p>
          {estimate?.receipt_url && (
            <a
              href={estimate.receipt_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex text-xs font-medium text-indigo-600 hover:underline"
            >
              View provisional receipt
            </a>
          )}
        </div>
      </section>

      <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <label className="block text-sm font-medium text-slate-700">
          Document category
          <select
            value={documentType}
            onChange={(event) => setDocumentType(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
          >
            {documentOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Upload file
          <input
            type="file"
            accept="application/pdf,image/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm text-slate-600"
          />
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Notes for the compliance team (optional)
          <textarea
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            rows={3}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500"
            placeholder="Include any context such as jurisdiction or contact details."
          />
        </label>

        {error && <p className="text-sm text-rose-600">{error}</p>}

        {upload && (
          <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
            <p className="font-semibold">Upload received!</p>
            <p className="mt-1">
              We are processing OCR ({upload.ocr_status}). We will notify you once the text extraction is complete and a reviewer has approved the document.
            </p>
          </div>
        )}
      </section>

      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm"
        >
          Back to estimator
        </button>
        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {submitting ? 'Uploading…' : 'Submit document'}
        </button>
      </div>
    </form>
  );
}
