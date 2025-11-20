'use client';

import { Card, CardContent, Badge } from '@/components/ui';
import { Search } from 'lucide-react';

interface VendorsFiltersProps {
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
}

export const VendorsFilters = ({
  statusFilter,
  onStatusFilterChange,
  searchQuery,
  onSearchQueryChange
}: VendorsFiltersProps) => {
  const statuses = [
    { value: 'all', label: 'All Vendors', count: 247 },
    { value: 'verified', label: 'Verified', count: 232 },
    { value: 'pending', label: 'Pending', count: 12 },
    { value: 'expired', label: 'Expired', count: 3 }
  ];

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              type="text"
              placeholder="Search vendors by name, email, or category..."
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          {/* Status Filters */}
          <div className="flex gap-2 overflow-x-auto pb-2 md:pb-0">
            {statuses.map((status) => (
              <button
                key={status.value}
                onClick={() => onStatusFilterChange(status.value)}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                  statusFilter === status.value
                    ? 'bg-brand text-white'
                    : 'bg-surface border border-border text-ink-muted hover:bg-surface-elevated'
                }`}
              >
                {status.label}
                <Badge
                  variant={statusFilter === status.value ? 'default' : 'outline'}
                  size="sm"
                  className={statusFilter === status.value ? 'bg-white/20 text-white border-white/30' : ''}
                >
                  {status.count}
                </Badge>
              </button>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
