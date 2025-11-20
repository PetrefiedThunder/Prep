'use client';

import * as React from 'react';
import { PageHeader } from '@/components/layout/page-header';
import { DocumentsList } from '@/components/documents/documents-list';
import { DocumentsFilters } from '@/components/documents/documents-filters';
import { Button } from '@/components/ui';
import { Upload } from 'lucide-react';

export default function DocumentsPage() {
  const [typeFilter, setTypeFilter] = React.useState<string>('all');
  const [statusFilter, setStatusFilter] = React.useState<string>('all');
  const [searchQuery, setSearchQuery] = React.useState('');

  return (
    <div className="space-y-6">
      <PageHeader
        title="Document Management"
        description="Track and manage all compliance documents across vendors"
        actions={
          <Button>
            <Upload className="h-4 w-4 mr-2" />
            Upload Document
          </Button>
        }
      />

      <DocumentsFilters
        typeFilter={typeFilter}
        statusFilter={statusFilter}
        onTypeFilterChange={setTypeFilter}
        onStatusFilterChange={setStatusFilter}
        searchQuery={searchQuery}
        onSearchQueryChange={setSearchQuery}
      />

      <DocumentsList typeFilter={typeFilter} statusFilter={statusFilter} searchQuery={searchQuery} />
    </div>
  );
}
