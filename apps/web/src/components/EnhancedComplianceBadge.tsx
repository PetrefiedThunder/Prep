import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Award,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  Clock,
  Shield,
  TrendingUp,
  XCircle,
} from 'lucide-react';

interface EnhancedComplianceBadgeProps {
  kitchenId: string;
  compact?: boolean;
  showTrend?: boolean;
}

interface BadgeResponse {
  badge_level: string;
  score: number;
  last_verified?: string;
  highlights?: string[];
  concerns?: string[];
  can_accept_bookings?: boolean;
}

interface TrendResponse {
  trend: number;
}

interface InspectionSummary {
  date: string;
  score: number;
  violation_count: number;
  critical_violations: number;
  source?: string;
}

interface InspectionHistoryResponse {
  inspections: InspectionSummary[];
}

const defaultBadge: BadgeResponse = {
  badge_level: 'needs_improvement',
  score: 0,
  highlights: [],
  concerns: [],
  can_accept_bookings: false,
};

export function EnhancedComplianceBadge({
  kitchenId,
  compact = false,
  showTrend = false,
}: EnhancedComplianceBadgeProps) {
  const [badgeData, setBadgeData] = useState<BadgeResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [expanded, setExpanded] = useState<boolean>(false);
  const [inspectionHistory, setInspectionHistory] = useState<InspectionSummary[]>([]);
  const [trendData, setTrendData] = useState<TrendResponse | null>(null);
  const [historyLoaded, setHistoryLoaded] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchBadge() {
      setLoading(true);
      try {
        const response = await fetch(`/api/compliance/badge/${kitchenId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch badge (${response.status})`);
        }
        const data = (await response.json()) as BadgeResponse;
        if (!cancelled) {
          setBadgeData({ ...defaultBadge, ...data });
        }
      } catch (error) {
        console.error('Error fetching compliance badge:', error);
        if (!cancelled) {
          setBadgeData(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    async function fetchTrend() {
      if (!showTrend) return;
      try {
        const response = await fetch(`/api/compliance/trend/${kitchenId}`);
        if (!response.ok) {
          throw new Error(`Failed to fetch trend (${response.status})`);
        }
        const data = (await response.json()) as TrendResponse;
        if (!cancelled) {
          setTrendData(data);
        }
      } catch (error) {
        console.error('Error fetching trend data:', error);
        if (!cancelled) {
          setTrendData(null);
        }
      }
    }

    fetchBadge();
    fetchTrend();

    return () => {
      cancelled = true;
    };
  }, [kitchenId, showTrend]);

  const toggleInspectionHistory = async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }

    if (historyLoaded) {
      setExpanded(true);
      return;
    }

    try {
      const response = await fetch(`/api/compliance/inspection-history/${kitchenId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch inspection history (${response.status})`);
      }
      const data = (await response.json()) as InspectionHistoryResponse;
      setInspectionHistory(data.inspections ?? []);
      setHistoryLoaded(true);
      setExpanded(true);
    } catch (error) {
      console.error('Error fetching inspection history:', error);
    }
  };

  if (loading) {
    return (
      <div className="animate-pulse flex items-center gap-3 p-4 bg-gray-100 rounded-lg">
        <div className="w-12 h-12 bg-gray-300 rounded-full" />
        <div className="flex-1">
          <div className="h-4 bg-gray-300 rounded w-3/4 mb-2" />
          <div className="h-3 bg-gray-300 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (!badgeData) {
    return (
      <div className="flex items-center gap-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <AlertTriangle className="text-yellow-600 w-5 h-5" />
        <span className="text-sm text-yellow-800">Compliance data unavailable</span>
      </div>
    );
  }

  const badge = { ...defaultBadge, ...badgeData };

  const getBadgeColor = () => {
    switch (badge.badge_level) {
      case 'gold':
        return 'bg-yellow-100 border-yellow-400 text-yellow-800';
      case 'silver':
        return 'bg-gray-100 border-gray-400 text-gray-800';
      case 'bronze':
        return 'bg-orange-100 border-orange-400 text-orange-800';
      default:
        return 'bg-red-100 border-red-400 text-red-800';
    }
  };

  const getBadgeIcon = () => {
    if (badge.score >= 95) return <Award className="w-6 h-6 text-yellow-600" />;
    if (badge.score >= 90) return <CheckCircle className="w-6 h-6 text-green-600" />;
    if (badge.score >= 70) return <Shield className="w-6 h-6 text-blue-600" />;
    return <AlertTriangle className="w-6 h-6 text-red-600" />;
  };

  const getScoreColor = () => {
    if (badge.score >= 95) return 'text-yellow-700 bg-yellow-50 border-yellow-200';
    if (badge.score >= 90) return 'text-green-700 bg-green-50 border-green-200';
    if (badge.score >= 80) return 'text-blue-700 bg-blue-50 border-blue-200';
    if (badge.score >= 70) return 'text-orange-700 bg-orange-50 border-orange-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  const getTrendIcon = () => {
    if (!trendData) return null;
    if (trendData.trend > 5) return <TrendingUp className="w-4 h-4 text-green-600" />;
    if (trendData.trend < -5) return <TrendingUp className="w-4 h-4 text-red-600 rotate-180" />;
    return <Clock className="w-4 h-4 text-gray-500" />;
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {getBadgeIcon()}
        <div className="text-sm">
          <span className="font-semibold">{Math.round(badge.score)}/100</span>
          <span className="text-gray-600 ml-1">Health Score</span>
          {showTrend && trendData && (
            <span className="ml-2 inline-flex items-center text-xs">
              {getTrendIcon()}
              <span className="ml-1">{trendData.trend > 0 ? '+' : ''}{trendData.trend}%</span>
            </span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden shadow-sm">
      <div className={`p-4 border-b ${getBadgeColor()}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getBadgeIcon()}
            <div>
              <h3 className="font-bold text-lg">Health &amp; Safety Verified</h3>
              <p className="text-sm opacity-90">
                Last verified{' '}
                {badge.last_verified
                  ? new Date(badge.last_verified).toLocaleDateString()
                  : 'N/A'}
              </p>
            </div>
          </div>

          <div className={`px-4 py-2 rounded-lg font-bold text-2xl border ${getScoreColor()}`}>
            {Math.round(badge.score)}/100
          </div>
        </div>
      </div>

      {showTrend && trendData && (
        <div className="px-4 py-3 bg-gray-50 border-b">
          <div className="flex items-center gap-2">
            {getTrendIcon()}
            <span className="text-sm font-medium">
              {trendData.trend > 5
                ? 'Improving'
                : trendData.trend < -5
                ? 'Declining'
                : 'Stable'}
            </span>
            <span className="text-sm text-gray-600">
              ({trendData.trend > 0 ? '+' : ''}{trendData.trend}% in 30 days)
            </span>
          </div>
        </div>
      )}

      <div className="p-4 bg-white">
        {badge.can_accept_bookings ? (
          <div className="flex items-center gap-2 text-green-700">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">Approved for bookings</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-red-700">
            <XCircle className="w-5 h-5" />
            <span className="font-medium">Currently unavailable - compliance issues</span>
          </div>
        )}
      </div>

      {badge.highlights && badge.highlights.length > 0 && (
        <div className="px-4 pb-4">
          <h4 className="font-semibold text-sm text-gray-700 mb-2">Safety Highlights</h4>
          <ul className="space-y-1">
            {badge.highlights.map((highlight, idx) => (
              <li key={`${highlight}-${idx}`} className="flex items-start gap-2 text-sm text-gray-700">
                <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                <span>{highlight}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {badge.concerns && badge.concerns.length > 0 && (
        <div className="px-4 pb-4">
          <h4 className="font-semibold text-sm text-gray-700 mb-2">Areas for Improvement</h4>
          <ul className="space-y-1">
            {badge.concerns.map((concern, idx) => (
              <li key={`${concern}-${idx}`} className="flex items-start gap-2 text-sm text-gray-700">
                <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                <span>{concern}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-4 pb-4">
        <button
          type="button"
          onClick={toggleInspectionHistory}
          className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-medium text-sm"
        >
          <span>View Full Inspection History</span>
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>

        {expanded && inspectionHistory.length > 0 && (
          <div className="mt-4 space-y-3">
            {inspectionHistory.map(inspection => (
              <div key={inspection.date} className="border border-gray-200 rounded-lg p-3">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <div className="font-semibold text-sm">
                      {new Date(inspection.date).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })}
                    </div>
                    <div className="text-xs text-gray-600">
                      Source: {inspection.source === 'county_api' ? 'County Health Dept' : 'Manual Upload'}
                    </div>
                  </div>

                  <div
                    className={`px-3 py-1 rounded-full font-bold text-sm border ${(() => {
                      if (inspection.score >= 95)
                        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
                      if (inspection.score >= 90)
                        return 'bg-green-100 text-green-800 border-green-200';
                      if (inspection.score >= 80)
                        return 'bg-blue-100 text-blue-800 border-blue-200';
                      if (inspection.score >= 70)
                        return 'bg-orange-100 text-orange-800 border-orange-200';
                      return 'bg-red-100 text-red-800 border-red-200';
                    })()}`}
                  >
                    {inspection.score}/100
                  </div>
                </div>

                <div className="flex gap-4 text-xs text-gray-600">
                  <span>{inspection.violation_count} total violations</span>
                  {inspection.critical_violations > 0 && (
                    <span className="text-red-600 font-medium">
                      {inspection.critical_violations} critical
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
        <p className="text-xs text-gray-600">
          Compliance data provided by PrepChef Data Intelligence in partnership with county health
          departments. Data is refreshed automatically every 30 days or when new inspections occur.
        </p>
      </div>
    </div>
  );
}

export default EnhancedComplianceBadge;
