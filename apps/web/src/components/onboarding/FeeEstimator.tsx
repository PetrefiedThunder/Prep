import { FormEvent, useEffect, useMemo, useState } from 'react';

type LineItem = {
  name: string;
  amountCents: number;
  category?: string;
};

type FeeEstimatorProps = {
  currency?: string;
  defaultItems?: LineItem[];
  onEstimate?: (summary: { totalCents: number; lineItems: LineItem[] }) => void;
  className?: string;
};

const formatterCache = new Map<string, Intl.NumberFormat>();

function formatCurrency(amountCents: number, currency: string) {
  const amount = amountCents / 100;
  if (!formatterCache.has(currency)) {
    formatterCache.set(
      currency,
      new Intl.NumberFormat(undefined, { style: 'currency', currency, currencyDisplay: 'symbol', maximumFractionDigits: 2 })
    );
  }
  return formatterCache.get(currency)!.format(amount);
}

export function FeeEstimator({ currency = 'usd', defaultItems = [], onEstimate, className }: FeeEstimatorProps) {
  const [lineItems, setLineItems] = useState<LineItem[]>(defaultItems);
  const [itemName, setItemName] = useState('');
  const [itemCategory, setItemCategory] = useState('');
  const [itemAmount, setItemAmount] = useState('');

  const totalCents = useMemo(
    () => lineItems.reduce((acc, item) => acc + (Number.isFinite(item.amountCents) ? item.amountCents : 0), 0),
    [lineItems]
  );

  useEffect(() => {
    onEstimate?.({ totalCents, lineItems });
  }, [lineItems, onEstimate, totalCents]);

  const addItem = (event: FormEvent) => {
    event.preventDefault();
    if (!itemName.trim()) {
      return;
    }
    const parsedAmount = Math.round(Number(itemAmount || 0) * 100);
    if (!Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      return;
    }
    setLineItems((prev) => [
      ...prev,
      {
        name: itemName.trim(),
        amountCents: parsedAmount,
        category: itemCategory.trim() || undefined,
      },
    ]);
    setItemName('');
    setItemAmount('');
    setItemCategory('');
  };

  const removeItem = (index: number) => {
    setLineItems((prev) => prev.filter((_, idx) => idx !== index));
  };

  return (
    <section className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className ?? ''}`}>
      <header className="mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Fee estimator</h2>
        <p className="text-sm text-slate-500">
          Model hourly kitchen costs, health department filing fees, security deposits, and more. Adjust line items to
          preview the total at checkout.
        </p>
      </header>

      <form className="mb-4 grid gap-3 md:grid-cols-4" onSubmit={addItem}>
        <label className="flex flex-col text-sm text-slate-600 md:col-span-2">
          Item name
          <input
            className="mt-1 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            value={itemName}
            onChange={(event) => setItemName(event.target.value)}
            placeholder="e.g. Fire inspection"
            required
          />
        </label>
        <label className="flex flex-col text-sm text-slate-600">
          Category
          <input
            className="mt-1 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            value={itemCategory}
            onChange={(event) => setItemCategory(event.target.value)}
            placeholder="Permit, inspection, deposit"
          />
        </label>
        <label className="flex flex-col text-sm text-slate-600">
          Amount ({currency.toUpperCase()})
          <input
            type="number"
            min="0"
            step="0.01"
            inputMode="decimal"
            className="mt-1 rounded-md border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
            value={itemAmount}
            onChange={(event) => setItemAmount(event.target.value)}
            placeholder="0.00"
            required
          />
        </label>
        <div className="flex items-end">
          <button
            type="submit"
            className="w-full rounded-md bg-emerald-500 px-3 py-2 text-sm font-semibold text-white shadow hover:bg-emerald-600"
          >
            Add line item
          </button>
        </div>
      </form>

      <div className="overflow-hidden rounded-lg border border-slate-200">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left font-medium text-slate-600">
            <tr>
              <th className="px-4 py-2">Item</th>
              <th className="px-4 py-2">Category</th>
              <th className="px-4 py-2 text-right">Amount</th>
              <th className="px-4 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {lineItems.map((item, index) => (
              <tr key={`${item.name}-${index}`}>
                <td className="px-4 py-2 font-medium text-slate-900">{item.name}</td>
                <td className="px-4 py-2 text-slate-500">{item.category ?? '—'}</td>
                <td className="px-4 py-2 text-right text-slate-900">{formatCurrency(item.amountCents, currency)}</td>
                <td className="px-4 py-2 text-right">
                  <button
                    type="button"
                    onClick={() => removeItem(index)}
                    className="rounded-md border border-transparent px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
            {lineItems.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-sm text-slate-500">
                  Add a line item to preview projected onboarding costs.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <footer className="mt-4 flex items-center justify-between text-sm">
        <span className="text-slate-500">Total estimated fees</span>
        <strong className="text-lg text-slate-900">{formatCurrency(totalCents, currency)}</strong>
      </footer>
    </section>
  );
}

export type { LineItem };
