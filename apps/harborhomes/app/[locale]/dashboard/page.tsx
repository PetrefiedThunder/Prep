import { PageHeader } from '@/components/layout/page-header';
import { DashboardMetrics } from '@/components/dashboard/dashboard-metrics';
import { ComplianceAlerts } from '@/components/dashboard/compliance-alerts';
import { RecentActivity } from '@/components/dashboard/recent-activity';
import { ExpiringDocuments } from '@/components/dashboard/expiring-documents';
import { VendorStatusChart } from '@/components/dashboard/vendor-status-chart';
import { ComplianceTrendChart } from '@/components/dashboard/compliance-trend-chart';

export const metadata = {
  title: 'Control Center – PrepChef',
  description: 'Monitor compliance, track vendors, and manage your commercial kitchen operations'
};

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <PageHeader
        title="Control Center"
        description="Monitor compliance status and manage operations across all locations"
      />

      {/* Key Metrics Grid */}
      <DashboardMetrics />

      {/* Compliance Trend Chart */}
      <ComplianceTrendChart />

      {/* Main Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        <ComplianceAlerts />
        <ExpiringDocuments />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <RecentActivity />
        </div>
        <div>
          <VendorStatusChart />
        </div>
      </div>
    </div>
  );
}
