/**
 * PrepChef API Type Definitions
 *
 * These types match the expected backend API structure.
 * Replace with generated types from OpenAPI spec when backend is ready.
 */

export interface Vendor {
  id: string;
  name: string;
  email: string;
  phone: string;
  status: 'verified' | 'pending' | 'expired' | 'suspended';
  complianceScore: number;
  lastVerified: string;
  documentsCount: number;
  createdAt: string;
  address: {
    street: string;
    city: string;
    state: string;
    zip: string;
  };
  categories: string[];
}

export interface Document {
  id: string;
  name: string;
  type: 'permit' | 'insurance' | 'certification' | 'inspection' | 'license';
  vendorId: string;
  vendorName: string;
  status: 'active' | 'expiring' | 'expired' | 'pending';
  issueDate: string;
  expiryDate: string;
  daysUntilExpiry: number;
  fileUrl?: string;
  verifiedBy?: string;
  verifiedAt?: string;
}

export interface ComplianceAlert {
  id: string;
  title: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
  type: 'expiry' | 'missing' | 'violation' | 'inspection';
  vendorId: string;
  vendorName: string;
  documentId?: string;
  createdAt: string;
  resolvedAt?: string;
}

export interface Activity {
  id: string;
  type: 'verification' | 'expiry' | 'renewal' | 'violation' | 'upload';
  vendorId: string;
  vendorName: string;
  action: string;
  status: 'completed' | 'pending' | 'failed';
  performedBy: string;
  createdAt: string;
}

export interface DashboardMetrics {
  activeVendors: {
    value: number;
    change: number;
    changeLabel: string;
  };
  complianceRate: {
    value: number;
    change: number;
    changeLabel: string;
  };
  documentsExpiring: {
    value: number;
    change: number;
    changeLabel: string;
  };
  verificationsPending: {
    value: number;
    change: number;
    changeLabel: string;
  };
}

export interface VendorStats {
  total: number;
  verified: number;
  pending: number;
  expired: number;
}

export interface ComplianceTrend {
  date: string;
  rate: number;
  vendors: number;
}

export interface SearchResult {
  vendors: Vendor[];
  documents: Document[];
  total: number;
}
