import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import KitchenBrowser from './pages/KitchenBrowser';
import BookingCheckout from './pages/BookingCheckout';
import Dashboard from './pages/Dashboard';
import AdminPortal from './pages/AdminPortal';
import AnalyticsPortal from './pages/AnalyticsPortal';

export default function App() {
  return (
    <BrowserRouter>
      <nav className="p-4 bg-gray-200 flex gap-4">
        <Link to="/">Home</Link>
        <Link to="/kitchens">Kitchens</Link>
        <Link to="/checkout">Checkout</Link>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/admin">Admin</Link>
        <Link to="/analytics">Analytics</Link>
      </nav>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/kitchens" element={<KitchenBrowser />} />
        <Route path="/checkout" element={<BookingCheckout />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/admin" element={<AdminPortal />} />
        <Route path="/analytics" element={<AnalyticsPortal />} />
      </Routes>
    </BrowserRouter>
  );
}
