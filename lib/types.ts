// Database types
export type UserRole = 'owner' | 'tenant' | 'admin'

export interface Profile {
  id: string
  email: string
  full_name: string | null
  phone: string | null
  role: UserRole
  created_at: string
  updated_at: string
}

export interface Kitchen {
  id: string
  owner_id: string
  title: string
  description: string | null
  address: string
  city: string
  state: string
  zip_code: string
  price_per_hour: number
  max_capacity: number | null
  square_feet: number | null
  is_active: boolean
  compliance_approved: boolean
  created_at: string
  updated_at: string
}

export interface KitchenPhoto {
  id: string
  kitchen_id: string
  url: string
  is_primary: boolean
  sort_order: number
  created_at: string
}

export interface KitchenWithPhotos extends Kitchen {
  kitchen_photos: KitchenPhoto[]
}

export type BookingStatus = 'pending' | 'confirmed' | 'cancelled' | 'completed'

export interface Booking {
  id: string
  kitchen_id: string
  renter_id: string
  start_time: string
  end_time: string
  total_hours: number
  price_per_hour: number
  total_amount: number
  status: BookingStatus
  stripe_payment_intent_id: string | null
  created_at: string
  updated_at: string
}

export interface BookingWithKitchen extends Booking {
  kitchens: Kitchen
  profiles?: Profile
}

export interface StripeAccount {
  id: string
  user_id: string
  stripe_account_id: string
  onboarding_complete: boolean
  created_at: string
  updated_at: string
}

export type PayoutStatus = 'pending' | 'processing' | 'paid' | 'failed'

export interface Payout {
  id: string
  booking_id: string
  owner_id: string
  amount: number
  platform_fee: number
  net_amount: number
  status: PayoutStatus
  stripe_transfer_id: string | null
  paid_at: string | null
  created_at: string
  updated_at: string
}

// Kitchen documents types
export type DocumentType = 'health_permit' | 'insurance_certificate'
export type DocumentStatus = 'pending' | 'approved' | 'rejected'

export interface KitchenDocument {
  id: string
  kitchen_id: string
  document_type: DocumentType
  file_url: string
  file_name: string
  status: DocumentStatus
  uploaded_at: string
  reviewed_at: string | null
  reviewer_id: string | null
  review_notes: string | null
}

export interface KitchenDocumentWithDetails extends KitchenDocument {
  kitchen_title: string
  owner_email: string
  owner_name: string | null
  address: string
  city: string
  state: string
}

// Form types
export interface KitchenFormData {
  title: string
  description: string
  address: string
  city: string
  state: string
  zip_code: string
  price_per_hour: number
  max_capacity: number
  square_feet?: number
}
