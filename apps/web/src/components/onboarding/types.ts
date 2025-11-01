export type ReadinessStatus = 'complete' | 'in_review' | 'missing';

export type BusinessReadinessChecklistItem = {
  slug: string;
  title: string;
  description: string;
  status: ReadinessStatus;
  completed_at: string | null;
};

export type BusinessReadinessResponse = {
  business_id: string;
  business_name: string;
  readiness_score: number;
  readiness_stage: string;
  checklist: BusinessReadinessChecklistItem[];
  gating_requirements: string[];
  outstanding_actions: string[];
  last_evaluated_at: string;
};

export type CheckoutLineItem = {
  name: string;
  amount: number;
  quantity: number;
  taxable: boolean;
  refundable: boolean;
};

export type CheckoutPaymentResponse = {
  id: string;
  business_id: string | null;
  booking_id: string | null;
  status: string;
  currency: string;
  total_amount: number;
  line_items: CheckoutLineItem[];
  payment_provider: string;
  provider_reference: string | null;
  receipt_url: string | null;
  metadata: Record<string, unknown> | null;
  refund_reason: string | null;
  refund_requested_at: string | null;
  refunded_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentUploadResponse = {
  id: string;
  business_id: string;
  document_type: string;
  filename: string;
  content_type: string | null;
  storage_bucket: string;
  storage_key: string;
  status: string;
  ocr_status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};
