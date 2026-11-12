import { describe, expect, it } from "vitest"

import { parsePayPalReturn } from "./paypalReturn"

describe("parsePayPalReturn", () => {
  it("reads the token PayPal appends to the return URL", () => {
    const result = parsePayPalReturn("?token=8AB12345&PayerID=XYZ123")

    expect(result.token).toBe("8AB12345")
    expect(result.cancelled).toBe(false)
  })

  it("reads the token even when PayerID is absent", () => {
    const result = parsePayPalReturn("?token=8AB12345")

    expect(result.token).toBe("8AB12345")
    expect(result.cancelled).toBe(false)
  })

  it("flags a cancel return and keeps the token when PayPal sends one", () => {
    const result = parsePayPalReturn("?cancelled=1&token=8AB12345")

    expect(result.cancelled).toBe(true)
    expect(result.token).toBe("8AB12345")
  })

  it("flags a cancel return without a token", () => {
    const result = parsePayPalReturn("?cancelled=1")

    expect(result.cancelled).toBe(true)
    expect(result.token).toBeNull()
  })

  it("returns no token for a plain page load", () => {
    const result = parsePayPalReturn("")

    expect(result.token).toBeNull()
    expect(result.cancelled).toBe(false)
    expect(result.paramNames).toEqual([])
  })

  it("does not create a token from unrelated query parameters", () => {
    const result = parsePayPalReturn("?demo=true&foo=bar")

    expect(result.token).toBeNull()
    expect(result.cancelled).toBe(false)
  })

  it("exposes parameter names only for diagnostics", () => {
    const result = parsePayPalReturn("?token=8AB12345&PayerID=XYZ123")

    expect(result.paramNames).toEqual(["token", "PayerID"])
  })
})
