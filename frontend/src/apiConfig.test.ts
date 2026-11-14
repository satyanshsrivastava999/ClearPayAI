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
})

