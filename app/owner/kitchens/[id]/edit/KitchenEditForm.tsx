'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { updateKitchen } from '@/lib/actions/kitchens'
import PhotoUpload from '@/components/PhotoUpload'
import type { KitchenWithPhotos } from '@/lib/types'

interface KitchenEditFormProps {
  kitchen: KitchenWithPhotos
}

export default function KitchenEditForm({ kitchen }: KitchenEditFormProps) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(false)

    const formData = new FormData(e.currentTarget)
    const data = {
      title: formData.get('title') as string,
      description: formData.get('description') as string,
      address: formData.get('address') as string,
      city: formData.get('city') as string,
      state: formData.get('state') as string,
      zip_code: formData.get('zip_code') as string,
      price_per_hour: parseFloat(formData.get('price_per_hour') as string),
      max_capacity: parseInt(formData.get('max_capacity') as string),
      square_feet: formData.get('square_feet')
        ? parseInt(formData.get('square_feet') as string)
        : undefined,
    }

    const result = await updateKitchen(kitchen.id, data)

    if (result.error) {
      setError(result.error)
    } else {
      setSuccess(true)
    }
    setLoading(false)
  }

  return (
    <div className="space-y-8">
      {/* Photo Upload Section */}
      <div className="bg-white p-8 rounded-lg shadow-md">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Photos</h2>
        <p className="text-sm text-gray-600 mb-4">
          Add photos to showcase your kitchen. The first photo will be used as the cover image.
        </p>
        <PhotoUpload
          kitchenId={kitchen.id}
          initialPhotos={kitchen.kitchen_photos?.map(p => ({
            id: p.id,
            url: p.url,
            storage_path: p.storage_path ?? null,
            is_primary: p.is_primary,
            sort_order: p.sort_order,
          })) || []}
        />
      </div>

      {/* Kitchen Details Form */}
      <form onSubmit={handleSubmit} className="bg-white p-8 rounded-lg shadow-md space-y-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Kitchen Details</h2>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            {error}
          </div>
        )}
        {success && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded">
            Kitchen details updated successfully.
          </div>
        )}

        <div>
          <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
            Kitchen Title *
          </label>
          <input id="title" name="title" type="text" required defaultValue={kitchen.title}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea id="description" name="description" rows={4} defaultValue={kitchen.description || ''}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label htmlFor="address" className="block text-sm font-medium text-gray-700 mb-1">Street Address *</label>
            <input id="address" name="address" type="text" required defaultValue={kitchen.address}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          <div>
            <label htmlFor="city" className="block text-sm font-medium text-gray-700 mb-1">City *</label>
            <input id="city" name="city" type="text" required defaultValue={kitchen.city}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          <div>
            <label htmlFor="state" className="block text-sm font-medium text-gray-700 mb-1">State *</label>
            <input id="state" name="state" type="text" required maxLength={2} defaultValue={kitchen.state}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          <div>
            <label htmlFor="zip_code" className="block text-sm font-medium text-gray-700 mb-1">ZIP Code *</label>
            <input id="zip_code" name="zip_code" type="text" required defaultValue={kitchen.zip_code}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label htmlFor="price_per_hour" className="block text-sm font-medium text-gray-700 mb-1">Price per Hour ($) *</label>
            <input id="price_per_hour" name="price_per_hour" type="number" step="0.01" min="0" required
              defaultValue={kitchen.price_per_hour}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          <div>
            <label htmlFor="max_capacity" className="block text-sm font-medium text-gray-700 mb-1">Max Capacity *</label>
            <input id="max_capacity" name="max_capacity" type="number" min="1" required
              defaultValue={kitchen.max_capacity || ''}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
          <div>
            <label htmlFor="square_feet" className="block text-sm font-medium text-gray-700 mb-1">Square Feet</label>
            <input id="square_feet" name="square_feet" type="number" min="1"
              defaultValue={kitchen.square_feet || ''}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-gray-900" />
          </div>
        </div>

        <div className="flex gap-4 pt-4">
          <button type="submit" disabled={loading}
            className="flex-1 bg-gray-900 text-white py-3 px-4 rounded-md font-semibold hover:bg-gray-800 transition disabled:opacity-50 disabled:cursor-not-allowed">
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
          <button type="button" onClick={() => router.push('/owner/kitchens')}
            className="px-6 py-3 border border-gray-300 rounded-md font-semibold hover:bg-gray-50 transition">
            Back to Kitchens
          </button>
        </div>
      </form>
    </div>
  )
}
