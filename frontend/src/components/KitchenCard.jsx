import { Link } from 'react-router-dom';

export default function KitchenCard({ kitchen }) {
  return (
    <div className="border p-4 rounded shadow">
      <h2 className="text-xl font-bold mb-2">{kitchen.name}</h2>
      <p className="mb-2">{kitchen.address}</p>
      <Link
        className="text-blue-500 hover:underline"
        to={`/kitchens/${kitchen.id}`}
      >
        View Details
      </Link>
    </div>
  );
}
