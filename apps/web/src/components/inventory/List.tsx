import { useEffect, useState } from 'react';

export type InventoryTransfer = {
  id: string;
  to_kitchen_id: string;
  approval_status: 'pending' | 'approved' | 'declined' | 'cancelled';
  quantity: number | string;
  unit: string;
  expiry_date: string | null;
};

export type InventoryLot = {
  id: string;
  quantity: number | string;
  unit: string;
  expiry_date: string | null;
  received_at: string | null;
};

export type SupplierSummary = {
  id: string;
  name: string;
  contact_email?: string | null;
  phone_number?: string | null;
};

export type InventoryItem = {
  id: string;
  kitchen_id: string;
  host_id: string;
  name: string;
  sku?: string | null;
  category?: string | null;
  unit: string;
  total_quantity: number | string;
  par_level?: number | string | null;
  oldest_expiry?: string | null;
  shared_shelf_available: boolean;
  supplier?: SupplierSummary | null;
  lots: InventoryLot[];
  pending_transfers: InventoryTransfer[];
};

export interface InventoryListProps {
  kitchenId?: string;
}

function normalizeNumber(value: number | string | undefined | null): number | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatQuantity(value: number | string): string {
  const normalized = normalizeNumber(value);
  if (normalized === null) {
    return '—';
  }
  if (Number.isInteger(normalized)) {
    return normalized.toString();
  }
  return normalized.toFixed(2);
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '—';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '—';
  }
  return date.toLocaleDateString();
}

async function fetchInventoryItems(kitchenId?: string): Promise<InventoryItem[]> {
  const query = kitchenId ? `?kitchen_id=${encodeURIComponent(kitchenId)}` : '';
  const response = await fetch(`/inventory/items${query}`);
  if (!response.ok) {
    throw new Error(`Failed to load inventory (${response.status})`);
  }
  return (await response.json()) as InventoryItem[];
}

export function InventoryList({ kitchenId }: InventoryListProps) {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchInventoryItems(kitchenId);
        if (!cancelled) {
          setItems(data);
        }
      } catch (err) {
        console.error('Failed to fetch inventory', err);
        if (!cancelled) {
          setError('Unable to load inventory right now. Please try again later.');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [kitchenId]);

  if (loading) {
    return <div className="rounded border border-slate-200 bg-white p-4 text-slate-600">Loading inventory…</div>;
  }

  if (error) {
    return (
      <div className="rounded border border-rose-200 bg-rose-50 p-4 text-rose-900" role="alert">
        {error}
      </div>
    );
  }

  if (items.length === 0) {
    return <div className="rounded border border-slate-200 bg-white p-4 text-slate-500">No inventory items found.</div>;
  }

  return (
    <div className="overflow-hidden rounded border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
              Item
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
              Total on hand
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
              Oldest expiry
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
              Supplier
            </th>
            <th scope="col" className="px-4 py-3 text-left text-sm font-semibold text-slate-700">
              Shared shelf offers
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-200">
          {items.map((item) => {
            const quantityLabel = `${formatQuantity(item.total_quantity)} ${item.unit}`;
            const supplierLabel = item.supplier?.name ?? '—';
            const pendingOffers = item.pending_transfers.filter((transfer) => transfer.approval_status === 'pending');
            const offerLabel = pendingOffers.length > 0 ? `${pendingOffers.length} pending` : item.shared_shelf_available ? 'Available' : '—';
            return (
              <tr key={item.id} className="hover:bg-slate-50">
                <td className="px-4 py-3">
                  <div className="flex flex-col">
                    <span className="font-medium text-slate-900">{item.name}</span>
                    <span className="text-sm text-slate-500">
                      {item.sku ? `SKU ${item.sku}` : item.category ?? 'Uncategorised'}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-700">{quantityLabel}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{formatDate(item.oldest_expiry)}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{supplierLabel}</td>
                <td className="px-4 py-3 text-sm text-slate-700">{offerLabel}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-500">
        Showing {items.length} inventory items. Expiry dates shown follow your browser locale.
      </div>
    </div>
  );
}

export default InventoryList;
