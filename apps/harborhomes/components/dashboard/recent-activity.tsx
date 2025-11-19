'use client';

import { CheckCircle, XCircle, Clock, FileCheck } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  Badge
} from '@/components/ui';

interface Activity {
  id: string;
  type: 'verification' | 'expiry' | 'renewal' | 'violation';
  vendor: string;
  action: string;
  status: 'completed' | 'pending' | 'failed';
  timestamp: string;
}

const statusConfig = {
  completed: {
    icon: <CheckCircle className="h-4 w-4" />,
    variant: 'success' as const,
    label: 'Completed'
  },
  pending: {
    icon: <Clock className="h-4 w-4" />,
    variant: 'warning' as const,
    label: 'Pending'
  },
  failed: {
    icon: <XCircle className="h-4 w-4" />,
    variant: 'error' as const,
    label: 'Failed'
  }
};

export const RecentActivity = () => {
  // Mock data - replace with real API
  const activities: Activity[] = [
    {
      id: '1',
      type: 'verification',
      vendor: 'Fresh Ingredients Co.',
      action: 'Insurance verification completed',
      status: 'completed',
      timestamp: '10 minutes ago'
    },
    {
      id: '2',
      type: 'renewal',
      vendor: 'Kitchen #4527',
      action: 'Health permit renewed',
      status: 'completed',
      timestamp: '1 hour ago'
    },
    {
      id: '3',
      type: 'verification',
      vendor: 'Quality Supplies Inc.',
      action: 'Document verification in progress',
      status: 'pending',
      timestamp: '2 hours ago'
    },
    {
      id: '4',
      type: 'expiry',
      vendor: 'Downtown Location',
      action: 'Fire safety certificate expired',
      status: 'failed',
      timestamp: '3 hours ago'
    },
    {
      id: '5',
      type: 'verification',
      vendor: 'Organic Foods Ltd.',
      action: 'FDA certification verified',
      status: 'completed',
      timestamp: '5 hours ago'
    }
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Vendor/Location</TableHead>
              <TableHead>Action</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {activities.map((activity) => {
              const config = statusConfig[activity.status];
              return (
                <TableRow key={activity.id}>
                  <TableCell className="font-medium">{activity.vendor}</TableCell>
                  <TableCell className="text-ink-muted">{activity.action}</TableCell>
                  <TableCell>
                    <Badge variant={config.variant} size="sm">
                      {config.label}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right text-sm text-ink-muted">
                    {activity.timestamp}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};
