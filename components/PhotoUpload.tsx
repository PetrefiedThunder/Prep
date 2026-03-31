'use client'

import { useState, useRef, useCallback } from 'react'
import Image from 'next/image'
import { uploadKitchenPhoto, deleteKitchenPhoto, setPhotoAsPrimary } from '@/lib/actions/photos'

interface Photo {
  id: string
  url: string
  storage_path: string | null
  is_primary: boolean
  sort_order: number
}

interface PhotoUploadProps {
  kitchenId: string
  initialPhotos?: Photo[]
  maxPhotos?: number
}

export default function PhotoUpload({
  kitchenId,
  initialPhotos = [],
  maxPhotos = 10,
}: PhotoUploadProps) {
  const [photos, setPhotos] = useState<Photo[]>(initialPhotos)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFiles = useCallback(async (files: FileList | null) => {
    if (!files || files.length === 0) return

    const remaining = maxPhotos - photos.length
    if (remaining <= 0) {
      setError(`Maximum ${maxPhotos} photos allowed`)
      return
    }

    setUploading(true)
    setError(null)

    const filesToUpload = Array.from(files).slice(0, remaining)

    for (const file of filesToUpload) {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('kitchenId', kitchenId)

      const result = await uploadKitchenPhoto(formData)

      if (result.error) {
        setError(result.error)
      } else if (result.data) {
        setPhotos(prev => [...prev, result.data as Photo])
      }
    }

    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }, [kitchenId, maxPhotos, photos.length])

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleDelete = async (photoId: string) => {
    const result = await deleteKitchenPhoto(photoId)
    if (result.error) {
      setError(result.error)
    } else {
      setPhotos(prev => prev.filter(p => p.id !== photoId))
    }
  }

  const handleSetPrimary = async (photoId: string) => {
    const result = await setPhotoAsPrimary(photoId)
    if (result.error) {
      setError(result.error)
    } else {
      setPhotos(prev =>
        prev.map(p => ({ ...p, is_primary: p.id === photoId }))
      )
    }
  }

  return (
    <div className="space-y-4">
      <label className="block text-sm font-medium text-gray-700">
        Kitchen Photos ({photos.length}/{maxPhotos})
      </label>

      {/* Drop zone */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
          ${dragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 bg-gray-50'
          }
          ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
          className="hidden"
          disabled={uploading}
        />

        <div className="space-y-2">
          <svg className="mx-auto h-12 w-12 text-gray-400" stroke="currentColor" fill="none" viewBox="0 0 48 48">
            <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {uploading ? (
            <p className="text-sm text-gray-600">Uploading...</p>
          ) : (
            <>
              <p className="text-sm text-gray-600">
                <span className="font-semibold text-gray-900">Click to upload</span> or drag and drop
              </p>
              <p className="text-xs text-gray-500">
                JPEG, PNG, or WebP up to 5MB
              </p>
            </>
          )}
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      {/* Photo grid */}
      {photos.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {photos.map((photo) => (
            <div key={photo.id} className="relative group aspect-square rounded-lg overflow-hidden bg-gray-100">
              <Image
                src={photo.url}
                alt="Kitchen photo"
                fill
                sizes="(max-width: 768px) 50vw, (max-width: 1200px) 33vw, 25vw"
                className="object-cover"
              />

              {/* Primary badge */}
              {photo.is_primary && (
                <div className="absolute top-2 left-2 bg-green-600 text-white text-xs font-semibold px-2 py-1 rounded">
                  Primary
                </div>
              )}

              {/* Action buttons overlay */}
              <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 transition-all flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                {!photo.is_primary && (
                  <button
                    onClick={() => handleSetPrimary(photo.id)}
                    className="bg-white text-gray-900 text-xs font-semibold px-3 py-1.5 rounded hover:bg-gray-100 transition"
                  >
                    Set Primary
                  </button>
                )}

                <button
                  onClick={() => handleDelete(photo.id)}
                  className="bg-red-600 text-white text-xs font-semibold px-3 py-1.5 rounded hover:bg-red-700 transition"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
