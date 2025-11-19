'use client';

import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { cn } from '@/lib/utils';

interface VendorStatus {
  label: string;
  count: number;
  percentage: number;
  color: string;
}

export const VendorStatusChart = () => {
  // Mock data - replace with real API
  const statuses: VendorStatus[] = [
    { label: 'Verified', count: 232, percentage: 94, color: 'bg-success' },
    { label: 'Pending', count: 12, percentage: 5, color: 'bg-warning' },
    { label: 'Expired', count: 3, percentage: 1, color: 'bg-error' }
  ];

  const total = statuses.reduce((sum, status) => sum + status.count, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Vendor Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Progress Bar */}
          <div>
            <div className="mb-4 flex justify-between text-sm">
              <span className="font-medium text-ink">Total Vendors</span>
              <span className="font-bold text-ink">{total}</span>
            </div>
            <div className="flex h-3 overflow-hidden rounded-full bg-surface-sunken">
              {statuses.map((status, index) => (
                <div
                  key={index}
                  className={cn('transition-all duration-slow', status.color)}
                  style={{ width: `${status.percentage}%` }}
                  title={`${status.label}: ${status.count} (${status.percentage}%)`}
                />
              ))}
            </div>
          </div>

          {/* Status Breakdown */}
          <div className="space-y-3">
            {statuses.map((status, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={cn('h-3 w-3 rounded-full', status.color)} />
                  <span className="text-sm text-ink-muted">{status.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-medium text-ink">{status.count}</span>
                  <span className="text-sm text-ink-subtle w-12 text-right">
                    {status.percentage}%
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Summary */}
          <div className="rounded-lg border border-success/20 bg-success-light/50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-success-dark">Compliance Rate</span>
              <span className="text-lg font-bold text-success-dark">
                {statuses[0].percentage}%
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
