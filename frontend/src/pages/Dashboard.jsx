import { useEffect, useState } from 'react';
import axios from 'axios';

export default function Dashboard() {
  const [certs, setCerts] = useState([]);

  useEffect(() => {
    axios
      .get(`${import.meta.env.VITE_API_BASE_URL}/admin/certs`)
      .then((res) => setCerts(res.data))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Cert Approvals</h1>
      <ul className="space-y-2">
        {certs.map((c) => (
          <li key={c.id} className="border p-2 rounded">
            {c.name} - Level {c.cert_level}
          </li>
        ))}
      </ul>
    </div>
  );
}
