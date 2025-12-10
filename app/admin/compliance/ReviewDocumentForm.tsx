'use client'

import { useState } from 'react'
import { reviewDocument } from '@/lib/actions/documents'

interface ReviewDocumentFormProps {
  documentId: string
}

export default function ReviewDocumentForm({ documentId }: ReviewDocumentFormProps) {
  const [reviewNotes, setReviewNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleReview = async (status: 'approved' | 'rejected') => {
    setSubmitting(true)
    setError(null)

    const result = await reviewDocument(documentId, status, reviewNotes)

    if (result.error) {
      setError(result.error)
      setSubmitting(false)
      return
    }

    // Success - page will revalidate and this document will disappear
    setSubmitting(false)
  }

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="notes" className="block text-sm font-medium mb-2">
          Review Notes (optional)
        </label>
        <textarea
          id="notes"
          value={reviewNotes}
          onChange={(e) => setReviewNotes(e.target.value)}
          disabled={submitting}
          placeholder="Add any notes about this review..."
          rows={4}
          className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <div className="flex gap-3">
        <button
          onClick={() => handleReview('approved')}
          disabled={submitting}
          className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {submitting ? 'Processing...' : '✓ Approve'}
        </button>
        <button
          onClick={() => handleReview('rejected')}
          disabled={submitting}
          className="flex-1 px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors font-medium"
        >
          {submitting ? 'Processing...' : '✗ Reject'}
        </button>
      </div>
    </div>
  )
}
