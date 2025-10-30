import { useEffect, useMemo, useState } from 'react';

import type { InventoryItem } from './List';

export interface InventoryAlertsProps {
  kitchenId?: string;
  expiryThresholdDays?: number;
}

function normalizeNumber(value: number | string | undefined | null): number | null {
  if (value === undefined || value === null) {
    return null;
  }
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : null;
  }
  const parsed = Number.parseFloat(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function formatQuantity(value: number | string | undefined | null): string {
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

export function InventoryAlerts({ kitchenId, expiryThresholdDays = 3 }: InventoryAlertsProps) {
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
        console.error('Failed to load inventory alerts', err);
        if (!cancelled) {
          setError('Unable to load inventory alerts.');
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

  const lowStockItems = useMemo(() => {
    return items.filter((item) => {
      const par = normalizeNumber(item.par_level);
      const total = normalizeNumber(item.total_quantity) ?? 0;
      return par !== null && total < par;
    });
  }, [items]);

  const expiringSoon = useMemo(() => {
    const now = Date.now();
    const thresholdMs = expiryThresholdDays * 24 * 60 * 60 * 1000;
    return items
      .filter((item) => item.oldest_expiry)
      .filter((item) => {
        const expiry = item.oldest_expiry ? new Date(item.oldest_expiry).getTime() : Number.NaN;
        if (Number.isNaN(expiry)) {
          return false;
        }
        return expiry - now <= thresholdMs;
      });
  }, [items, expiryThresholdDays]);

  const sharedShelfOffers = useMemo(() => {
    return items.filter((item) => item.pending_transfers.some((transfer) => transfer.approval_status === 'pending'));
  }, [items]);

  if (loading) {
    return <div className="rounded border border-slate-200 bg-white p-4 text-slate-600">Loading alerts…</div>;
  }

  if (error) {
    return (
      <div className="rounded border border-rose-200 bg-rose-50 p-4 text-rose-900" role="alert">
        {error}
      </div>
    );
  }

  if (lowStockItems.length === 0 && expiringSoon.length === 0 && sharedShelfOffers.length === 0) {
    return <div className="rounded border border-emerald-200 bg-emerald-50 p-4 text-emerald-800">Inventory looks healthy. No alerts right now.</div>;
  }

  return (
    <div className="space-y-4">
      {lowStockItems.length > 0 && (
        <section className="rounded border border-amber-200 bg-amber-50 p-4">
          <header className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-amber-900">Low stock</h3>
            <span className="text-xs text-amber-800">{lowStockItems.length} items</span>
          </header>
          <ul className="space-y-1 text-sm text-amber-900">
            {lowStockItems.map((item) => {
              const total = formatQuantity(item.total_quantity);
              const par = formatQuantity(item.par_level ?? null);
              return (
                <li key={item.id} className="flex items-center justify-between">
                  <span className="font-medium">{item.name}</span>
                  <span className="text-xs">{total} / par {par}</span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {expiringSoon.length > 0 && (
        <section className="rounded border border-rose-200 bg-rose-50 p-4">
          <header className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-rose-900">Expiring soon</h3>
            <span className="text-xs text-rose-800">Within {expiryThresholdDays} days</span>
          </header>
          <ul className="space-y-1 text-sm text-rose-900">
            {expiringSoon.map((item) => {
              const expiryLabel = formatDate(item.oldest_expiry);
              const qty = formatQuantity(item.total_quantity);
              return (
                <li key={item.id} className="flex items-center justify-between">
                  <span className="font-medium">{item.name}</span>
                  <span className="text-xs">{qty} {item.unit} • expires {expiryLabel}</span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {sharedShelfOffers.length > 0 && (
        <section className="rounded border border-sky-200 bg-sky-50 p-4">
          <header className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-sky-900">Shared shelf offers</h3>
            <span className="text-xs text-sky-800">{sharedShelfOffers.length} items</span>
          </header>
          <ul className="space-y-2 text-sm text-sky-900">
            {sharedShelfOffers.map((item) => (
              <li key={item.id} className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{item.name}</span>
                  <span className="text-xs">{item.pending_transfers.length} pending offers</span>
                </div>
                <ul className="ml-4 space-y-0.5 text-xs text-sky-800">
                  {item.pending_transfers
                    .filter((transfer) => transfer.approval_status === 'pending')
                    .map((transfer) => {
                      const qty = formatQuantity(transfer.quantity);
                      const expiryLabel = formatDate(transfer.expiry_date);
                      return (
                        <li key={transfer.id}>
                          {qty} {transfer.unit} → kitchen {transfer.to_kitchen_id.slice(0, 6)} • expiry {expiryLabel}
                        </li>
                      );
                    })}
                </ul>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export default InventoryAlerts;
