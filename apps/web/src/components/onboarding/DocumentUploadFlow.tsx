import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from 'react';

type DocumentUpload = {
  id: string;
  file_name: string;
  file_url: string;
  ocr_status: string;
  requirement_key?: string | null;
  created_at?: string;
  updated_at?: string;
};

type DocumentUploadFlowProps = {
  businessId: string;
  permitId?: string;
  requirementKey?: string;
  pollIntervalMs?: number;
  onUploaded?: (document: DocumentUpload) => void;
  className?: string;
};

const OCR_STATUS_COPY: Record<string, { label: string; tone: string }> = {
  received: { label: 'Received', tone: 'text-slate-500' },
  processing: { label: 'Processing OCR', tone: 'text-amber-500' },
  completed: { label: 'OCR completed', tone: 'text-emerald-600' },
  failed: { label: 'OCR failed', tone: 'text-red-600' },
};

export function DocumentUploadFlow({
  businessId,
  permitId,
  requirementKey,
  pollIntervalMs = 5000,
  onUploaded,
  className,
}: DocumentUploadFlowProps) {
  const [file, setFile] = useState<File | null>(null);
  const [document, setDocument] = useState<DocumentUpload | null>(null);
  const [uploadState, setUploadState] = useState<'idle' | 'uploading' | 'processing' | 'completed' | 'failed'>(
    'idle'
  );
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setError(null);
  };

  const fetchDocument = useCallback(
    async (id: string) => {
      const res = await fetch(`/api/v1/platform/documents/${id}`);
      if (!res.ok) {
        throw new Error(`Failed to refresh OCR status (${res.status})`);
      }
      const payload = await res.json();
      setDocument(payload);
      const status = String(payload.ocr_status ?? payload.ocrStatus ?? 'processing').toLowerCase();
      if (status === 'completed') {
        setUploadState('completed');
        onUploaded?.(payload);
      } else if (status === 'failed') {
        setUploadState('failed');
      } else {
        setUploadState('processing');
      }
    },
    [onUploaded]
  );

  useEffect(() => {
    if (!document || uploadState === 'completed' || uploadState === 'failed') {
      return;
    }
    const id = window.setInterval(() => {
      void fetchDocument(document.id).catch((err) => {
        setError(err instanceof Error ? err.message : 'Unknown error');
      });
    }, pollIntervalMs);
    return () => window.clearInterval(id);
  }, [document, fetchDocument, pollIntervalMs, uploadState]);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) {
      setError('Select a document to continue');
      return;
    }
    setError(null);
    setUploadState('uploading');

    try {
      const body = {
        business_id: businessId,
        permit_id: permitId,
        requirement_key: requirementKey,
        file_name: file.name,
        file_url: `https://uploads.prep.local/${encodeURIComponent(file.name)}-${Date.now()}`,
        content_type: file.type || 'application/octet-stream',
        storage_bucket: 'prep-onboarding',
        trigger_ocr: true,
      };

      const res = await fetch('/api/v1/platform/documents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`Upload failed (${res.status})`);
      }

      const payload: DocumentUpload = await res.json();
      setDocument(payload);
      onUploaded?.(payload);
      const status = String(payload.ocr_status ?? payload.ocrStatus ?? 'processing').toLowerCase();
      if (status === 'completed') {
        setUploadState('completed');
      } else if (status === 'failed') {
        setUploadState('failed');
      } else {
        setUploadState('processing');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to upload document');
      setUploadState('failed');
    }
  };

  const statusLabel = useMemo(() => {
    const statusKey = uploadState === 'uploading' ? 'received' : document?.ocr_status ?? 'idle';
    const normalized = String(statusKey).toLowerCase();
    return OCR_STATUS_COPY[normalized]?.label ?? 'Awaiting upload';
  }, [document?.ocr_status, uploadState]);

  const statusTone = useMemo(() => {
    const statusKey = uploadState === 'uploading' ? 'received' : document?.ocr_status ?? 'idle';
    const normalized = String(statusKey).toLowerCase();
    return OCR_STATUS_COPY[normalized]?.tone ?? 'text-slate-400';
  }, [document?.ocr_status, uploadState]);

  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className ?? ''}`}>
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Document upload & OCR</h2>
        <p className="text-sm text-slate-500">
          Securely upload permits, insurance, and compliance docs. We automatically trigger OCR processing so your
          regulatory team can review without manual data entry.
        </p>
      </header>

      <form className="space-y-3" onSubmit={submit}>
        <input type="file" accept="application/pdf,image/*" onChange={handleFileChange} />
        <button
          type="submit"
          className="rounded-md bg-emerald-500 px-3 py-2 text-sm font-semibold text-white shadow hover:bg-emerald-600 disabled:cursor-not-allowed disabled:bg-emerald-300"
          disabled={!file || uploadState === 'uploading'}
        >
          {uploadState === 'uploading' ? 'Uploading…' : 'Upload and start OCR'}
        </button>
      </form>

      {error && <p className="mt-3 rounded-md bg-red-50 p-3 text-sm text-red-600">{error}</p>}

      <div className="mt-4 rounded-md bg-slate-50 p-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="font-medium text-slate-600">OCR status</span>
          <span className={`font-semibold ${statusTone}`}>{statusLabel}</span>
        </div>
        {document && (
          <dl className="mt-3 grid gap-2 text-xs text-slate-500 md:grid-cols-2">
            <div>
              <dt className="font-medium text-slate-600">File</dt>
              <dd>{document.file_name}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-600">Requirement</dt>
              <dd>{document.requirement_key ?? requirementKey ?? '—'}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-600">Submitted</dt>
              <dd>{document.created_at ? new Date(document.created_at).toLocaleString() : 'Just now'}</dd>
            </div>
            <div>
              <dt className="font-medium text-slate-600">Last updated</dt>
              <dd>{document.updated_at ? new Date(document.updated_at).toLocaleString() : 'Pending'}</dd>
            </div>
          </dl>
        )}
      </div>
    </section>
  );
}

export type { DocumentUpload };
