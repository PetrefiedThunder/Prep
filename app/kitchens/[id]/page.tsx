import Link from 'next/link'
import Image from 'next/image'
import { getKitchen } from '@/lib/actions/kitchens'
import type { KitchenPhoto } from '@/lib/types'

interface KitchenDetailPageProps {
  params: Promise<{ id: string }>
}

export default async function KitchenDetailPage({ params }: KitchenDetailPageProps) {
  const { id } = await params
  const result = await getKitchen(id)

  if (result.error || !result.data) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          Kitchen not found or unavailable
        </div>
        <Link
          href="/kitchens"
          className="inline-block mt-4 text-gray-900 hover:underline"
        >
          ← Back to search
        </Link>
      </div>
    )
  }

  const kitchen = result.data
  const primaryPhoto = kitchen.kitchen_photos?.find((p: KitchenPhoto) => p.is_primary)
  const otherPhotos = kitchen.kitchen_photos?.filter((p: KitchenPhoto) => !p.is_primary) || []

  return (
    <div className="max-w-6xl mx-auto">
      <Link
        href="/kitchens"
        className="inline-block mb-4 text-gray-900 hover:underline"
      >
        ← Back to search
      </Link>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {/* Photo Gallery */}
        <div className="aspect-[21/9] bg-gray-200 relative">
          {primaryPhoto && (
            <Image
              src={primaryPhoto.url}
              alt={kitchen.title}
              fill
              sizes="100vw"
              priority
              className="object-cover"
            />
          )}
        </div>

        {otherPhotos.length > 0 && (
          <div className="grid grid-cols-4 gap-2 p-4">
            {otherPhotos.slice(0, 4).map((photo: KitchenPhoto) => (
              <div key={photo.id} className="aspect-video bg-gray-200 rounded overflow-hidden relative">
                <Image
                  src={photo.url}
                  alt="Kitchen photo"
                  fill
                  sizes="(max-width: 768px) 50vw, 25vw"
                  className="object-cover"
                />
              </div>
            ))}
          </div>
        )}

        {/* Kitchen Details */}
        <div className="p-8">
          <div className="flex items-start justify-between mb-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {kitchen.title}
              </h1>
              <p className="text-gray-600">
                {kitchen.address}, {kitchen.city}, {kitchen.state} {kitchen.zip_code}
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-gray-900">
                ${kitchen.price_per_hour}
              </div>
              <div className="text-sm text-gray-600">per hour</div>
            </div>
          </div>

          {kitchen.description && (
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Description
              </h2>
              <p className="text-gray-700 whitespace-pre-wrap">
                {kitchen.description}
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8 p-4 bg-gray-50 rounded-lg">
            {kitchen.max_capacity && (
              <div>
                <div className="text-sm text-gray-600">Max Capacity</div>
                <div className="text-lg font-semibold text-gray-900">
                  {kitchen.max_capacity} people
                </div>
              </div>
            )}
            {kitchen.square_feet && (
              <div>
                <div className="text-sm text-gray-600">Size</div>
                <div className="text-lg font-semibold text-gray-900">
                  {kitchen.square_feet} sq ft
                </div>
              </div>
            )}
            <div>
              <div className="text-sm text-gray-600">Location</div>
              <div className="text-lg font-semibold text-gray-900">
                {kitchen.city}, {kitchen.state}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Status</div>
              <div className="text-lg font-semibold text-green-600">
                Available
              </div>
            </div>
          </div>

          <div className="border-t pt-6">
            <Link
              href={`/kitchens/${kitchen.id}/book`}
              className="block w-full bg-gray-900 text-white text-center py-4 rounded-lg font-semibold hover:bg-gray-800 transition"
            >
              Book This Kitchen
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
