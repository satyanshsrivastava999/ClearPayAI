import { type AIAnalysisResponse } from "./aiCopilot"

export type NavItem = "overview" | "copilot" | "transactions" | "cases" | "settings"

export type PaymentState =
  | "idle"
  | "creating"
  | "awaiting_approval"
  | "processing"
  | "completed"
  | "cancelled"
  | "declined"
  | "failed"
  | "simulated_completed"

export interface TransactionRecord {
  id: string
  orderId: string
  amount: string
  currency: string
  status: PaymentState
  captureId?: string
  createdAt: string
  failureReason?: string
  isDemo?: boolean
}

export interface RecoveryCaseRecord {
  id: string
  orderId?: string
  status: "Active Analysis" | "Action Required" | "Resolved"
  title: string
  summary: string
  actionsCount: number
  createdAt: string
  analysis: AIAnalysisResponse
  isDemo?: boolean
}

export interface ActivityItem {
  id: string
  timestamp: string
  type: "payment" | "copilot" | "system"
  description: string
  badge?: string
}

export interface DashboardStats {
  totalTransactions: number
  successfulPayments: number
  failedPayments: number
  pendingPayments: number
  recoveryCases: number
}

export interface SystemStatus {
  status: string
  environment: string
  paypal_configured: boolean
  gemini_configured: boolean
  demo_mode: boolean
  model: string
}

/**
 * Clearly labeled sample data used ONLY when user opts into Demo Data preview.
 */
export const DEMO_TRANSACTIONS: TransactionRecord[] = [
  {
    id: "tx-demo-101",
    orderId: "5O198114181717017",
    amount: "45.00",
    currency: "USD",
    status: "completed",
    captureId: "8AB12345678901234",
    createdAt: "2026-11-12 18:24 UTC",
    isDemo: true,
  },
  {
    id: "tx-demo-102",
    orderId: "9K234114181717022",
    amount: "10.00",
    currency: "USD",
    status: "failed",
    failureReason: "INSTRUMENT_DECLINED",
    createdAt: "2026-11-12 18:45 UTC",
    isDemo: true,
  },
  {
    id: "tx-demo-103",
    orderId: "3A789114181717088",
    amount: "120.50",
    currency: "USD",
    status: "declined",
    failureReason: "PAYER_DECLINED",
    createdAt: "2026-11-12 19:10 UTC",
    isDemo: true,
  },
  {
    id: "tx-demo-104",
    orderId: "2X555114181717044",
    amount: "25.00",
    currency: "USD",
    status: "awaiting_approval",
    createdAt: "2026-11-12 19:30 UTC",
    isDemo: true,
  },
]

export const DEMO_CASES: RecoveryCaseRecord[] = [
  {
    id: "case-demo-1",
    orderId: "9K234114181717022",
    status: "Action Required",
    title: "Funding Instrument Declined (INSTRUMENT_DECLINED)",
    summary: "Sandbox payment rejected by card issuer risk check. Buyer action needed to provide alternative funding method.",
    actionsCount: 3,
    createdAt: "2026-11-12 18:46 UTC",
    isDemo: true,
    analysis: {
      issue_title: "PayPal Payment Failure: INSTRUMENT_DECLINED",
      summary: "A sandbox payment attempt failed due to INSTRUMENT_DECLINED error from PayPal.",
      confirmed_facts: ["Error code: INSTRUMENT_DECLINED", "Provider: PayPal", "Status: FAILED"],
      possible_causes: [
        {
          description: "Card rejected by card issuer or PayPal risk filter",
          evidence: "PayPal returned INSTRUMENT_DECLINED",
          confidence: 85,
        },
      ],
      recommended_actions: [
        "Prompt buyer to select a different payment instrument",
        "Restart checkout flow without automated immediate retry",
      ],
      retry_guidance: "Do not retry with same card. Request alternative payment method.",
      document_checklist: [
        {
          document: "Bank Statement",
          reason: "To verify card validity and sufficient balance",
          condition: "If customer questions decline",
          where_to_obtain: "Cardholder bank app",
          official_source: "https://developer.paypal.com/docs/api/orders/v2/#errors",
        },
      ],
      customer_facing_message: "Your payment method was declined. Please try another card or bank account.",
      additional_info_needed: "API response headers with PayPal-Debug-Id",
      source_references: ["https://developer.paypal.com/docs/api/orders/v2/#errors"],
    },
  },
]

