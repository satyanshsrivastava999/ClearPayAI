/**
 * Helper types and pure utility functions for Payment Recovery Copilot.
 */

export type AICause = {
  description: string
  evidence: string
  confidence: number
}

export type DocumentChecklistItem = {
  document?: string
  name?: string
  reason?: string
  purpose?: string
  condition?: string
  where_to_obtain?: string
  recommended_next_step?: string
  official_source?: string
  provider?: string
}

export type AIAnalysisResponse = {
  issue_title: string
  summary: string
  confirmed_facts: string[]
  possible_causes: AICause[]
  recommended_actions: string[]
  retry_guidance: string
  document_checklist: DocumentChecklistItem[]
  customer_facing_message: string
  additional_info_needed: string
  source_references: string[]
}

export type IncidentFormInputs = {
  provider: string
  status: string
  errorCode?: string
  errorMessage?: string
  amount?: string
  currency?: string
  previousAttempts: number
  incidentDescription: string
  additionalDiagnostics?: string
}

export type ValidationResult = {
  valid: boolean
  error?: string
}

/**
 * Validate incident submission form inputs.
 */
export function validateIncidentForm(inputs: IncidentFormInputs): ValidationResult {
  const validStatuses = ["FAILED", "DECLINED", "PENDING", "ON_HOLD"]
  if (!validStatuses.includes(inputs.status.toUpperCase())) {
    return {
      valid: false,
      error: `Status must be one of: ${validStatuses.join(", ")}`,
    }
  }

  if (inputs.previousAttempts < 0 || isNaN(inputs.previousAttempts)) {
    return {
      valid: false,
      error: "Previous attempts count cannot be negative.",
    }
  }

  if (inputs.amount && inputs.amount.trim() !== "") {
    const num = Number(inputs.amount.trim())
    if (isNaN(num) || num <= 0) {
      return {
        valid: false,
        error: "Amount must be a valid positive number.",
      }
    }
    const parts = inputs.amount.trim().split(".")
    if (parts.length > 1 && parts[1].length > 2) {
      return {
        valid: false,
        error: "Amount can have at most 2 decimal places.",
      }
    }
  }

  if (inputs.currency && inputs.currency.trim() !== "") {
    const curr = inputs.currency.trim().toUpperCase()
    if (curr.length !== 3 || !/^[A-Z]{3}$/.test(curr)) {
      return {
        valid: false,
        error: "Currency must be a 3-letter ISO code (e.g. USD).",
      }
    }
  }

  return { valid: true }
}

/**
 * Validate follow-up question before submission.
 */
export function validateFollowUpQuestion(question: string): ValidationResult {
  const trimmed = question.trim()
  if (!trimmed) {
    return {
      valid: false,
      error: "Follow-up question cannot be empty.",
    }
  }
  if (trimmed.length > 2000) {
    return {
      valid: false,
      error: "Question exceeds maximum length of 2000 characters.",
    }
  }
  return { valid: true }
}

export type FormattedDocument = {
  name: string
  purpose: string
  condition: string
  nextStep: string
  source: string
  provider: string
}

/**
 * Safely format conditional document checklist item without inventing facts.
 */
export function formatDocumentItem(doc: DocumentChecklistItem): FormattedDocument {
  const name = (doc.document || doc.name || "Required Document / Information").trim()
  const purpose = (doc.purpose || doc.reason || "Provider verification").trim()
  const condition = (doc.condition || "").trim()
  const nextStep = (doc.recommended_next_step || doc.where_to_obtain || "").trim()
  const source = (doc.official_source || "").trim()
  const provider = (doc.provider || "").trim()

  return {
    name,
    purpose,
    condition,
    nextStep,
    source,
    provider,
  }
}

