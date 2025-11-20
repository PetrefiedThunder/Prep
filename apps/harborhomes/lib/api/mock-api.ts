/**
 * Mock API Service for PrepChef
 *
 * Simulates FastAPI backend with realistic data.
 * Replace with real API calls when backend is ready.
 *
 * Usage:
 * import { mockApi } from '@/lib/api/mock-api';
 * const vendors = await mockApi.vendors.list();
 */

import type {
  Vendor,
  Document,
  ComplianceAlert,
  Activity,
  DashboardMetrics,
  VendorStats,
  ComplianceTrend,
  SearchResult
} from '@/lib/types/api';

// Simulate network delay
const delay = (ms: number = 300) => new Promise((resolve) => setTimeout(resolve, ms));

// Mock data generators
const generateVendors = (): Vendor[] => {
  const statuses: Vendor['status'][] = ['verified', 'verified', 'verified', 'verified', 'pending', 'expired'];
  const categories = [
    ['Ingredients', 'Produce'],
    ['Equipment', 'Supplies'],
    ['Ingredients', 'Dairy'],
    ['Cleaning', 'Maintenance'],
    ['Packaging', 'Supplies']
  ];

  const vendors: Vendor[] = [
    {
      id: '1',
      name: 'Fresh Ingredients Co.',
      email: 'contact@freshingredients.com',
      phone: '(555) 123-4567',
      status: 'verified',
      complianceScore: 98,
      lastVerified: '2025-01-15T10:00:00Z',
      documentsCount: 8,
      createdAt: '2024-03-20T10:00:00Z',
      address: {
        street: '123 Market St',
        city: 'San Francisco',
        state: 'CA',
        zip: '94103'
      },
      categories: ['Ingredients', 'Produce']
    },
    {
      id: '2',
      name: 'Quality Supplies Inc.',
      email: 'orders@qualitysupplies.com',
      phone: '(555) 234-5678',
      status: 'verified',
      complianceScore: 95,
      lastVerified: '2025-01-14T14:30:00Z',
      documentsCount: 6,
      createdAt: '2024-02-15T10:00:00Z',
      address: {
        street: '456 Industrial Blvd',
        city: 'Oakland',
        state: 'CA',
        zip: '94607'
      },
      categories: ['Equipment', 'Supplies']
    },
    {
      id: '3',
      name: 'Organic Foods Ltd.',
      email: 'info@organicfoods.com',
      phone: '(555) 345-6789',
      status: 'pending',
      complianceScore: 72,
      lastVerified: '2024-12-20T10:00:00Z',
      documentsCount: 4,
      createdAt: '2024-11-01T10:00:00Z',
      address: {
        street: '789 Green Ave',
        city: 'Berkeley',
        state: 'CA',
        zip: '94704'
      },
      categories: ['Ingredients', 'Organic']
    },
    {
      id: '4',
      name: 'Premium Dairy Products',
      email: 'sales@premiumdairy.com',
      phone: '(555) 456-7890',
      status: 'verified',
      complianceScore: 92,
      lastVerified: '2025-01-10T09:00:00Z',
      documentsCount: 7,
      createdAt: '2024-01-10T10:00:00Z',
      address: {
        street: '321 Dairy Ln',
        city: 'San Jose',
        state: 'CA',
        zip: '95110'
      },
      categories: ['Ingredients', 'Dairy']
    },
    {
      id: '5',
      name: 'Kitchen Equipment Pro',
      email: 'support@kitchenequip.com',
      phone: '(555) 567-8901',
      status: 'verified',
      complianceScore: 88,
      lastVerified: '2025-01-12T11:00:00Z',
      documentsCount: 5,
      createdAt: '2024-05-05T10:00:00Z',
      address: {
        street: '654 Commerce Dr',
        city: 'Fremont',
        state: 'CA',
        zip: '94538'
      },
      categories: ['Equipment', 'Maintenance']
    },
    {
      id: '6',
      name: 'Global Spice Traders',
      email: 'info@globalspice.com',
      phone: '(555) 678-9012',
      status: 'expired',
      complianceScore: 45,
      lastVerified: '2024-09-15T10:00:00Z',
      documentsCount: 3,
      createdAt: '2024-08-01T10:00:00Z',
      address: {
        street: '987 Trade St',
        city: 'San Francisco',
        state: 'CA',
        zip: '94105'
      },
      categories: ['Ingredients', 'Spices']
    }
  ];

  return vendors;
};

