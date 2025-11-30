export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Welcome to PrepChef
        </h1>
        <p className="text-xl text-gray-600">
          The marketplace for commercial kitchen rentals
        </p>
      </div>

      <div className="prose prose-lg mx-auto space-y-6">
        <p className="text-gray-700 leading-relaxed">
          PrepChef connects culinary entrepreneurs with available commercial kitchen
          space. Whether you&apos;re a food truck operator, caterer, or home baker looking
          to scale up, we help you find certified, licensed kitchen facilities by the hour.
        </p>

        <p className="text-gray-700 leading-relaxed">
          Our platform makes it simple for kitchen owners to list their space and manage
          bookings, while renters can easily search, book, and pay for kitchen time. All
          payments are handled securely through our platform, with direct payouts to
          kitchen owners.
        </p>

        <p className="text-gray-700 leading-relaxed">
          Get started today by browsing available kitchens in your area or list your
          own commercial kitchen to start earning revenue from unused time slots.
        </p>

        <div className="flex gap-4 justify-center mt-8">
          <button className="bg-gray-900 text-white px-6 py-3 rounded-lg font-semibold hover:bg-gray-800 transition">
            Find a Kitchen
          </button>
          <button className="border-2 border-gray-900 text-gray-900 px-6 py-3 rounded-lg font-semibold hover:bg-gray-50 transition">
            List Your Kitchen
          </button>
        </div>
      </div>
    </div>
  );
}
