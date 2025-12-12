'use client'

import { useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { toggleKitchenActive, deleteKitchen } from '@/lib/actions/kitchens'
import type { KitchenWithPhotos } from '@/lib/types'

interface KitchenCardProps {
  kitchen: KitchenWithPhotos
}

export default function KitchenCard({ kitchen }: KitchenCardProps) {
  const [isActive, setIsActive] = useState(kitchen.is_active)
  const [loading, setLoading] = useState(false)

  const handleToggleActive = async () => {
    setLoading(true)
    const result = await toggleKitchenActive(kitchen.id, !isActive)
    if (!result.error) {
      setIsActive(!isActive)
    }
    setLoading(false)
  }

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this kitchen? This action cannot be undone.')) {
      return
    }

    setLoading(true)
    const result = await deleteKitchen(kitchen.id)
    if (result.error) {
      alert('Error deleting kitchen: ' + result.error)
      setLoading(false)
    }
    // Page will refresh via revalidation
  }

  const primaryPhoto = kitchen.kitchen_photos?.find(p => p.is_primary)
  const photoUrl = primaryPhoto?.url || '/placeholder-kitchen.jpg'

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden">
      <div className="aspect-video bg-gray-200 relative">
        {photoUrl && (
          <Image
            src={photoUrl}
            alt={kitchen.title}
            fill
            sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
            className="object-cover"
          />
        )}
        <div className="absolute top-2 right-2 z-10">
          <span
            className={`px-3 py-1 rounded-full text-sm font-semibold ${
              isActive
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {isActive ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>

      <div className="p-4">
        <h3 className="text-xl font-semibold text-gray-900 mb-2">
          {kitchen.title}
        </h3>

        <div className="text-sm text-gray-600 mb-2">
          {kitchen.city}, {kitchen.state}
        </div>

        <div className="text-lg font-bold text-gray-900 mb-2">
          ${kitchen.price_per_hour}/hour
        </div>

        {!kitchen.compliance_approved && (
          <div className="mb-3 px-3 py-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
            ⚠️ Compliance documents needed
          </div>
        )}

        <div className="flex gap-2 mb-2">
          <Link
            href={`/owner/kitchens/${kitchen.id}/edit`}
            className="flex-1 text-center bg-gray-100 text-gray-900 py-2 rounded-md font-semibold hover:bg-gray-200 transition text-sm"
          >
            Edit
          </Link>
          <button
            onClick={handleToggleActive}
            disabled={loading}
            className="flex-1 bg-gray-900 text-white py-2 rounded-md font-semibold hover:bg-gray-800 transition disabled:opacity-50 text-sm"
          >
            {isActive ? 'Deactivate' : 'Activate'}
          </button>
        </div>

        <Link
          href={`/owner/kitchens/${kitchen.id}/compliance`}
          className="block w-full text-center bg-blue-600 text-white py-2 rounded-md font-semibold hover:bg-blue-700 transition text-sm"
        >
          Compliance Documents
        </Link>

        <button
          onClick={handleDelete}
          disabled={loading}
          className="w-full mt-2 text-red-600 py-2 text-sm font-semibold hover:text-red-800 transition disabled:opacity-50"
        >
          Delete
        </button>
      </div>
    </div>
  )
}
