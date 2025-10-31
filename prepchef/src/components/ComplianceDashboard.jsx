import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Shield, AlertTriangle, CheckCircle, Clock, MapPin, Star } from 'lucide-react';

const ComplianceDashboard = ({ kitchenId }) => {
  const { token } = useAuth();
  const [complianceData, setComplianceData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [regulations, setRegulations] = useState([]);
  const [regulationsLoading, setRegulationsLoading] = useState(false);

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

  const renderPlanStatus = () => {
    const status = complianceData?.subscription_status;
    if (!status) {
      return null;
    }

    const normalizedStatus = status.replace(/_/g, ' ');
    let detail = normalizedStatus;
    if (status === 'trial' && complianceData?.trial_ends_at) {
      const endDate = new Date(complianceData.trial_ends_at);
      const now = new Date();
      const msRemaining = endDate.getTime() - now.getTime();
      const daysRemaining = Math.max(0, Math.ceil(msRemaining / (1000 * 60 * 60 * 24)));
      detail = `Trial – ${daysRemaining} day${daysRemaining === 1 ? '' : 's'} left`;
    }

    return (
      <div className="flex items-center space-x-2 bg-blue-50 text-blue-700 px-3 py-1 rounded-full text-sm">
        <Star size={16} />
        <span>{detail}</span>
      </div>
    );
  };

  const getComplianceStatusIcon = (level) => {
    switch (level) {
      case 'compliant':
        return <CheckCircle className="text-green-500" size={24} />;
      case 'partial_compliance':
        return <Clock className="text-yellow-500" size={24} />;
      case 'non_compliant':
        return <AlertTriangle className="text-red-500" size={24} />;
      default:
        return <Shield className="text-gray-500" size={24} />;
    }
  };

  if (loading) {
    return <div className="animate-pulse">Loading compliance data...</div>;
  }

  if (!complianceData) {
    return <div className="text-red-600">Unable to load compliance data.</div>;
  }

  return (
    <div className="compliance-dashboard space-y-6">
      {/* Compliance Status Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {getComplianceStatusIcon(complianceData?.compliance_level)}
            <div>
              <h2 className="text-xl font-semibold">Compliance Status</h2>
              <p className="text-gray-600 flex items-center">
                <MapPin size={16} className="mr-1" />
                {complianceData?.city}, {complianceData?.state}
              </p>
            </div>
          </div>
          <div className="flex flex-col items-end space-y-2">
            {renderPlanStatus()}
            <div className="text-right">
              <div className="text-2xl font-bold">{complianceData?.risk_score}/100</div>
              <div className="text-sm text-gray-500">Risk Score</div>
            </div>
          </div>
        </div>
      </div>

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