const generateDocuments = (): Document[] => {
  const today = new Date();
  const addDays = (days: number) => {
    const date = new Date(today);
    date.setDate(date.getDate() + days);
    return date.toISOString();
  };

  return [
    {
      id: '1',
      name: 'Health Permit',
      type: 'permit',
      vendorId: '1',
      vendorName: 'Fresh Ingredients Co.',
      status: 'expiring',
      issueDate: '2024-01-20T00:00:00Z',
      expiryDate: addDays(7),
      daysUntilExpiry: 7,
      verifiedBy: 'John Admin',
      verifiedAt: '2024-01-20T10:00:00Z'
    },
    {
      id: '2',
      name: 'Liability Insurance',
      type: 'insurance',
      vendorId: '2',
      vendorName: 'Quality Supplies Inc.',
      status: 'expiring',
      issueDate: '2024-02-01T00:00:00Z',
      expiryDate: addDays(14),
      daysUntilExpiry: 14,
      verifiedBy: 'Sarah Manager',
      verifiedAt: '2024-02-01T10:00:00Z'
    },
    {
      id: '3',
      name: 'Food Handler Certificate',
      type: 'certification',
      vendorId: '1',
      vendorName: 'Fresh Ingredients Co.',
      status: 'expiring',
      issueDate: '2024-03-01T00:00:00Z',
      expiryDate: addDays(21),
      daysUntilExpiry: 21,
      verifiedBy: 'John Admin',
      verifiedAt: '2024-03-01T10:00:00Z'
    },
    {
      id: '4',
      name: 'Fire Safety Inspection',
      type: 'inspection',
      vendorId: '3',
      vendorName: 'Organic Foods Ltd.',
      status: 'expiring',
      issueDate: '2024-04-01T00:00:00Z',
      expiryDate: addDays(28),
      daysUntilExpiry: 28,
      verifiedBy: 'Mike Inspector',
      verifiedAt: '2024-04-01T10:00:00Z'
    },
    {
      id: '5',
      name: 'FDA Certification',
      type: 'certification',
      vendorId: '4',
      vendorName: 'Premium Dairy Products',
      status: 'active',
      issueDate: '2024-05-01T00:00:00Z',
      expiryDate: addDays(180),
      daysUntilExpiry: 180,
      verifiedBy: 'John Admin',
      verifiedAt: '2024-05-01T10:00:00Z'
    },
    {
      id: '6',
      name: 'Business License',
      type: 'license',
      vendorId: '6',
      vendorName: 'Global Spice Traders',
      status: 'expired',
      issueDate: '2024-01-01T00:00:00Z',
      expiryDate: addDays(-30),
      daysUntilExpiry: -30
    }
  ];
};

