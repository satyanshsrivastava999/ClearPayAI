/**
 * ClearPay AI — API Configuration
 *
 * Resolves the backend API base URL:
 * - In development: defaults to http://127.0.0.1:8000 (preserving local dev behavior).
 * - In production: uses same-origin relative URLs ("") by default for Vercel
 *   multi-service deployment where /api/* and /health are routed directly to clearpayai-backend.
 * - Supports VITE_API_BASE_URL if explicitly configured (warns if targeting localhost in production).
 */

export function getApiBaseUrl(): string {
  const metaEnv = (import.meta as unknown as { env?: Record<string, string | boolean> }).env || {}
  const envUrl = typeof metaEnv.VITE_API_BASE_URL === "string" ? metaEnv.VITE_API_BASE_URL.trim() : ""

  const isProd = metaEnv.PROD === true || metaEnv.MODE === "production"

  if (envUrl) {
    const cleaned = envUrl.replace(/\/+$/, "")
    if (isProd && (cleaned.includes("localhost") || cleaned.includes("127.0.0.1"))) {
      console.warn(
        "[ClearPay AI Warning] Production build is targeting a localhost URL: " +
        cleaned + ". In Vercel multi-service deployment, leave VITE_API_BASE_URL empty to use same-origin /api routes."
      )
    }
    return cleaned
  }

  // In production, default to same-origin relative URLs ("") for Vercel multi-service routing
  if (isProd) {
    return ""
  }

  // Default for local development
  return "http://127.0.0.1:8000"
}

export function apiUrl(endpoint: string): string {
  const base = getApiBaseUrl()
  const path = endpoint.startsWith("/") ? endpoint : `/${endpoint}`
  return `${base}${path}`
}

