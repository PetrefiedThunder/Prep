"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

interface Location {
  country: string;
  state?: string;
  city?: string;
}

interface CheckResult {
  code: string;
  status: "pass" | "fail" | "warn";
  details?: string;
  regulation_version?: string;
  evidence?: Array<{
    document_id: string;
    note?: string;
  }>;
}

interface Decision {
  overall: "pass" | "fail" | "warn";
  score: number;
  check_results: CheckResult[];
}

interface Recommendation {
  summary: string;
  operator_action?: string;
}

interface VerificationDetail {
  verification_id: string;
  vendor_id: string;
  status: string;
  evaluated_at?: string;
  jurisdiction: Location;
  kitchen_id?: string;
  decision: Decision;
  recommendation: Recommendation;
  ruleset_name: string;
  regulation_version: string;
  engine_version: string;
  initiated_by?: string;
  initiated_from: string;
  created_at: string;
  updated_at: string;
}

export default function VerificationDetailPage() {
  const params = useParams();
  const verificationId = params?.verificationId as string;

  const [verification, setVerification] = useState<VerificationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchVerification() {
      try {
        // In production, fetch from API
        // GET /api/v1/vendors/{vendorId}/verifications/{verificationId}
        setLoading(false);
      } catch (err) {
        setError("Failed to load verification details");
        setLoading(false);
      }
    }

    if (verificationId) {
      fetchVerification();
    }
  }, [verificationId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-gray-600">Loading verification...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!verification) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-gray-600">Verification not found</div>
        </div>
      </div>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "passed":
        return "bg-green-100 text-green-800";
      case "failed":
        return "bg-red-100 text-red-800";
      case "in_review":
        return "bg-blue-100 text-blue-800";
      case "pending_documents":
        return "bg-yellow-100 text-yellow-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getCheckStatusIcon = (status: "pass" | "fail" | "warn") => {
    switch (status) {
      case "pass":
        return "✓";
      case "fail":
        return "✗";
      case "warn":
        return "⚠";
    }
  };

  const getCheckStatusColor = (status: "pass" | "fail" | "warn") => {
    switch (status) {
      case "pass":
        return "text-green-600";
      case "fail":
        return "text-red-600";
      case "warn":
        return "text-yellow-600";
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <Link
            href={`/operator/vendors/${verification.vendor_id}`}
            className="text-blue-600 hover:text-blue-800 mb-4 inline-block"
          >
            ← Back to vendor
          </Link>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex justify-between items-start mb-6">
            <h1 className="text-3xl font-bold text-gray-900">
              Verification Results
            </h1>
            <span
              className={`px-3 py-1 text-sm font-semibold rounded-full ${getStatusColor(
                verification.status
              )}`}
            >
              {verification.status.replace(/_/g, " ").toUpperCase()}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-6 mb-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Verification ID
              </h3>
              <p className="text-gray-900 font-mono text-sm">
                {verification.verification_id}
              </p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Vendor ID
              </h3>
              <p className="text-gray-900 font-mono text-sm">
                {verification.vendor_id}
              </p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Jurisdiction
              </h3>
              <p className="text-gray-900">
                {verification.jurisdiction.city && `${verification.jurisdiction.city}, `}
                {verification.jurisdiction.state && `${verification.jurisdiction.state}, `}
                {verification.jurisdiction.country}
              </p>
            </div>

            {verification.kitchen_id && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  Kitchen ID
                </h3>
                <p className="text-gray-900">{verification.kitchen_id}</p>
              </div>
            )}

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Ruleset
              </h3>
              <p className="text-gray-900">{verification.ruleset_name}</p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Regulation Version
              </h3>
              <p className="text-gray-900">{verification.regulation_version}</p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Engine Version
              </h3>
              <p className="text-gray-900">{verification.engine_version}</p>
            </div>

            {verification.evaluated_at && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  Evaluated At
                </h3>
                <p className="text-gray-900">
                  {new Date(verification.evaluated_at).toLocaleString()}
                </p>
              </div>
            )}
          </div>

          <div className="border-t pt-6">
            <div className="flex items-center mb-4">
              <div
                className={`text-5xl font-bold mr-4 ${
                  verification.decision.overall === "pass"
                    ? "text-green-600"
                    : verification.decision.overall === "fail"
                    ? "text-red-600"
                    : "text-yellow-600"
                }`}
              >
                {verification.decision.overall === "pass" ? "✓" : "✗"}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {verification.decision.overall.toUpperCase()}
                </h2>
                <p className="text-gray-600">
                  Compliance Score: {(verification.decision.score * 100).toFixed(0)}%
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Check Results
          </h2>

          {verification.decision.check_results.length === 0 ? (
            <p className="text-gray-600">No check results available</p>
          ) : (
            <div className="space-y-4">
              {verification.decision.check_results.map((check, index) => (
                <div
                  key={index}
                  className="border rounded-lg p-4 hover:bg-gray-50"
                >
                  <div className="flex items-start">
                    <div
                      className={`text-2xl mr-3 ${getCheckStatusColor(
                        check.status
                      )}`}
                    >
                      {getCheckStatusIcon(check.status)}
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-start mb-2">
                        <h3 className="font-semibold text-gray-900">
                          {check.code.replace(/_/g, " ")}
                        </h3>
                        <span
                          className={`px-2 py-1 text-xs font-semibold rounded ${
                            check.status === "pass"
                              ? "bg-green-100 text-green-800"
                              : check.status === "fail"
                              ? "bg-red-100 text-red-800"
                              : "bg-yellow-100 text-yellow-800"
                          }`}
                        >
                          {check.status.toUpperCase()}
                        </span>
                      </div>
                      {check.details && (
                        <p className="text-gray-700 mb-2">{check.details}</p>
                      )}
                      {check.regulation_version && (
                        <p className="text-sm text-gray-500">
                          Regulation: {check.regulation_version}
                        </p>
                      )}
                      {check.evidence && check.evidence.length > 0 && (
                        <div className="mt-2">
                          <p className="text-sm font-medium text-gray-700 mb-1">
                            Evidence:
                          </p>
                          <ul className="text-sm text-gray-600 space-y-1">
                            {check.evidence.map((ev, evIndex) => (
                              <li key={evIndex} className="flex items-center">
                                <span className="font-mono text-xs mr-2">
                                  {ev.document_id.substring(0, 8)}...
                                </span>
                                {ev.note && (
                                  <span className="text-gray-500">- {ev.note}</span>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            Recommendation
          </h2>
          <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-4">
            <p className="text-gray-900">{verification.recommendation.summary}</p>
          </div>
          {verification.recommendation.operator_action && (
            <div>
              <h3 className="font-semibold text-gray-900 mb-2">
                Operator Action:
              </h3>
              <p className="text-gray-700">
                {verification.recommendation.operator_action}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
