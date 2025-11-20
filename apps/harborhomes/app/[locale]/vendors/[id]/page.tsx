'use client';

import * as React from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { PageHeader } from '@/components/layout/page-header';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Button,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  Alert,
  AlertTitle,
  AlertDescription
} from '@/components/ui';
import {
  Building2,
  Mail,
  Phone,
  MapPin,
  FileText,
  Calendar,
  ArrowLeft,
  Edit,
  AlertCircle
} from 'lucide-react';
import type { Vendor, Document } from '@/lib/types/api';

export default function VendorDetailPage() {
  const params = useParams();
  const vendorId = params.id as string;

  const [vendor, setVendor] = React.useState<Vendor | null>(null);
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const loadVendorData = async () => {
      try {
        const { mockApi } = await import('@/lib/api/mock-api');
        const [vendorData, docsData] = await Promise.all([
          mockApi.vendors.getById(vendorId),
          mockApi.documents.getByVendorId(vendorId)
        ]);

        setVendor(vendorData);
        setDocuments(docsData);
      } catch (error) {
        console.error('Failed to load vendor:', error);
      } finally {
        setLoading(false);
      }
    };

    loadVendorData();
  }, [vendorId]);

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-20 w-full animate-pulse rounded-lg bg-border/40" />
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="h-96 animate-pulse rounded-lg bg-border/40 lg:col-span-2" />
          <div className="h-96 animate-pulse rounded-lg bg-border/40" />
        </div>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <Alert variant="error" className="max-w-md">
          <AlertTitle>Vendor Not Found</AlertTitle>
          <AlertDescription>The requested vendor could not be found.</AlertDescription>
        </Alert>
      </div>
    );
  }

  const statusConfig = {
    verified: { variant: 'success' as const, label: 'Verified' },
    pending: { variant: 'warning' as const, label: 'Pending Review' },
    expired: { variant: 'error' as const, label: 'Expired' },
    suspended: { variant: 'error' as const, label: 'Suspended' }
  };

  const config = statusConfig[vendor.status];

  return (
    <div className="space-y-6">
      <PageHeader
        title={vendor.name}
        description={`Vendor ID: ${vendor.id} • Compliance Score: ${vendor.complianceScore}%`}
        breadcrumbs={
          <Link href="/en/vendors" className="flex items-center gap-1 text-brand hover:underline">
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Vendors
          </Link>
        }
        actions={
          <Button variant="outline">
            <Edit className="h-4 w-4 mr-2" />
            Edit Vendor
          </Button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Status Alert */}
          {vendor.status !== 'verified' && (
            <Alert variant={vendor.status === 'pending' ? 'warning' : 'error'}>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Action Required</AlertTitle>
              <AlertDescription>
                {vendor.status === 'pending'
                  ? 'This vendor is pending verification. Review and approve their documents to complete onboarding.'
                  : 'This vendor has expired credentials. Contact them to update their documentation.'}
              </AlertDescription>
            </Alert>
          )}

          {/* Documents Table */}
          <Card>
            <CardHeader>
              <CardTitle>Documents ({documents.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {documents.length === 0 ? (
                <div className="py-8 text-center text-ink-muted">
                  <FileText className="mx-auto h-8 w-8 opacity-50" />
                  <p className="mt-2">No documents on file</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Document Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Expiry Date</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {documents.map((doc) => {
                      const statusVariant =
                        doc.status === 'active'
                          ? 'success'
                          : doc.status === 'expiring'
                            ? 'warning'
                            : 'error';
                      return (
                        <TableRow key={doc.id}>
                          <TableCell className="font-medium">{doc.name}</TableCell>
                          <TableCell className="capitalize">{doc.type}</TableCell>
                          <TableCell>
                            <Badge variant={statusVariant as any} size="sm">
                              {doc.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            {new Date(doc.expiryDate).toLocaleDateString()}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Status Card */}
          <Card>
            <CardHeader>
              <CardTitle>Status</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-ink-muted mb-1">Compliance Status</div>
                  <Badge variant={config.variant}>{config.label}</Badge>
                </div>
                <div>
                  <div className="text-sm text-ink-muted mb-1">Compliance Score</div>
                  <div className="text-3xl font-bold text-brand">{vendor.complianceScore}%</div>
                </div>
                <div>
                  <div className="text-sm text-ink-muted mb-1">Last Verified</div>
                  <div className="text-sm text-ink">
                    {new Date(vendor.lastVerified).toLocaleDateString()}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Contact Info */}
          <Card>
            <CardHeader>
              <CardTitle>Contact Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="h-4 w-4 text-ink-muted" />
                  <a href={`mailto:${vendor.email}`} className="text-brand hover:underline">
                    {vendor.email}
                  </a>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <Phone className="h-4 w-4 text-ink-muted" />
                  <a href={`tel:${vendor.phone}`} className="text-brand hover:underline">
                    {vendor.phone}
                  </a>
                </div>
                <div className="flex items-start gap-2 text-sm">
                  <MapPin className="h-4 w-4 text-ink-muted mt-0.5" />
                  <div>
                    <div>{vendor.address.street}</div>
                    <div>
                      {vendor.address.city}, {vendor.address.state} {vendor.address.zip}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Categories */}
          <Card>
            <CardHeader>
              <CardTitle>Categories</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {vendor.categories.map((category, index) => (
                  <Badge key={index} variant="outline">
                    {category}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
