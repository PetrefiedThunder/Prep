'use client'

import { useState } from 'react'
import { uploadDocumentFile, createKitchenDocument } from '@/lib/actions/documents'
import type { DocumentType } from '@/lib/types'

interface DocumentUploadFormProps {
  kitchenId: string
  documentType: DocumentType
}

export default function DocumentUploadForm({
  kitchenId,
  documentType,
}: DocumentUploadFormProps) {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    setError(null)

    try {
      // Upload file to storage
      const uploadResult = await uploadDocumentFile(file, kitchenId, documentType)

      if (uploadResult.error) {
        setError(uploadResult.error)
        setUploading(false)
        return
      }

      // Create document record
      const documentResult = await createKitchenDocument(
        kitchenId,
        documentType,
        uploadResult.data!.file_url,
        uploadResult.data!.file_name
      )

      if (documentResult.error) {
        setError(documentResult.error)
        setUploading(false)
        return
      }

      // Success - page will revalidate
      setFile(null)
      setUploading(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4">
      <div className="flex flex-col gap-3">
        <input
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          disabled={uploading}
          className="block w-full text-sm text-gray-500
            file:mr-4 file:py-2 file:px-4
            file:rounded-md file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100
            disabled:opacity-50 disabled:cursor-not-allowed"
        />
        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}
        <button
          type="submit"
          disabled={!file || uploading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
      </div>
    </form>
  )
}
