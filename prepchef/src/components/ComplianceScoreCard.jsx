import React, { useMemo } from 'react';
import { Shield, AlertTriangle, CheckCircle, Clock, MapPin } from 'lucide-react';

const COMPLIANCE_ICON_MAP = {
  compliant: { icon: CheckCircle, className: 'text-green-500' },
  partial_compliance: { icon: Clock, className: 'text-yellow-500' },
  non_compliant: { icon: AlertTriangle, className: 'text-red-500' },
};

const formatDate = (value) => {
  if (!value) {
    return null;
  }

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

const formatPlanState = (state) => {
  if (!state) {
    return 'Trial Plan';
  }

  const normalized = state.toString().trim().toLowerCase();

  if (normalized === 'paid') {
    return 'Paid Plan';
  }

  if (normalized === 'trial') {
    return 'Trial Plan';
  }

  const label = normalized.replace(/_/g, ' ');
  const capitalized = label
    .split(' ')
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ');

  return `${capitalized || 'Custom'} Plan`;
};

const ComplianceScoreCard = ({
  complianceLevel,
  location,
  riskScore,
  planState,
  pilotMode,
  pilotDeadline,
  onOverride,
  overrideLoading = false,
}) => {
  const { icon: StatusIcon, className: statusClassName } = useMemo(() => {
    return COMPLIANCE_ICON_MAP[complianceLevel] || {
      icon: Shield,
      className: 'text-gray-500',
    };
  }, [complianceLevel]);

  const formattedPlanState = formatPlanState(planState);
  const formattedPilotDeadline = formatDate(pilotDeadline);

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start space-x-4">
          <StatusIcon className={statusClassName} size={28} />
          <div>
            <h2 className="text-xl font-semibold">Compliance Status</h2>
            {location && (
              <p className="text-gray-600 flex items-center mt-1">
                <MapPin size={16} className="mr-1" />
                {location}
              </p>
            )}
            <div className="mt-2 text-sm text-gray-500">
              Plan Status: <span className="font-medium text-gray-700">{formattedPlanState}</span>
            </div>
            {pilotMode ? (
              <div className="mt-2 text-sm text-amber-600">
                Pilot access active{formattedPilotDeadline ? ` • Ends ${formattedPilotDeadline}` : ''}
              </div>
            ) : (
              <div className="mt-2 text-sm text-gray-500">Pilot mode disabled</div>
            )}
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">{riskScore != null ? `${riskScore}/100` : '—'}</div>
          <div className="text-sm text-gray-500">Risk Score</div>
          {pilotMode && onOverride && (
            <button
              type="button"
              onClick={onOverride}
              disabled={overrideLoading}
              className="mt-4 inline-flex items-center justify-center rounded-md border border-amber-500 px-4 py-2 text-sm font-medium text-amber-700 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:border-amber-200 disabled:text-amber-300"
            >
              {overrideLoading ? 'Submitting override…' : 'Override Pilot Hold'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ComplianceScoreCard;
