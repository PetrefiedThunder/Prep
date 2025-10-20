import { useEffect, useState } from 'react';

type Stats = { bookings: number };

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch('/api/dashboard')
      .then((r) => r.json())
      .then(setStats)
      .catch(() => setStats(null));
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold">Dashboard</h1>
      {stats ? <p>Bookings: {stats.bookings}</p> : <p>Loading...</p>}
    </div>
  );
}
