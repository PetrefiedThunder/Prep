import { useState } from 'react';

export default function BookingCheckout() {
  const [status, setStatus] = useState<string | null>(null);

  const submit = async () => {
    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });
      setStatus(res.ok ? 'Booked!' : 'Failed');
    } catch {
      setStatus('Failed');
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold">Checkout</h1>
      <button className="mt-2 px-4 py-2 bg-blue-500 text-white" onClick={submit}>
        Confirm Booking
      </button>
      {status && <p className="mt-2">{status}</p>}
    </div>
  );
}
