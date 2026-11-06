// In development Vite proxies /api to the backend, so the base is empty.
// In production set VITE_API_URL to your hosted backend address.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

export async function api(path, body) {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}
