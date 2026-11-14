/**
 * ClearPay AI — API Configuration
 *
 * Resolves the backend API base URL:
 * - In development: defaults to http://127.0.0.1:8000 (preserving local dev behavior).
 * - In production: uses VITE_API_BASE_URL (configured in Vercel project environment).
 * - Ensures production builds never inadvertently call localhost without warning.
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
        cleaned + ". Ensure VITE_API_BASE_URL in Vercel points to your deployed Render service."
      )
    }
    return cleaned
  }

  // If in production without explicit VITE_API_BASE_URL, avoid defaulting to localhost
  if (isProd) {
    console.warn(
      "[ClearPay AI] VITE_API_BASE_URL is not set in production. " +
      "Set VITE_API_BASE_URL in your Vercel project settings to your Render backend URL."
    )
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

