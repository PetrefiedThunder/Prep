import React, { useState, useEffect, useCallback } from 'react';
import { X, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import ComplianceScoreCard from './ComplianceScoreCard';

const ComplianceDashboard = ({ kitchenId }) => {
  const { token } = useAuth();
  const [complianceData, setComplianceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regulations, setRegulations] = useState([]);
  const [regulationsLoading, setRegulationsLoading] = useState(false);
  const [overrideLoading, setOverrideLoading] = useState(false);
  const [toasts, setToasts] = useState([]);

  useEffect(() => {
    if (!kitchenId) {
      return;
    }

    const fetchCompliance = async () => {
      setLoading(true);
      try {
        const response = await api.get(`/kitchens/${kitchenId}/compliance`, token);
        setComplianceData(response);
      } catch (error) {
        console.error('Failed to load compliance data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCompliance();
  }, [kitchenId, token]);

  useEffect(() => {
    if (!complianceData?.state) {
      return;
    }

    const fetchRegulations = async () => {
      setRegulationsLoading(true);
      try {
        const cityQuery = complianceData.city ? `?city=${encodeURIComponent(complianceData.city)}` : '';
        const response = await api.get(`/regulatory/regulations/${complianceData.state}${cityQuery}`, token);
        setRegulations(response.regulations || []);
      } catch (error) {
        console.error('Failed to load regulations:', error);
      } finally {
        setRegulationsLoading(false);
      }
    };

    fetchRegulations();
  }, [complianceData?.state, complianceData?.city, token]);

  const enqueueToast = useCallback((toast) => {
    setToasts((current) => [
      ...current,
      {
        id: toast.id || `${Date.now()}-${Math.random()}`,
        tone: toast.tone || 'info',
        duration: toast.duration || 6000,
        persist: toast.persist || false,
        ...toast,
      },
    ]);
  }, []);

  useEffect(() => {
    if (!complianceData) {
      setToasts((current) => current.filter((toast) => toast.meta !== 'pilot-deadline'));
      return;
    }

    const pilotDeadline = complianceData.pilot_deadline ? new Date(complianceData.pilot_deadline) : null;

    setToasts((current) => {
      const withoutPilotToasts = current.filter((toast) => toast.meta !== 'pilot-deadline');

      if (!complianceData.pilot_mode || !pilotDeadline || Number.isNaN(pilotDeadline.getTime())) {
        return withoutPilotToasts;
      }

      const now = new Date();
      const timeRemaining = pilotDeadline.getTime() - now.getTime();

      if (timeRemaining <= 0) {
        return withoutPilotToasts;
      }

      const daysRemaining = Math.ceil(timeRemaining / (1000 * 60 * 60 * 24));

      if (daysRemaining > 14) {
        return withoutPilotToasts;
      }

      const tone = daysRemaining <= 3 ? 'danger' : 'warning';
      const title = daysRemaining <= 3 ? 'Pilot access ending' : 'Pilot access expiring soon';
      const message = `Pilot access ends in ${daysRemaining} day${daysRemaining === 1 ? '' : 's'} (${pilotDeadline.toLocaleDateString()}).`;

      return [
        ...withoutPilotToasts,
        {
          id: 'pilot-deadline',
          meta: 'pilot-deadline',
          tone,
          title,
          message,
          persist: true,
        },
      ];
    });
  }, [complianceData]);

  useEffect(() => {
    if (toasts.length === 0) {
      return undefined;
    }

    const timers = toasts
      .filter((toast) => !toast.persist)
      .map((toast) =>
        setTimeout(() => {
          setToasts((current) => current.filter((item) => item.id !== toast.id));
        }, toast.duration)
      );

    return () => {
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [toasts]);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const handlePilotOverride = useCallback(async () => {
    if (!kitchenId) {
      return;
    }

    setOverrideLoading(true);
    try {
      await api.post(`/admin/pilots/${kitchenId}/override`, {}, token);
      enqueueToast({
        tone: 'success',
        title: 'Override submitted',
        message: 'Pilot override request sent to the admin endpoint.',
      });
    } catch (error) {
      console.error('Failed to submit pilot override:', error);
      enqueueToast({
        tone: 'danger',
        title: 'Override failed',
        message: 'Unable to submit pilot override. Please try again later.',
      });
    } finally {
      setOverrideLoading(false);
    }
  }, [enqueueToast, kitchenId, token]);

  if (loading) {
    return <div className="animate-pulse">Loading compliance data...</div>;
  }

  if (!complianceData) {
    return <div className="text-red-600">Unable to load compliance data.</div>;
  }

  return (
    <div className="compliance-dashboard space-y-6">
      <div className="fixed top-4 right-4 z-50 space-y-3">
        {toasts.map((toast) => {
          const toneClasses = {
            info: 'border-blue-400',
            success: 'border-green-400',
            warning: 'border-amber-400',
            danger: 'border-red-500',
          };
          const iconMap = {
            info: <Info size={18} className="text-blue-300" />,
            success: <CheckCircle size={18} className="text-green-300" />,
            warning: <AlertTriangle size={18} className="text-amber-300" />,
            danger: <AlertTriangle size={18} className="text-red-300" />,
          };

          return (
            <div
              key={toast.id}
              className={`flex w-80 items-start space-x-3 rounded-lg border-l-4 ${
                toneClasses[toast.tone] || toneClasses.info
              } bg-gray-900/95 p-4 text-white shadow-xl`}
            >
              <div className="mt-0.5">{iconMap[toast.tone] || iconMap.info}</div>
              <div className="flex-1">
                <div className="text-sm font-semibold">{toast.title}</div>
                <div className="text-sm text-gray-200">{toast.message}</div>
              </div>
              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                className="text-gray-400 transition hover:text-white"
                aria-label="Dismiss notification"
              >
                <X size={16} />
              </button>
            </div>
          );
        })}
      </div>

      {/* Compliance Status Header */}
      <ComplianceScoreCard
        complianceLevel={complianceData?.compliance_level}
        location={complianceData?.city && complianceData?.state ? `${complianceData.city}, ${complianceData.state}` : undefined}
        riskScore={complianceData?.risk_score}
        planState={complianceData?.plan_state}
        pilotMode={Boolean(complianceData?.pilot_mode)}
        pilotDeadline={complianceData?.pilot_deadline}
        onOverride={complianceData?.pilot_mode ? handlePilotOverride : undefined}
        overrideLoading={overrideLoading}
      />

      {complianceData?.pilot_mode && (
        <div className="flex items-start space-x-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <AlertTriangle className="text-amber-500" size={20} />
          <div>
            <h3 className="text-sm font-semibold text-amber-900">Pilot mode limitations</h3>
            <p className="text-sm text-amber-800">
              Your account is currently running in pilot mode. Access may be limited until the pilot ends or is overridden by an
              administrator.
            </p>
          </div>
        </div>
      )}

      {/* Missing Requirements */}
      {complianceData?.missing_requirements?.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-4">Missing Requirements</h3>
          <ul className="space-y-2">
            {complianceData.missing_requirements.map((req, index) => (
              <li key={index} className="flex items-center text-red-700">
                <AlertTriangle size={16} className="mr-2" />
                {req}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {complianceData?.recommendations?.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-blue-800 mb-4">Recommendations</h3>
          <ul className="space-y-2">
            {complianceData.recommendations.map((rec, index) => (
              <li key={index} className="text-blue-700">• {rec}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Applicable Regulations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Applicable Regulations</h3>
        {regulationsLoading && (
          <div className="text-gray-500 text-sm">Loading regulations...</div>
        )}
        <div className="space-y-4">
          {regulations.map((regulation, index) => (
            <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
              <h4 className="font-medium">{regulation.title}</h4>
              <p className="text-sm text-gray-600">{regulation.description}</p>
              <div className="text-xs text-gray-500 mt-1">
                {regulation.jurisdiction} • {regulation.regulation_type}
              </div>
            </div>
          ))}
          {regulations.length === 0 && !regulationsLoading && (
            <p className="text-gray-500 text-sm">No specific regulations found for this location.</p>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex space-x-4">
        <button
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
          onClick={() => window.open('/compliance/upload', '_blank')}
        >
          Upload Compliance Documents
        </button>
        <button
          className="border border-gray-300 px-6 py-2 rounded-lg hover:bg-gray-50"
          onClick={() => window.open('/regulatory/guide', '_blank')}
        >
          View Regulatory Guide
        </button>
      </div>
    </div>
  );
};

export default ComplianceDashboard;
