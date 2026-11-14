import { describe, it, expect } from "vitest"
import { getApiBaseUrl, apiUrl } from "./apiConfig"

describe("apiConfig", () => {
  it("resolves default API base URL in development", () => {
    const url = getApiBaseUrl()
    expect(url).toBeDefined()
    expect(typeof url).toBe("string")
  })

  it("constructs correct apiUrl with leading slash", () => {
    const full = apiUrl("/health")
    expect(full).toMatch(/\/health$/)
  })

  it("constructs correct apiUrl without leading slash", () => {
    const full = apiUrl("api/orders")
    expect(full).toMatch(/\/api\/orders$/)
  })

  it("constructs expected relative paths for same-origin production calls", () => {
    // When getApiBaseUrl returns empty string in production, paths must start with /
    const endpoints = [
      "/health",
      "/api/settings/status",
      "/api/orders",
      "/api/transactions",
      "/api/recovery-cases",
      "/api/dashboard/stats",
      "/api/activity",
      "/api/ai/analyze-payment",
      "/api/ai/follow-up",
    ]
    for (const ep of endpoints) {
      const url = apiUrl(ep)
      expect(url.endsWith(ep)).toBe(true)
    }
  })
})

