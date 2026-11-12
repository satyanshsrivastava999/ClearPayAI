import { describe, expect, it } from "vitest"
import {
  formatDocumentItem,
  validateFollowUpQuestion,
  validateIncidentForm,
  type DocumentChecklistItem,
  type IncidentFormInputs,
} from "./aiCopilot"

describe("validateIncidentForm", () => {
  it("accepts valid inputs for a FAILED incident", () => {
    const input: IncidentFormInputs = {
      provider: "PayPal",
      status: "FAILED",
      errorCode: "INSTRUMENT_DECLINED",
      errorMessage: "The instrument presented was declined.",
      amount: "10.00",
      currency: "USD",
      previousAttempts: 1,
      incidentDescription: "Payment failed during sandbox test.",
    }
    const result = validateIncidentForm(input)
    expect(result.valid).toBe(true)
    expect(result.error).toBeUndefined()
  })

  it("accepts DECLINED, PENDING, and ON_HOLD statuses", () => {
    for (const status of ["DECLINED", "PENDING", "ON_HOLD", "declined"]) {
      const res = validateIncidentForm({
        provider: "PayPal",
        status,
        previousAttempts: 0,
        incidentDescription: "",
      })
      expect(res.valid).toBe(true)
    }
  })

  it("rejects invalid status", () => {
    const res = validateIncidentForm({
      provider: "PayPal",
      status: "COMPLETED",
      previousAttempts: 0,
      incidentDescription: "",
    })
    expect(res.valid).toBe(false)
    expect(res.error).toContain("Status must be one of")
  })

  it("rejects negative previous attempts", () => {
    const res = validateIncidentForm({
      provider: "PayPal",
      status: "FAILED",
      previousAttempts: -1,
      incidentDescription: "",
    })
    expect(res.valid).toBe(false)
    expect(res.error).toContain("cannot be negative")
  })

  it("rejects non-numeric or negative amount", () => {
    const resNaN = validateIncidentForm({
      provider: "PayPal",
      status: "FAILED",
      amount: "invalid-amount",
      previousAttempts: 0,
      incidentDescription: "",
    })
    expect(resNaN.valid).toBe(false)

    const resNeg = validateIncidentForm({
      provider: "PayPal",
      status: "FAILED",
      amount: "-10.00",
      previousAttempts: 0,
      incidentDescription: "",
    })
    expect(resNeg.valid).toBe(false)
  })

  it("rejects amount with more than 2 decimal places", () => {
    const res = validateIncidentForm({
      provider: "PayPal",
      status: "FAILED",
      amount: "10.555",
      previousAttempts: 0,
      incidentDescription: "",
    })
    expect(res.valid).toBe(false)
    expect(res.error).toContain("at most 2 decimal places")
  })

  it("rejects invalid currency code", () => {
    const res = validateIncidentForm({
      provider: "PayPal",
      status: "FAILED",
      currency: "US",
      previousAttempts: 0,
      incidentDescription: "",
    })
    expect(res.valid).toBe(false)
    expect(res.error).toContain("3-letter ISO code")
  })
})

describe("validateFollowUpQuestion", () => {
  it("accepts valid follow-up question", () => {
    const res = validateFollowUpQuestion("What information should I collect before contacting the provider?")
    expect(res.valid).toBe(true)
  })

  it("rejects empty or whitespace-only questions", () => {
    expect(validateFollowUpQuestion("").valid).toBe(false)
    expect(validateFollowUpQuestion("   ").valid).toBe(false)
  })

  it("rejects oversized questions (>2000 chars)", () => {
    const longQuestion = "a".repeat(2001)
    const res = validateFollowUpQuestion(longQuestion)
    expect(res.valid).toBe(false)
    expect(res.error).toContain("2000 characters")
  })
})

describe("formatDocumentItem", () => {
  it("formats document checklist item correctly", () => {
    const doc: DocumentChecklistItem = {
      document: "Bank Statement",
      reason: "To verify funding instrument validity",
      condition: "If bank declines charge",
      where_to_obtain: "Direct from buyer bank portal",
      official_source: "https://developer.paypal.com/docs/api/orders/v2/#errors",
      provider: "PayPal",
    }
    const formatted = formatDocumentItem(doc)
    expect(formatted.name).toBe("Bank Statement")
    expect(formatted.purpose).toBe("To verify funding instrument validity")
    expect(formatted.condition).toBe("If bank declines charge")
    expect(formatted.nextStep).toBe("Direct from buyer bank portal")
    expect(formatted.source).toBe("https://developer.paypal.com/docs/api/orders/v2/#errors")
    expect(formatted.provider).toBe("PayPal")
  })

  it("safely handles missing optional fields without fabricating", () => {
    const doc: DocumentChecklistItem = {
      document: "Account Details",
    }
    const formatted = formatDocumentItem(doc)
    expect(formatted.name).toBe("Account Details")
    expect(formatted.condition).toBe("")
    expect(formatted.nextStep).toBe("")
    expect(formatted.source).toBe("")
  })
})

