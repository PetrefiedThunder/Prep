"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

interface Location {
  country: string;
  state?: string;
  city?: string;
}

interface Vendor {
  vendor_id: string;
  external_id: string;
  legal_name: string;
  doing_business_as?: string;
  status: string;
  primary_location: Location;
  contact?: {
    email?: string;
    phone?: string;
  };
  tax_id_last4?: string;
  created_at: string;
  updated_at: string;
}

interface Document {
  document_id: string;
  type: string;
  jurisdiction: Location;
  expires_on?: string;
  file_name: string;
  created_at: string;
}

export default function VendorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const vendorId = params?.vendorId as string;

  const [vendor, setVendor] = useState<Vendor | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    async function fetchVendorData() {
      try {
        // In production, fetch from API
        // For now, using mock data
        setLoading(false);
      } catch (err) {
        setError("Failed to load vendor data");
        setLoading(false);
      }
    }

    if (vendorId) {
      fetchVendorData();
    }
  }, [vendorId]);

  async function handleRunVerification() {
    if (!vendor) return;

    setVerifying(true);
    try {
      // In production, call POST /api/v1/vendors/{vendorId}/verifications
      // const response = await fetch(`/api/v1/vendors/${vendorId}/verifications`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'X-Prep-Api-Key': 'your-api-key',
      //   },
      //   body: JSON.stringify({
      //     jurisdiction: { country: 'US', state: 'CA', city: 'San Francisco' },
      //     purpose: 'shared_kitchen_rental',
      //   }),
      // });
      // const data = await response.json();
      // router.push(`/operator/verifications/${data.verification_id}`);

      alert("Verification feature will be available when API is running");
      setVerifying(false);
    } catch (err) {
      setError("Failed to run verification");
      setVerifying(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-gray-600">Loading vendor...</div>
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
          <Link
            href="/operator/vendors"
            className="mt-4 inline-block text-blue-600 hover:text-blue-800"
          >
            Back to vendors
          </Link>
        </div>
      </div>
    );
  }

  if (!vendor) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-gray-600">Vendor not found</div>
          <Link
            href="/operator/vendors"
            className="mt-4 inline-block text-blue-600 hover:text-blue-800"
          >
            Back to vendors
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <Link
            href="/operator/vendors"
            className="text-blue-600 hover:text-blue-800 mb-4 inline-block"
          >
            ← Back to vendors
          </Link>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                {vendor.doing_business_as || vendor.legal_name}
              </h1>
              {vendor.doing_business_as && (
                <p className="text-gray-600 mt-1">Legal: {vendor.legal_name}</p>
              )}
            </div>
            <span
              className={`px-3 py-1 text-sm font-semibold rounded-full ${
                vendor.status === "verified"
                  ? "bg-green-100 text-green-800"
                  : vendor.status === "onboarding"
                  ? "bg-yellow-100 text-yellow-800"
                  : vendor.status === "rejected"
                  ? "bg-red-100 text-red-800"
                  : "bg-gray-100 text-gray-800"
              }`}
            >
              {vendor.status}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                External ID
              </h3>
              <p className="text-gray-900">{vendor.external_id}</p>
            </div>

            <div>
              <h3 className="text-sm font-medium text-gray-500 mb-2">
                Location
              </h3>
              <p className="text-gray-900">
                {vendor.primary_location.city && `${vendor.primary_location.city}, `}
                {vendor.primary_location.state && `${vendor.primary_location.state}, `}
                {vendor.primary_location.country}
              </p>
            </div>

            {vendor.contact?.email && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Email</h3>
                <p className="text-gray-900">{vendor.contact.email}</p>
              </div>
            )}

            {vendor.contact?.phone && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">Phone</h3>
                <p className="text-gray-900">{vendor.contact.phone}</p>
              </div>
            )}

            {vendor.tax_id_last4 && (
              <div>
                <h3 className="text-sm font-medium text-gray-500 mb-2">
                  Tax ID (Last 4)
                </h3>
                <p className="text-gray-900">****{vendor.tax_id_last4}</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Documents</h2>

          {documents.length === 0 ? (
            <p className="text-gray-600">No documents uploaded yet</p>
          ) : (
            <div className="overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Type
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      File Name
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Jurisdiction
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Expires
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                      Uploaded
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <tr key={doc.document_id}>
                      <td className="px-4 py-4 text-sm text-gray-900">
                        {doc.type.replace(/_/g, " ")}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-500">
                        {doc.file_name}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-500">
                        {doc.jurisdiction.city && `${doc.jurisdiction.city}, `}
                        {doc.jurisdiction.state && `${doc.jurisdiction.state}, `}
                        {doc.jurisdiction.country}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-500">
                        {doc.expires_on
                          ? new Date(doc.expires_on).toLocaleDateString()
                          : "N/A"}
                      </td>
                      <td className="px-4 py-4 text-sm text-gray-500">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Verification</h2>
          <p className="text-gray-600 mb-4">
            Run a verification for this vendor for a San Francisco shared kitchen.
          </p>
          <button
            onClick={handleRunVerification}
            disabled={verifying}
            className={`${
              verifying
                ? "bg-gray-400 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700"
            } text-white font-semibold py-2 px-4 rounded`}
          >
            {verifying ? "Running verification..." : "Run Verification for SF Kitchen"}
          </button>
        </div>
      </div>
    </div>
  );
}
