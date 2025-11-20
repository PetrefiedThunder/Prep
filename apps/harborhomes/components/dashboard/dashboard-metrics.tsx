'use client';

import * as React from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, CheckCircle, AlertTriangle, Users, FileCheck } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { staggerContainer, staggerItem } from '@/lib/animations';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: {
    value: number;
    label: string;
    positive?: boolean;
  };
  icon: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

const MetricCard = ({ title, value, change, icon, variant = 'default' }: MetricCardProps) => {
  const variantClasses = {
    default: 'bg-brand/10 text-brand',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-error/10 text-error'
  };

  return (
    <motion.div variants={staggerItem}>
      <Card className="overflow-hidden">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-ink-muted">{title}</CardTitle>
            <div className={cn('rounded-lg p-2', variantClasses[variant])}>{icon}</div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-1">
            <p className="text-3xl font-bold text-ink">{value}</p>
            {change && (
              <div className="flex items-center gap-1 text-sm">
                {change.positive ? (
                  <TrendingUp className="h-4 w-4 text-success" />
                ) : (
                  <TrendingDown className="h-4 w-4 text-error" />
                )}
                <span
                  className={cn(
                    'font-medium',
                    change.positive ? 'text-success' : 'text-error'
                  )}
                >
                  {change.value > 0 ? '+' : ''}
                  {change.value}%
                </span>
                <span className="text-ink-muted">{change.label}</span>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
};

export const DashboardMetrics = () => {
  const [metrics, setMetrics] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const loadMetrics = async () => {
      try {
        const { mockApi } = await import('@/lib/api/mock-api');
        const data = await mockApi.dashboard.getMetrics();

        setMetrics([
          {
            title: 'Active Vendors',
            value: data.activeVendors.value,
            change: {
              value: data.activeVendors.change,
              label: data.activeVendors.changeLabel,
              positive: data.activeVendors.change > 0
            },
            icon: <Users className="h-5 w-5" />,
            variant: 'default' as const
          },
          {
            title: 'Compliance Rate',
            value: `${data.complianceRate.value}%`,
            change: {
              value: data.complianceRate.change,
              label: data.complianceRate.changeLabel,
              positive: data.complianceRate.change > 0
            },
            icon: <CheckCircle className="h-5 w-5" />,
            variant: 'success' as const
          },
          {
            title: 'Documents Expiring',
            value: data.documentsExpiring.value,
            change: {
              value: data.documentsExpiring.change,
              label: data.documentsExpiring.changeLabel,
              positive: data.documentsExpiring.change < 0
            },
            icon: <AlertTriangle className="h-5 w-5" />,
            variant: 'warning' as const
          },
          {
            title: 'Verifications Pending',
            value: data.verificationsPending.value,
            change: {
              value: data.verificationsPending.change,
              label: data.verificationsPending.changeLabel,
              positive: data.verificationsPending.change < 0
            },
            icon: <FileCheck className="h-5 w-5" />,
            variant: 'default' as const
          }
        ]);
      } catch (error) {
        console.error('Failed to load metrics:', error);
      } finally {
        setLoading(false);
      }
    };

    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="overflow-hidden">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="h-4 w-32 animate-pulse rounded bg-border/40" />
                <div className="h-10 w-10 animate-pulse rounded-lg bg-border/40" />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="h-9 w-20 animate-pulse rounded bg-border/40" />
                <div className="h-5 w-40 animate-pulse rounded bg-border/40" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <motion.div
      className="grid gap-4 md:grid-cols-2 lg:grid-cols-4"
      initial="initial"
      animate="animate"
      variants={staggerContainer}
    >
      {metrics.map((metric, index) => (
        <MetricCard key={index} {...metric} />
      ))}
    </motion.div>
  );
};
