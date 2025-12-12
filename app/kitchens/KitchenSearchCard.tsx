import Link from 'next/link'
import Image from 'next/image'
import type { KitchenWithPhotos } from '@/lib/types'

interface KitchenSearchCardProps {
  kitchen: KitchenWithPhotos
}

export default function KitchenSearchCard({ kitchen }: KitchenSearchCardProps) {
  const primaryPhoto = kitchen.kitchen_photos?.find(p => p.is_primary)
  const photoUrl = primaryPhoto?.url || '/placeholder-kitchen.jpg'

  return (
    <Link href={`/kitchens/${kitchen.id}`} className="group">
      <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition">
        <div className="aspect-video bg-gray-200 relative">
          {photoUrl && (
            <Image
              src={photoUrl}
              alt={kitchen.title}
              fill
              sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
              className="object-cover group-hover:scale-105 transition duration-300"
            />
          )}
        </div>

        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-2 group-hover:text-gray-700 transition">
            {kitchen.title}
          </h3>

          <div className="text-sm text-gray-600 mb-2">
            {kitchen.city}, {kitchen.state}
          </div>

          {kitchen.description && (
            <p className="text-sm text-gray-600 mb-3 line-clamp-2">
              {kitchen.description}
            </p>
          )}

          <div className="flex items-center justify-between">
            <div className="text-xl font-bold text-gray-900">
              ${kitchen.price_per_hour}/hr
            </div>

            {kitchen.max_capacity && (
              <div className="text-sm text-gray-600">
                Up to {kitchen.max_capacity} people
              </div>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}
