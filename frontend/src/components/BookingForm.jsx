import { useState } from 'react';
import axios from 'axios';

export default function BookingForm({ kitchenId }) {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    axios
      .post(`${import.meta.env.VITE_API_BASE_URL}/bookings`, {
        user_id: 2,
        kitchen_id: kitchenId,
        start_time: new Date(),
        end_time: new Date(),
      })
      .then(() => setSubmitted(true))
      .catch((err) => console.error(err));
  };

  if (submitted) return <div className="text-green-600">Booking Submitted!</div>;

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <button
        type="submit"
        className="px-4 py-2 bg-blue-500 text-white rounded"
      >
        Book Now
      </button>
    </form>
  );
}
