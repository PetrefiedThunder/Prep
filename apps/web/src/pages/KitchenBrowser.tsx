import { useEffect, useState } from 'react';

type Kitchen = { id: string; name: string };

export default function KitchenBrowser() {
  const [kitchens, setKitchens] = useState<Kitchen[]>([]);

  useEffect(() => {
    fetch('/api/kitchens')
      .then((res) => res.json())
      .then(setKitchens)
      .catch(() => setKitchens([]));
  }, []);

  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold">Browse Kitchens</h1>
      <ul className="mt-2 list-disc pl-6">
        {kitchens.map((k) => (
          <li key={k.id}>{k.name}</li>
        ))}
      </ul>
    </div>
  );
}
