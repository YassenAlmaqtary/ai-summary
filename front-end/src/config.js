// Central API base URL configuration
// Prefer environment variable via Vite; falls back to localhost
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9000';

// Helper to build full API URLs safely
export const apiUrl = (path = '/') => {
  const p = String(path || '/');
  if (p.startsWith('/')) return `${API_BASE_URL}${p}`;
  return `${API_BASE_URL}/${p}`;
};