// Mock API implementation
export const mockApi = {
  // Dashboard
  dashboard: {
    async getMetrics(): Promise<DashboardMetrics> {
      await delay();
      return {
        activeVendors: { value: 247, change: 12, changeLabel: 'vs last month' },
        complianceRate: { value: 94.2, change: 2.1, changeLabel: 'from last week' },
        documentsExpiring: { value: 18, change: -5, changeLabel: 'vs last month' },
        verificationsPending: { value: 7, change: -3, changeLabel: 'vs yesterday' }
      };
    },

    async getAlerts(): Promise<ComplianceAlert[]> {
      await delay();
      return [
        {
          id: '1',
          title: 'Health Permit Expiring Soon',
          description: 'Fresh Ingredients Co. health permit expires in 7 days',
          severity: 'high',
          type: 'expiry',
          vendorId: '1',
          vendorName: 'Fresh Ingredients Co.',
          documentId: '1',
          createdAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '2',
          title: 'Insurance Certificate Needed',
          description: 'Quality Supplies Inc. missing liability insurance',
          severity: 'high',
          type: 'missing',
          vendorId: '2',
          vendorName: 'Quality Supplies Inc.',
          createdAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '3',
          title: 'Inspection Scheduled',
          description: 'Health inspection scheduled for Organic Foods Ltd.',
          severity: 'medium',
          type: 'inspection',
          vendorId: '3',
          vendorName: 'Organic Foods Ltd.',
          createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '4',
          title: 'Training Certification Due',
          description: 'Premium Dairy Products - 3 staff need recertification',
          severity: 'medium',
          type: 'expiry',
          vendorId: '4',
          vendorName: 'Premium Dairy Products',
          createdAt: new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString()
        }
      ];
    },

    async getRecentActivity(): Promise<Activity[]> {
      await delay();
      const now = Date.now();
      return [
        {
          id: '1',
          type: 'verification',
          vendorId: '1',
          vendorName: 'Fresh Ingredients Co.',
          action: 'Insurance verification completed',
          status: 'completed',
          performedBy: 'John Admin',
          createdAt: new Date(now - 10 * 60 * 1000).toISOString()
        },
        {
          id: '2',
          type: 'renewal',
          vendorId: '2',
          vendorName: 'Quality Supplies Inc.',
          action: 'Health permit renewed',
          status: 'completed',
          performedBy: 'Sarah Manager',
          createdAt: new Date(now - 60 * 60 * 1000).toISOString()
        },
        {
          id: '3',
          type: 'verification',
          vendorId: '3',
          vendorName: 'Organic Foods Ltd.',
          action: 'Document verification in progress',
          status: 'pending',
          performedBy: 'Mike Inspector',
          createdAt: new Date(now - 2 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '4',
          type: 'expiry',
          vendorId: '6',
          vendorName: 'Global Spice Traders',
          action: 'Fire safety certificate expired',
          status: 'failed',
          performedBy: 'System',
          createdAt: new Date(now - 3 * 60 * 60 * 1000).toISOString()
        },
        {
          id: '5',
          type: 'verification',
          vendorId: '4',
          vendorName: 'Premium Dairy Products',
          action: 'FDA certification verified',
          status: 'completed',
          performedBy: 'John Admin',
          createdAt: new Date(now - 5 * 60 * 60 * 1000).toISOString()
        }
      ];
    },

    async getVendorStats(): Promise<VendorStats> {
      await delay();
      return {
        total: 247,
        verified: 232,
        pending: 12,
        expired: 3
      };
    },

    async getComplianceTrends(): Promise<ComplianceTrend[]> {
      await delay();
      const trends: ComplianceTrend[] = [];
      const today = new Date();

      for (let i = 29; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        trends.push({
          date: date.toISOString().split('T')[0],
          rate: 88 + Math.random() * 8,
          vendors: 230 + Math.floor(Math.random() * 20)
        });
      }

      return trends;
    }
  },

  // Vendors
  vendors: {
    async list(): Promise<Vendor[]> {
      await delay();
      return generateVendors();
    },

    async getById(id: string): Promise<Vendor | null> {
      await delay();
      const vendors = generateVendors();
      return vendors.find((v) => v.id === id) || null;
    },

    async search(query: string): Promise<Vendor[]> {
      await delay(500);
      const vendors = generateVendors();
      const lowerQuery = query.toLowerCase();
      return vendors.filter(
        (v) =>
          v.name.toLowerCase().includes(lowerQuery) ||
          v.email.toLowerCase().includes(lowerQuery) ||
          v.categories.some((c) => c.toLowerCase().includes(lowerQuery))
      );
    }
  },

  // Documents
  documents: {
    async list(): Promise<Document[]> {
      await delay();
      return generateDocuments();
    },

    async getById(id: string): Promise<Document | null> {
      await delay();
      const docs = generateDocuments();
      return docs.find((d) => d.id === id) || null;
    },

    async getByVendorId(vendorId: string): Promise<Document[]> {
      await delay();
      const docs = generateDocuments();
      return docs.filter((d) => d.vendorId === vendorId);
    },

    async getExpiring(days: number = 30): Promise<Document[]> {
      await delay();
      const docs = generateDocuments();
      return docs.filter((d) => d.daysUntilExpiry > 0 && d.daysUntilExpiry <= days);
    }
  },

  // Search
  search: {
    async global(query: string): Promise<SearchResult> {
      await delay(600);
      const vendors = await mockApi.vendors.search(query);
      const allDocs = generateDocuments();
      const lowerQuery = query.toLowerCase();

      const documents = allDocs.filter(
        (d) =>
          d.name.toLowerCase().includes(lowerQuery) ||
          d.vendorName.toLowerCase().includes(lowerQuery) ||
          d.type.toLowerCase().includes(lowerQuery)
      );

      return {
        vendors,
        documents,
        total: vendors.length + documents.length
      };
    }
  }
};
