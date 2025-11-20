'use client';

import { Card, CardContent, Badge } from '@/components/ui';
import { Search } from 'lucide-react';

interface DocumentsFiltersProps {
  typeFilter: string;
  statusFilter: string;
  onTypeFilterChange: (type: string) => void;
  onStatusFilterChange: (status: string) => void;
  searchQuery: string;
  onSearchQueryChange: (query: string) => void;
}

export const DocumentsFilters = ({
  typeFilter,
  statusFilter,
  onTypeFilterChange,
  onStatusFilterChange,
  searchQuery,
  onSearchQueryChange
}: DocumentsFiltersProps) => {
  const types = [
    { value: 'all', label: 'All Types' },
    { value: 'permit', label: 'Permits' },
    { value: 'insurance', label: 'Insurance' },
    { value: 'certification', label: 'Certifications' },
    { value: 'inspection', label: 'Inspections' },
    { value: 'license', label: 'Licenses' }
  ];

  const statuses = [
    { value: 'all', label: 'All Status', count: 45 },
    { value: 'active', label: 'Active', count: 28 },
    { value: 'expiring', label: 'Expiring', count: 14 },
    { value: 'expired', label: 'Expired', count: 3 }
  ];

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Search */}
          <div className="relative max-w-md">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              type="text"
              placeholder="Search documents by name or vendor..."
              value={searchQuery}
              onChange={(e) => onSearchQueryChange(e.target.value)}
              className="w-full rounded-lg border border-border bg-surface pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
            />
          </div>

          {/* Filters Row */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            {/* Type Filter */}
            <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
              {types.map((type) => (
                <button
                  key={type.value}
                  onClick={() => onTypeFilterChange(type.value)}
                  className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors whitespace-nowrap ${
                    typeFilter === type.value
                      ? 'bg-brand text-white'
                      : 'bg-surface border border-border text-ink-muted hover:bg-surface-elevated'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>

            {/* Status Filter */}
            <div className="flex gap-2 overflow-x-auto pb-2 sm:pb-0">
              {statuses.map((status) => (
                <button
                  key={status.value}
                  onClick={() => onStatusFilterChange(status.value)}
                  className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors whitespace-nowrap ${
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
        </div>
      </CardContent>
    </Card>
  );
};
