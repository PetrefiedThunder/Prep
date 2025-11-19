'use client';

import { AlertCircle, AlertTriangle, Info } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent, Badge } from '@/components/ui';
import { cn } from '@/lib/utils';

interface ComplianceAlert {
  id: string;
  title: string;
  description: string;
  severity: 'high' | 'medium' | 'low';
  timestamp: string;
}

const severityConfig = {
  high: {
    icon: <AlertCircle className="h-4 w-4" />,
    variant: 'error' as const,
    label: 'High Priority'
  },
  medium: {
    icon: <AlertTriangle className="h-4 w-4" />,
    variant: 'warning' as const,
    label: 'Medium Priority'
  },
  low: {
    icon: <Info className="h-4 w-4" />,
    variant: 'info' as const,
    label: 'Low Priority'
  }
};

export const ComplianceAlerts = () => {
  // Mock data - replace with real API
  const alerts: ComplianceAlert[] = [
    {
      id: '1',
      title: 'Health Permit Expiring Soon',
      description: 'Kitchen #4527 health permit expires in 7 days',
      severity: 'high',
      timestamp: '2 hours ago'
    },
    {
      id: '2',
      title: 'Insurance Certificate Needed',
      description: 'Vendor "Fresh Ingredients Co." missing liability insurance',
      severity: 'high',
      timestamp: '5 hours ago'
    },
    {
      id: '3',
      title: 'Inspection Scheduled',
      description: 'Health inspection scheduled for downtown location',
      severity: 'medium',
      timestamp: '1 day ago'
    },
    {
      id: '4',
      title: 'Training Certification Due',
      description: '3 staff members need food safety recertification',
      severity: 'medium',
      timestamp: '2 days ago'
    }
  ];

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Compliance Alerts</CardTitle>
          <Badge variant="error" size="sm">
            {alerts.filter((a) => a.severity === 'high').length} High Priority
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {alerts.map((alert) => {
            const config = severityConfig[alert.severity];
            return (
              <div
                key={alert.id}
                className={cn(
                  'flex gap-3 rounded-lg border p-3 transition-colors duration-fast',
                  'hover:bg-surface-sunken cursor-pointer',
                  alert.severity === 'high' && 'border-error/20 bg-error-light/50',
                  alert.severity === 'medium' && 'border-warning/20 bg-warning-light/50',
                  alert.severity === 'low' && 'border-info/20 bg-info-light/50'
                )}
              >
                <div className="flex-shrink-0 pt-0.5">{config.icon}</div>
                <div className="flex-1 space-y-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="font-medium text-sm text-ink">{alert.title}</p>
                    <span className="text-xs text-ink-muted whitespace-nowrap">
                      {alert.timestamp}
                    </span>
                  </div>
                  <p className="text-sm text-ink-muted">{alert.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};
