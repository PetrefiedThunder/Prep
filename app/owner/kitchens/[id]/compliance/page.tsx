import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getKitchenDocuments } from '@/lib/actions/documents'
import DocumentUploadForm from './DocumentUploadForm'
import DocumentStatusBadge from './DocumentStatusBadge'
import type { KitchenDocument } from '@/lib/types'

export default async function KitchenCompliancePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Get kitchen info
  const { data: kitchen } = await supabase
    .from('kitchens')
    .select('id, title, owner_id, compliance_approved')
    .eq('id', id)
    .single()

  if (!kitchen || kitchen.owner_id !== user.id) {
    redirect('/owner/kitchens')
  }

  // Get documents for this kitchen
  const { data: documents } = await getKitchenDocuments(id)

  const healthPermit = (documents as KitchenDocument[])?.find(
    d => d.document_type === 'health_permit'
  )
  const insurance = (documents as KitchenDocument[])?.find(
    d => d.document_type === 'insurance_certificate'
  )

  const isCompliant = kitchen.compliance_approved

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Compliance Documents</h1>
        <p className="text-gray-600">
          Kitchen: <span className="font-semibold">{kitchen.title}</span>
        </p>
        {isCompliant ? (
          <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-800 font-semibold">
              ✅ Your kitchen is compliant and available for booking
            </p>
          </div>
        ) : (
          <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-yellow-800">
              ⚠️ Upload and get approval for both documents to make your kitchen bookable
            </p>
          </div>
        )}
      </div>

      <div className="space-y-8">
        {/* Health Permit Section */}
        <div className="border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold">Health Permit</h2>
              <p className="text-sm text-gray-600">
                Valid health department permit or certificate
              </p>
            </div>
            {healthPermit && <DocumentStatusBadge status={healthPermit.status} />}
          </div>

          {healthPermit ? (
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                Uploaded: {new Date(healthPermit.uploaded_at).toLocaleDateString()}
              </p>
              <p className="text-sm">
                <a
                  href={healthPermit.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  View Document →
                </a>
              </p>
              {healthPermit.review_notes && (
                <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
                  <p className="font-semibold">Review Notes:</p>
                  <p className="text-gray-700">{healthPermit.review_notes}</p>
                </div>
              )}
              {healthPermit.status === 'rejected' && (
                <DocumentUploadForm kitchenId={id} documentType="health_permit" />
              )}
            </div>
          ) : (
            <DocumentUploadForm kitchenId={id} documentType="health_permit" />
          )}
        </div>

        {/* Insurance Certificate Section */}
        <div className="border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-xl font-semibold">Insurance Certificate</h2>
              <p className="text-sm text-gray-600">
                General liability insurance certificate
              </p>
            </div>
            {insurance && <DocumentStatusBadge status={insurance.status} />}
          </div>

          {insurance ? (
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                Uploaded: {new Date(insurance.uploaded_at).toLocaleDateString()}
              </p>
              <p className="text-sm">
                <a
                  href={insurance.file_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  View Document →
                </a>
              </p>
              {insurance.review_notes && (
                <div className="mt-3 p-3 bg-gray-50 rounded text-sm">
                  <p className="font-semibold">Review Notes:</p>
                  <p className="text-gray-700">{insurance.review_notes}</p>
                </div>
              )}
              {insurance.status === 'rejected' && (
                <DocumentUploadForm kitchenId={id} documentType="insurance_certificate" />
              )}
            </div>
          ) : (
            <DocumentUploadForm kitchenId={id} documentType="insurance_certificate" />
          )}
        </div>
      </div>

      <div className="mt-8">
        <a
          href="/owner/kitchens"
          className="text-blue-600 hover:underline"
        >
          ← Back to My Kitchens
        </a>
      </div>
    </div>
  )
}
