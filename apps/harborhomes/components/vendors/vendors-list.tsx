'use client';

import * as React from 'react';
import Link from 'next/link';
import { motion } from 'framer-motion';
import { Card, CardHeader, CardTitle, CardContent, Badge, SkeletonCard } from '@/components/ui';
import { Building2, Mail, Phone, MapPin, FileText, TrendingUp } from 'lucide-react';
import { staggerContainer, staggerItem } from '@/lib/animations';
import type { Vendor } from '@/lib/types/api';

interface VendorsListProps {
  statusFilter: string;
  searchQuery: string;
}

const VendorCard = ({ vendor }: { vendor: Vendor }) => {
  const statusConfig = {
    verified: { variant: 'success' as const, label: 'Verified' },
    pending: { variant: 'warning' as const, label: 'Pending Review' },
    expired: { variant: 'error' as const, label: 'Expired' },
    suspended: { variant: 'error' as const, label: 'Suspended' }
  };

  const config = statusConfig[vendor.status];

  return (
    <motion.div variants={staggerItem}>
      <Link href={`/en/vendors/${vendor.id}`}>
        <Card hoverable className="h-full transition-all duration-base">
          <CardHeader>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-brand/10 p-2 text-brand">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">{vendor.name}</CardTitle>
                  <Badge variant={config.variant} size="sm" className="mt-2">
                    {config.label}
                  </Badge>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-brand">{vendor.complianceScore}%</div>
                <div className="text-xs text-ink-muted">Compliance</div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-ink-muted">
                <Mail className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">{vendor.email}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-ink-muted">
                <Phone className="h-4 w-4 flex-shrink-0" />
                <span>{vendor.phone}</span>
              </div>
              <div className="flex items-center gap-2 text-sm text-ink-muted">
                <MapPin className="h-4 w-4 flex-shrink-0" />
                <span className="truncate">
                  {vendor.address.city}, {vendor.address.state}
                </span>
              </div>
              <div className="flex items-center gap-2 text-sm text-ink-muted">
                <FileText className="h-4 w-4 flex-shrink-0" />
                <span>{vendor.documentsCount} Documents</span>
              </div>

              {vendor.categories.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {vendor.categories.map((category, index) => (
                    <Badge key={index} variant="outline" size="sm">
                      {category}
                    </Badge>
                  ))}
                </div>
              )}

              <div className="mt-4 pt-3 border-t border-border text-xs text-ink-muted">
                Last verified: {new Date(vendor.lastVerified).toLocaleDateString()}
              </div>
            </div>
          </CardContent>
        </Card>
      </Link>
    </motion.div>
  );
};

export const VendorsList = ({ statusFilter, searchQuery }: VendorsListProps) => {
  const [vendors, setVendors] = React.useState<Vendor[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const loadVendors = async () => {
      setLoading(true);
      try {
        const { mockApi } = await import('@/lib/api/mock-api');
        let data = await mockApi.vendors.list();

        // Apply status filter
        if (statusFilter !== 'all') {
          data = data.filter((v) => v.status === statusFilter);
        }

        // Apply search filter
        if (searchQuery) {
          const query = searchQuery.toLowerCase();
          data = data.filter(
            (v) =>
              v.name.toLowerCase().includes(query) ||
              v.email.toLowerCase().includes(query) ||
              v.categories.some((c) => c.toLowerCase().includes(query))
          );
        }

        setVendors(data);
      } catch (error) {
        console.error('Failed to load vendors:', error);
      } finally {
        setLoading(false);
      }
    };

    loadVendors();
  }, [statusFilter, searchQuery]);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (vendors.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <Building2 className="mx-auto h-12 w-12 text-ink-muted opacity-50" />
          <h3 className="mt-4 text-lg font-semibold text-ink">No vendors found</h3>
          <p className="mt-2 text-sm text-ink-muted">
            {searchQuery
              ? `No vendors match your search for "${searchQuery}"`
              : `No vendors with status "${statusFilter}"`}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <motion.div
      className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
      initial="initial"
      animate="animate"
      variants={staggerContainer}
    >
      {vendors.map((vendor) => (
        <VendorCard key={vendor.id} vendor={vendor} />
      ))}
    </motion.div>
  );
};
