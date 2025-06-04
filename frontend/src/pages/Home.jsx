import { useEffect, useState } from 'react';
import axios from 'axios';
import KitchenCard from '../components/KitchenCard.jsx';

export default function Home() {
  const [kitchens, setKitchens] = useState([]);

  useEffect(() => {
    axios
      .get(`${import.meta.env.VITE_API_BASE_URL}/kitchens`)
      .then((res) => setKitchens(res.data))
      .catch((err) => console.error(err));
  }, []);

  return (
    <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
      {kitchens.map((k) => (
        <KitchenCard key={k.id} kitchen={k} />
      ))}
    </div>
  );
}
