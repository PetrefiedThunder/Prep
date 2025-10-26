import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';
import { Shield, TrendingUp, AlertCircle, Map, RefreshCw } from 'lucide-react';

const AdminRegulatoryDashboard = () => {
  const { token } = useAuth();
  const [regulatoryData, setRegulatoryData] = useState({ states: [], alerts: [] });
  const [scrapingStatus, setScrapingStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [scrapeLoading, setScrapeLoading] = useState({});

  useEffect(() => {
    loadRegulatoryData();
  }, []);

  const loadRegulatoryData = async () => {
    setLoading(true);
    try {
      const [states, scraping] = await Promise.all([
        api.get('/admin/regulatory/states', token),
        api.get('/admin/regulatory/scraping-status', token),
      ]);
      setRegulatoryData(states);
      setScrapingStatus(scraping.status || {});
    } catch (error) {
      console.error('Failed to load regulatory data:', error);
    } finally {
      setLoading(false);
    }
  };

  const triggerScraping = async (state) => {
    setScrapeLoading((prev) => ({ ...prev, [state]: true }));
    try {
      await api.post('/admin/regulatory/scrape', { states: [state] }, token);
      await loadRegulatoryData();
    } catch (error) {
      console.error('Failed to trigger scraping:', error);
    } finally {
      setScrapeLoading((prev) => ({ ...prev, [state]: false }));
    }
  };

  const getCompliancePercentage = (stateData) => {
    const totalKitchens = stateData.total_kitchens || 1;
    const compliantKitchens = stateData.compliant_kitchens || 0;
    return Math.round((compliantKitchens / totalKitchens) * 100);
  };

  if (loading) {
    return <div>Loading regulatory dashboard...</div>;
  }

  return (
    <div className="admin-regulatory-dashboard space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <Shield className="text-blue-500 mr-3" size={24} />
            <div>
              <div className="text-2xl font-bold">{regulatoryData.total_kitchens}</div>
              <div className="text-sm text-gray-500">Total Kitchens</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <TrendingUp className="text-green-500 mr-3" size={24} />
            <div>
              <div className="text-2xl font-bold">{regulatoryData.compliant_kitchens}</div>
              <div className="text-sm text-gray-500">Compliant Kitchens</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <AlertCircle className="text-red-500 mr-3" size={24} />
            <div>
              <div className="text-2xl font-bold">{regulatoryData.non_compliant_kitchens}</div>
              <div className="text-sm text-gray-500">Non-Compliant</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center">
            <Map className="text-purple-500 mr-3" size={24} />
            <div>
              <div className="text-2xl font-bold">{regulatoryData.states_covered}</div>
              <div className="text-sm text-gray-500">States Covered</div>
            </div>
          </div>
        </div>
      </div>

      {/* State-by-State Compliance */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">State Compliance Overview</h3>
        <div className="space-y-4">
          {regulatoryData.states?.map((state) => (
            <div key={state.code} className="flex items-center justify-between p-3 border rounded">
              <div className="flex items-center space-x-4">
                <span className="font-medium">{state.name}</span>
                <span
                  className={`px-2 py-1 rounded text-xs ${
                    getCompliancePercentage(state) >= 80
                      ? 'bg-green-100 text-green-800'
                      : getCompliancePercentage(state) >= 60
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {getCompliancePercentage(state)}% Compliant
                </span>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">
                  {state.compliant_kitchens}/{state.total_kitchens} kitchens
                </span>
                <button
                  onClick={() => triggerScraping(state.code)}
                  className="flex items-center text-blue-600 hover:text-blue-800"
                  disabled={scrapeLoading[state.code] || scrapingStatus[state.code] === 'running'}
                >
                  <RefreshCw
                    size={16}
                    className={`mr-1 ${
                      scrapeLoading[state.code] || scrapingStatus[state.code] === 'running'
                        ? 'animate-spin'
                        : ''
                    }`}
                  />
                  Update
                </button>
              </div>
            </div>
          ))}
          {regulatoryData.states?.length === 0 && (
            <p className="text-gray-500 text-sm">No state compliance data available.</p>
          )}
        </div>
      </div>

      {/* Regulatory Alerts */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-yellow-800 mb-4">Regulatory Alerts</h3>
        <div className="space-y-2">
          {regulatoryData.alerts?.map((alert, index) => (
            <div key={index} className="flex items-center text-yellow-700">
              <AlertCircle size={16} className="mr-2" />
              <span>
                {alert.message}
                {alert.state ? ` - ${alert.state}` : ''}
              </span>
            </div>
          ))}
          {(!regulatoryData.alerts || regulatoryData.alerts.length === 0) && (
            <p className="text-yellow-600">No active regulatory alerts</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminRegulatoryDashboard;
