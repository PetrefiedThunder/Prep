'use client';

import * as React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { ComplianceTrend } from '@/lib/types/api';

export const ComplianceTrendChart = () => {
  const [data, setData] = React.useState<ComplianceTrend[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const loadData = async () => {
      try {
        const { mockApi } = await import('@/lib/api/mock-api');
        const trends = await mockApi.dashboard.getComplianceTrends();
        setData(trends);
      } catch (error) {
        console.error('Failed to load trends:', error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Compliance Trends (30 Days)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 animate-pulse rounded bg-border/40" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compliance Trends (30 Days)</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={320}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="date"
              stroke="hsl(var(--ink-muted))"
              fontSize={12}
              tickFormatter={(value) => {
                const date = new Date(value);
                return `${date.getMonth() + 1}/${date.getDate()}`;
              }}
            />
            <YAxis
              stroke="hsl(var(--ink-muted))"
              fontSize={12}
              domain={[85, 100]}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'hsl(var(--surface-elevated))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                padding: '8px 12px'
              }}
              labelFormatter={(value) => {
                const date = new Date(value as string);
                return date.toLocaleDateString();
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, 'Compliance Rate']}
            />
            <Line
              type="monotone"
              dataKey="rate"
              stroke="hsl(var(--brand))"
              strokeWidth={2}
              dot={{ fill: 'hsl(var(--brand))', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
        <div className="mt-4 flex items-center justify-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="h-3 w-3 rounded-full bg-brand" />
            <span className="text-ink-muted">Compliance Rate</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
