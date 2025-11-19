'use client';

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
  // Mock data - replace with real API calls
  const metrics = [
    {
      title: 'Active Vendors',
      value: 247,
      change: { value: 12, label: 'vs last month', positive: true },
      icon: <Users className="h-5 w-5" />,
      variant: 'default' as const
    },
    {
      title: 'Compliance Rate',
      value: '94.2%',
      change: { value: 2.1, label: 'from last week', positive: true },
      icon: <CheckCircle className="h-5 w-5" />,
      variant: 'success' as const
    },
    {
      title: 'Documents Expiring',
      value: 18,
      change: { value: -5, label: 'vs last month', positive: true },
      icon: <AlertTriangle className="h-5 w-5" />,
      variant: 'warning' as const
    },
    {
      title: 'Verifications Pending',
      value: 7,
      change: { value: -3, label: 'vs yesterday', positive: true },
      icon: <FileCheck className="h-5 w-5" />,
      variant: 'default' as const
    }
  ];

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
