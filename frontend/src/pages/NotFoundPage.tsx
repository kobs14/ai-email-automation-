import { Link } from 'react-router-dom';
import { Home } from 'lucide-react';

export function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center">
      <h1 className="text-6xl font-bold text-gray-300">404</h1>
      <p className="mt-4 text-lg text-gray-600">Page not found</p>
      <Link
        to="/dashboard"
        className="mt-6 btn-primary inline-flex items-center gap-2"
      >
        <Home className="w-4 h-4" />
        Go to Dashboard
      </Link>
    </div>
  );
}
