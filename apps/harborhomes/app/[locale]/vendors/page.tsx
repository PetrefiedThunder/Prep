'use client';

import * as React from 'react';
import { PageHeader } from '@/components/layout/page-header';
import { VendorsList } from '@/components/vendors/vendors-list';
import { VendorsFilters } from '@/components/vendors/vendors-filter';
import { Button } from '@/components/ui';
import { Plus } from 'lucide-react';

export default function VendorsPage() {
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [searchQuery, setSearchQuery] = React.useState('');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Vendor Management"
        description="Monitor and manage all vendor compliance and certifications"
        actions={
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Vendor
          </Button>
        }
      />

      <VendorsFilters
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
      />

      <VendorsList statusFilter={statusFilter} searchQuery={searchQuery} />
    </div>
  );
}
