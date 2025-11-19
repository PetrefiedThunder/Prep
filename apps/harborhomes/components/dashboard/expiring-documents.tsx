'use client';

import { FileText, Calendar } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui';
import { cn } from '@/lib/utils';

interface ExpiringDocument {
  id: string;
  name: string;
  vendor: string;
  daysUntilExpiry: number;
  type: string;
}

export const ExpiringDocuments = () => {
  // Mock data - replace with real API
  const documents: ExpiringDocument[] = [
    {
      id: '1',
      name: 'Health Permit',
      vendor: 'Kitchen #4527',
      daysUntilExpiry: 7,
      type: 'Permit'
    },
    {
      id: '2',
      name: 'Liability Insurance',
      vendor: 'Downtown Location',
      daysUntilExpiry: 14,
      type: 'Insurance'
    },
    {
      id: '3',
      name: 'Food Handler Certificate',
      vendor: 'John Smith',
      daysUntilExpiry: 21,
      type: 'Certification'
    },
    {
      id: '4',
      name: 'Fire Safety Inspection',
      vendor: 'Kitchen #3891',
      daysUntilExpiry: 28,
      type: 'Inspection'
    }
  ];

  const getUrgencyBadge = (days: number) => {
    if (days <= 7) return <Badge variant="error" size="sm">{days} days</Badge>;
    if (days <= 14) return <Badge variant="warning" size="sm">{days} days</Badge>;
    return <Badge variant="info" size="sm">{days} days</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Expiring Documents</CardTitle>
          <Badge variant="warning" size="sm">
            {documents.filter((d) => d.daysUntilExpiry <= 30).length} This Month
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className={cn(
                'flex items-center gap-3 rounded-lg border border-border p-3',
                'hover:bg-surface-sunken transition-colors duration-fast cursor-pointer'
              )}
            >
              <div className="flex-shrink-0">
                <div className="rounded-lg bg-brand/10 p-2 text-brand">
                  <FileText className="h-4 w-4" />
                </div>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-sm text-ink truncate">{doc.name}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-ink-muted">{doc.vendor}</span>
                  <span className="text-xs text-ink-subtle">•</span>
                  <span className="text-xs text-ink-muted">{doc.type}</span>
                </div>
              </div>
              <div className="flex-shrink-0 flex items-center gap-2">
                <Calendar className="h-3.5 w-3.5 text-ink-muted" />
                {getUrgencyBadge(doc.daysUntilExpiry)}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};
