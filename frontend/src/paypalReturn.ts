/**
 * PayPal appends its own parameters to the configured return/cancel URL, e.g.
 *   http://localhost:5173/?token=8AB12345&PayerID=XYZ
 *   http://localhost:5173/?cancelled=1&token=8AB12345
 *
 * This helper is deliberately pure so the return handling can be tested without
 * a browser. It exposes parameter *names* for diagnostics but never logs values.
 */
export type PayPalReturn = {
  /** PayPal order token from the return URL (the order ID to capture). */
  token: string | null
  /** True when the buyer came back through cancel_url. */
  cancelled: boolean
  /** Query parameter names only — safe to log, never the values. */
  paramNames: string[]
}

export function parsePayPalReturn(search: string): PayPalReturn {
  const params = new URLSearchParams(search ?? "")
  const rawToken = params.get("token")
  const token = rawToken && rawToken.trim() !== "" ? rawToken.trim() : null

  return {
    token,
    cancelled: params.get("cancelled") === "1",
    paramNames: Array.from(params.keys()),
  }
}
