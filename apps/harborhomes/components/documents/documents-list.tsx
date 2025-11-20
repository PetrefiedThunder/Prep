'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Card,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  Badge,
  SkeletonTable
} from '@/components/ui';
import { FileText, Calendar, Download, ExternalLink } from 'lucide-react';
import type { Document } from '@/lib/types/api';

interface DocumentsListProps {
  typeFilter: string;
  statusFilter: string;
  searchQuery: string;
}

export const DocumentsList = ({ typeFilter, statusFilter, searchQuery }: DocumentsListProps) => {
  const [documents, setDocuments] = React.useState<Document[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const loadDocuments = async () => {
      setLoading(true);
      try {
        const { mockApi } = await import('@/lib/api/mock-api');
        let data = await mockApi.documents.list();

        // Apply type filter
        if (typeFilter !== 'all') {
          data = data.filter((d) => d.type === typeFilter);
        }

        // Apply status filter
        if (statusFilter !== 'all') {
          data = data.filter((d) => d.status === statusFilter);
        }

        // Apply search filter
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          data = data.filter(
            (d) =>
              d.name.toLowerCase().includes(query) ||
              d.vendorName.toLowerCase().includes(query) ||
              d.type.toLowerCase().includes(query)
          );
        }

        setDocuments(data);
      } catch (error) {
        console.error('Failed to load documents:', error);
      } finally {
        setLoading(false);
      }
    };

    loadDocuments();
  }, [typeFilter, statusFilter, searchQuery]);

  if (loading) {
    return <SkeletonTable rows={8} />;
  }

  if (documents.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-ink-muted opacity-50" />
          <h3 className="mt-4 text-lg font-semibold text-ink">No documents found</h3>
          <p className="mt-2 text-sm text-ink-muted">
            {searchQuery ? `No documents match your search for "${searchQuery}"` : 'No documents match your filters'}
          </p>
        </CardContent>
      </Card>
    );
  }

  const getStatusConfig = (status: Document['status']) => {
    const configs = {
      active: { variant: 'success' as const, label: 'Active' },
      expiring: { variant: 'warning' as const, label: 'Expiring Soon' },
      expired: { variant: 'error' as const, label: 'Expired' },
      pending: { variant: 'info' as const, label: 'Pending Review' }
    };
    return configs[status];
  };

  const getUrgencyColor = (days: number) => {
    if (days < 0) return 'text-error';
    if (days <= 7) return 'text-error';
    if (days <= 30) return 'text-warning';
    return 'text-success';
  };

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Document Name</TableHead>
                <TableHead>Vendor</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Issue Date</TableHead>
                <TableHead>Expiry Date</TableHead>
                <TableHead className="text-right">Days Until Expiry</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {documents.map((doc) => {
                const statusConfig = getStatusConfig(doc.status);
                const urgencyColor = getUrgencyColor(doc.daysUntilExpiry);

                return (
                  <TableRow key={doc.id} className="hover:bg-surface-sunken transition-colors">
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-brand" />
                        {doc.name}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Link
                        href={`/en/vendors/${doc.vendorId}`}
                        className="text-brand hover:underline"
                      >
                        {doc.vendorName}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" size="sm" className="capitalize">
                        {doc.type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusConfig.variant} size="sm">
                        {statusConfig.label}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-ink-muted">
                      {new Date(doc.issueDate).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-sm text-ink-muted">
                      {new Date(doc.expiryDate).toLocaleDateString()}
                    </TableCell>
                    <TableCell className={`text-right font-medium ${urgencyColor}`}>
                      {doc.daysUntilExpiry < 0 ? (
                        <span>Expired {Math.abs(doc.daysUntilExpiry)} days ago</span>
                      ) : (
                        <span>{doc.daysUntilExpiry} days</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          className="p-1 hover:bg-surface-sunken rounded transition-colors"
                          title="Download"
                        >
                          <Download className="h-4 w-4 text-ink-muted" />
                        </button>
                        <button
                          className="p-1 hover:bg-surface-sunken rounded transition-colors"
                          title="View Details"
                        >
                          <ExternalLink className="h-4 w-4 text-ink-muted" />
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
};
