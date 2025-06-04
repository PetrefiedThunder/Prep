import { useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import axios from 'axios';
import BookingForm from '../components/BookingForm.jsx';

export default function KitchenDetail() {
  const { id } = useParams();
  const [kitchen, setKitchen] = useState(null);

  useEffect(() => {
    axios
      .get(`${import.meta.env.VITE_API_BASE_URL}/kitchens/${id}`)
      .then((res) => setKitchen(res.data))
      .catch((err) => console.error(err));
  }, [id]);

  if (!kitchen) return <div>Loading...</div>;

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-2">{kitchen.name}</h1>
      <p className="mb-2">{kitchen.address}</p>
      <p className="mb-2">Cert Level: {kitchen.cert_level}</p>
      <p className="mb-4">Pricing: ${kitchen.pricing} / hr</p>
      <BookingForm kitchenId={kitchen.id} />
    </div>
  );
}
