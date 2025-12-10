import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { getPendingDocuments } from '@/lib/actions/documents'
import ReviewDocumentForm from './ReviewDocumentForm'
import type { KitchenDocument } from '@/lib/types'

interface DocumentWithKitchen extends KitchenDocument {
  kitchens: {
    title: string
    address: string
    city: string
    state: string
    profiles: {
      email: string
      full_name: string | null
    }
  }
}

export default async function AdminCompliancePage() {
  const supabase = await createClient()

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (!user) {
    redirect('/auth/login')
  }

  // Check if user is admin
  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single()

  if (!profile || profile.role !== 'admin') {
    redirect('/')
  }

  // Get pending documents
  const { data: documents, error } = await getPendingDocuments()

  if (error) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <h1 className="text-3xl font-bold mb-4">Compliance Review Dashboard</h1>
        <p className="text-red-600">Error loading documents: {error}</p>
      </div>
    )
  }

  const pendingDocs = (documents || []) as DocumentWithKitchen[]

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Compliance Review Dashboard</h1>
        <p className="text-gray-600">
          Review and approve kitchen compliance documents
        </p>
      </div>

      {pendingDocs.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-600 text-lg">
            ✓ No pending documents to review
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {pendingDocs.map((doc) => {
            const kitchen = doc.kitchens
            const owner = kitchen?.profiles

            return (
              <div
                key={doc.id}
                className="border border-gray-200 rounded-lg p-6 bg-white shadow-sm"
              >
                <div className="grid md:grid-cols-2 gap-6">
                  {/* Document Info */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3">
                      {doc.document_type === 'health_permit'
                        ? 'Health Permit'
                        : 'Insurance Certificate'}
                    </h3>

                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-semibold">Kitchen:</span>{' '}
                        {kitchen?.title || 'Unknown'}
                      </div>
                      <div>
                        <span className="font-semibold">Location:</span>{' '}
                        {kitchen?.city}, {kitchen?.state}
                      </div>
                      <div>
                        <span className="font-semibold">Address:</span>{' '}
                        {kitchen?.address}
                      </div>
                      <div>
                        <span className="font-semibold">Owner:</span>{' '}
                        {owner?.full_name || owner?.email}
                      </div>
                      <div>
                        <span className="font-semibold">Email:</span>{' '}
                        {owner?.email}
                      </div>
                      <div>
                        <span className="font-semibold">Uploaded:</span>{' '}
                        {new Date(doc.uploaded_at).toLocaleString()}
                      </div>
                    </div>

                    <div className="mt-4">
                      <a
                        href={doc.file_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-md text-sm font-medium transition-colors"
                      >
                        View Document →
                      </a>
                    </div>
                  </div>

                  {/* Review Actions */}
                  <div className="border-l border-gray-200 pl-6">
                    <h4 className="font-semibold mb-3">Review Actions</h4>
                    <ReviewDocumentForm documentId={doc.id} />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      <div className="mt-8">
        <a
          href="/admin"
          className="text-blue-600 hover:underline"
        >
          ← Back to Admin Dashboard
        </a>
      </div>
    </div>
  )
}
