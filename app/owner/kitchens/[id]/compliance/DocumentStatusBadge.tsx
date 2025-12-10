import type { DocumentStatus } from '@/lib/types'

interface DocumentStatusBadgeProps {
  status: DocumentStatus
}

export default function DocumentStatusBadge({ status }: DocumentStatusBadgeProps) {
  const styles = {
    pending: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    approved: 'bg-green-100 text-green-800 border-green-300',
    rejected: 'bg-red-100 text-red-800 border-red-300',
  }

  const labels = {
    pending: '⏳ Pending Review',
    approved: '✓ Approved',
    rejected: '✗ Rejected',
  }

  return (
    <span
      className={`px-3 py-1 border rounded-full text-sm font-semibold ${styles[status]}`}
    >
      {labels[status]}
    </span>
  )
}
