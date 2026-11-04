export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      ...options,
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "X-Mikuy-Request": "1",
        ...options.headers,
      },
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw e;
    window.dispatchEvent(new Event("connection-lost"));
    throw new ApiError(
      0,
      "No hay conexión con Mikuy. Comprueba internet e inténtalo de nuevo. Tu formulario sigue abierto.",
    );
  }
  window.dispatchEvent(new Event("connection-restored"));
  if (!response.ok) {
    const data = await response
      .json()
      .catch(() => ({ detail: "No se pudo completar la solicitud." }));
    if (response.status === 401 && !path.startsWith("/auth/"))
      window.dispatchEvent(new Event("session-expired"));
    throw new ApiError(
      response.status,
      typeof data.detail === "string"
        ? data.detail
        : "Revisa los datos e inténtalo de nuevo.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export const body = (method: string, value?: unknown): RequestInit => ({
  method,
  body: value === undefined ? undefined : JSON.stringify(value),
});
export const soles = (n: number) =>
  new Intl.NumberFormat("es-PE", { style: "currency", currency: "PEN" }).format(
    n,
  );
export const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Lima",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
export const isISODate = (value: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(value + "T12:00:00Z");
  return (
    Number.isFinite(parsed.getTime()) &&
    parsed.toISOString().slice(0, 10) === value
  );
};
export const addDays = (date: string, offset: number) => {
  if (!isISODate(date) || !Number.isFinite(offset)) return "";
  const d = new Date(date + "T12:00:00");
  d.setDate(d.getDate() + offset);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export const formatDate = (date: string) =>
  isISODate(date)
    ? new Intl.DateTimeFormat("es-PE", {
        day: "numeric",
        month: "long",
      }).format(new Date(date + "T12:00:00"))
    : "Fecha no disponible";
