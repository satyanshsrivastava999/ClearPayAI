import { describe, expect, it } from "vitest"
import { renderToString } from "react-dom/server"
import React from "react"
import { Sidebar } from "./components/Sidebar"
import { Header } from "./components/Header"
import { OverviewPage, StatusBadge } from "./components/OverviewPage"
import { TransactionsPage } from "./components/TransactionsPage"
import { RecoveryCasesPage } from "./components/RecoveryCasesPage"
import { SettingsPage } from "./components/SettingsPage"
import { CopilotPage } from "./components/CopilotPage"
import { PayPalReturnBanner } from "./components/PayPalReturnBanner"
import {
  type TransactionRecord,
  type RecoveryCaseRecord,
  type SystemStatus,
  DEMO_CASES,
} from "./dashboardTypes"

describe("Sidebar Navigation", () => {
  it("renders all 5 required navigation items", () => {
    const html = renderToString(
      React.createElement(Sidebar, {
        currentNav: "overview",
        onNavigate: () => {},
        isOpen: false,
        onClose: () => {},
      })
    )

    expect(html).toContain("Overview")
    expect(html).toContain("Payment Recovery Copilot")
    expect(html).toContain("Payment Transactions")
    expect(html).toContain("Recovery Cases")
    expect(html).toContain("Settings")
  })

  it("applies active class to the current navigation item", () => {
    const htmlCopilot = renderToString(
      React.createElement(Sidebar, {
        currentNav: "copilot",
        onNavigate: () => {},
        isOpen: false,
        onClose: () => {},
      })
    )
    expect(htmlCopilot).toContain("active")
    expect(htmlCopilot).toContain("Payment Recovery Copilot")
  })
})

describe("Header Component", () => {
  it("displays the correct title for each page", () => {
    const html = renderToString(
      React.createElement(Header, {
        currentNav: "overview",
        onToggleMobileNav: () => {},
        backendHealthy: true,
        isCheckingBackend: false,
        onCheckBackend: () => {},
        demoMode: false,
        onToggleDemoMode: () => {},
      })
    )
    expect(html).toContain("Overview Dashboard")
    expect(html).toContain("API Online")
    expect(html).toContain("Demo Mode: OFF")
  })

  it("reflects demo mode ON state", () => {
    const html = renderToString(
      React.createElement(Header, {
        currentNav: "settings",
        onToggleMobileNav: () => {},
        backendHealthy: false,
        isCheckingBackend: false,
        onCheckBackend: () => {},
        demoMode: true,
        onToggleDemoMode: () => {},
      })
    )
    expect(html).toContain("Settings &amp; System Status")
    expect(html).toContain("Demo Mode: ON")
    expect(html).toContain("API Offline")
  })
})

describe("Overview Page", () => {
  it("renders all 5 KPI cards with honest empty states when no transactions exist", () => {
    const html = renderToString(
      React.createElement(OverviewPage, {
        sessionTransactions: [],
        recoveryCases: [],
        activityLog: [],
        showDemoData: false,
        onToggleDemoData: () => {},
        onNavigate: () => {},
        onCreateOrder: () => {},
        isCreatingOrder: false,
        onAnalyzeTransaction: () => {},
      })
    )

    // Check 5 KPI cards
    expect(html).toContain("Total Transactions")
    expect(html).toContain("Successful Payments")
    expect(html).toContain("Failed / Declined")
    expect(html).toContain("Pending Approval")
    expect(html).toContain("Recovery Cases")

    // Empty state explanation
    expect(html).toContain("No transactions recorded yet")
    expect(html).toContain("Database Connected:")
    expect(html).toContain("clearpayai.db")
  })

  it("renders database-backed stats accurately when dashboardStats is provided", () => {
    const html = renderToString(
      React.createElement(OverviewPage, {
        sessionTransactions: [],
        recoveryCases: [],
        activityLog: [],
        dashboardStats: {
          totalTransactions: 12,
          successfulPayments: 8,
          failedPayments: 3,
          pendingPayments: 1,
          recoveryCases: 5,
        },
        showDemoData: false,
        onToggleDemoData: () => {},
        onNavigate: () => {},
        onCreateOrder: () => {},
        isCreatingOrder: false,
        onAnalyzeTransaction: () => {},
      })
    )

    expect(html).toContain("12")
    expect(html).toContain("8")
    expect(html).toContain("3")
    expect(html).toContain("1")
    expect(html).toContain("5")
    expect(html).toContain("Database records")
  })

  it("renders sample metrics when demo preview is enabled with clear DEMO DATA badge", () => {
    const html = renderToString(
      React.createElement(OverviewPage, {
        sessionTransactions: [],
        recoveryCases: [],
        activityLog: [],
        showDemoData: true,
        onToggleDemoData: () => {},
        onNavigate: () => {},
        onCreateOrder: () => {},
        isCreatingOrder: false,
        onAnalyzeTransaction: () => {},
      })
    )

    expect(html).toContain("DEMO DATA MODE")
    expect(html).toContain("DEMO DATA")
    expect(html).toContain("5O198114181717017")
  })
})

describe("Transactions Page", () => {
  it("renders empty state and database connection notice when no transactions exist", () => {
    const html = renderToString(
      React.createElement(TransactionsPage, {
        sessionTransactions: [],
        onCreateOrder: () => {},
        isCreatingOrder: false,
        onAnalyzeTransaction: () => {},
        showDemoData: false,
        onToggleDemoData: () => {},
      })
    )

    expect(html).toContain("Database Connected:")
    expect(html).toContain("clearpayai.db")
    expect(html).toContain("No transactions in current session")
  })

  it("renders database syncing state and retry button when error occurs", () => {
    const html = renderToString(
      React.createElement(TransactionsPage, {
        sessionTransactions: [],
        onCreateOrder: () => {},
        isCreatingOrder: false,
        onAnalyzeTransaction: () => {},
        showDemoData: false,
        onToggleDemoData: () => {},
        isLoading: true,
        error: "Failed to connect to backend",
        onRefresh: () => {},
      })
    )

    expect(html).toContain("Database Error:")
    expect(html).toContain("Failed to connect to backend")
    expect(html).toContain("Retry")
    expect(html).toContain("Syncing...")
  })

  it("renders transaction table with correct columns and status badges when records exist", () => {
    const sampleTx: TransactionRecord[] = [
      {
        id: "tx-1",
        orderId: "ORDER-TEST-123",
        amount: "10.00",
        currency: "USD",
        status: "completed",
        captureId: "CAP-456",
        createdAt: "12:00:00",
      },
      {
        id: "tx-2",
        orderId: "ORDER-TEST-789",
        amount: "25.00",
        currency: "USD",
        status: "failed",
        failureReason: "INSTRUMENT_DECLINED",
        createdAt: "12:05:00",
      },
    ]

    const html = renderToString(
      React.createElement(TransactionsPage, {
        sessionTransactions: sampleTx,
        onCreateOrder: () => {},
        isCreatingOrder: false,
        onAnalyzeTransaction: () => {},
        showDemoData: false,
        onToggleDemoData: () => {},
      })
    )

    expect(html).toContain("ORDER-TEST-123")
    expect(html).toContain("CAP-456")
    expect(html).toContain("ORDER-TEST-789")
    expect(html).toContain("INSTRUMENT_DECLINED")
    expect(html).toContain("Diagnose in Copilot")
  })
})

describe("Recovery Cases Page", () => {
  it("renders database connection notice and empty state when no cases exist", () => {
    const html = renderToString(
      React.createElement(RecoveryCasesPage, {
        recoveryCases: [],
        onOpenCaseInCopilot: () => {},
        onNavigateToCopilot: () => {},
        showDemoData: false,
        onToggleDemoData: () => {},
      })
    )

    expect(html).toContain("Database Connected:")
    expect(html).toContain("clearpayai.db")
    expect(html).toContain("No recovery cases recorded in this session")
  })

  it("renders case cards with diagnosis summary and recommended actions", () => {
    const sampleCase: RecoveryCaseRecord = {
      id: "case-999",
      orderId: "ORDER-ABC",
      status: "Action Required",
      title: "Funding Instrument Declined",
      summary: "Payment failed due to buyer card decline.",
      actionsCount: 2,
      createdAt: "12:10:00",
      analysis: DEMO_CASES[0].analysis,
    }

    const html = renderToString(
      React.createElement(RecoveryCasesPage, {
        recoveryCases: [sampleCase],
        onOpenCaseInCopilot: () => {},
        onNavigateToCopilot: () => {},
        showDemoData: false,
        onToggleDemoData: () => {},
      })
    )

    expect(html).toContain("case-999")
    expect(html).toContain("ORDER-ABC")
    expect(html).toContain("Action Required")
    expect(html).toContain("Payment failed due to buyer card decline.")
    expect(html).toContain("Recommended Next Action:")
    expect(html).toContain("View in Copilot")
  })
})

describe("Settings Page", () => {
  it("displays system status without exposing credentials", () => {
    const status: SystemStatus = {
      status: "healthy",
      environment: "sandbox",
      paypal_configured: true,
      gemini_configured: true,
      demo_mode: false,
      model: "gemini-3.5-flash",
    }

    const html = renderToString(
      React.createElement(SettingsPage, {
        backendHealthy: true,
        isCheckingBackend: false,
        onCheckBackend: () => {},
        systemStatus: status,
        demoMode: false,
        onToggleDemoMode: () => {},
      })
    )

    expect(html).toContain("Security &amp; Credentials Policy")
    expect(html).toContain("Online &amp; Healthy")
    expect(html).toContain("Google Gemini API")
    expect(html).toContain("gemini-3.5-flash")
    expect(html).toContain("PayPal Sandbox")
    expect(html).toContain("SANDBOX / DEVELOPMENT")
    // Ensure no secrets leaked
    expect(html).not.toContain("api_key")
    expect(html).not.toContain("client_secret")
  })
})

describe("Copilot Page Preservation", () => {
  it("renders the full Copilot form with all fields and advisory notice", () => {
    const html = renderToString(
      React.createElement(CopilotPage, {
        aiProvider: "PayPal",
        setAiProvider: () => {},
        aiStatus: "FAILED",
        setAiStatus: () => {},
        aiErrorCode: "INSTRUMENT_DECLINED",
        setAiErrorCode: () => {},
        aiErrorMessage: "Declined",
        setAiErrorMessage: () => {},
        aiAmount: "10.00",
        setAiAmount: () => {},
        aiCurrency: "USD",
        setAiCurrency: () => {},
        aiPreviousAttempts: 1,
        setAiPreviousAttempts: () => {},
        aiIncidentDescription: "Test incident description",
        setAiIncidentDescription: () => {},
        aiAdditionalDiagnostics: "",
        setAiAdditionalDiagnostics: () => {},
        aiLoading: false,
        aiError: null,
        aiResult: null,
        aiFollowUpQuestion: "",
        setAiFollowUpQuestion: () => {},
        aiFollowUpLoading: false,
        aiFollowUpError: null,
        aiHistory: [],
        onAnalyzePayment: () => {},
        onAskFollowUp: () => {},
        onResetAnalysis: () => {},
      })
    )

    expect(html).toContain("Payment Incident Details")
    expect(html).toContain("INSTRUMENT_DECLINED")
    expect(html).toContain("Test incident description")
    expect(html).toContain("Analyze Payment Failure")
    expect(html).toContain("AI-generated recommendations based on the submitted information")
  })

  it("renders structured AI diagnosis when aiResult is present", () => {
    const html = renderToString(
      React.createElement(CopilotPage, {
        aiProvider: "PayPal",
        setAiProvider: () => {},
        aiStatus: "FAILED",
        setAiStatus: () => {},
        aiErrorCode: "",
        setAiErrorCode: () => {},
        aiErrorMessage: "",
        setAiErrorMessage: () => {},
        aiAmount: "",
        setAiAmount: () => {},
        aiCurrency: "USD",
        setAiCurrency: () => {},
        setAiPreviousAttempts: () => {},
        aiPreviousAttempts: 0,
        aiIncidentDescription: "",
        setAiIncidentDescription: () => {},
        aiAdditionalDiagnostics: "",
        setAiAdditionalDiagnostics: () => {},
        aiLoading: false,
        aiError: null,
        aiResult: DEMO_CASES[0].analysis,
        aiFollowUpQuestion: "",
        setAiFollowUpQuestion: () => {},
        aiFollowUpLoading: false,
        aiFollowUpError: null,
        aiHistory: [
          { question: "Can I retry now?", answer: "No, do not retry with the same funding instrument." },
        ],
        onAnalyzePayment: () => {},
        onAskFollowUp: () => {},
        onResetAnalysis: () => {},
      })
    )

    expect(html).toContain("PayPal Payment Failure: INSTRUMENT_DECLINED")
    expect(html).toContain("Confirmed Facts")
    expect(html).toContain("Possible Causes")
    expect(html).toContain("Prioritized Recovery Actions")
    expect(html).toContain("Conditional Document Checklist")
    expect(html).toContain("Customer-Facing Message")
    expect(html).toContain("Ask Follow-up Question")
    expect(html).toContain("Can I retry now?")
    expect(html).toContain("No, do not retry with the same funding instrument.")
  })
})

describe("PayPal Return Banner", () => {
  it("renders verified COMPLETED capture details", () => {
    const html = renderToString(
      React.createElement(PayPalReturnBanner, {
        paymentState: "completed",
        orderId: "ORDER-12345",
        captureId: "CAPTURE-67890",
        orderAmount: "10.00",
        orderCurrency: "USD",
        errorMessage: null,
        onDismiss: () => {},
      })
    )

    expect(html).toContain("PayPal Payment Captured Successfully")
    expect(html).toContain("ORDER-12345")
    expect(html).toContain("CAPTURE-67890")
    expect(html).toContain("10.00")
    expect(html).toContain("USD")
  })

  it("returns null when paymentState is idle", () => {
    const html = renderToString(
      React.createElement(PayPalReturnBanner, {
        paymentState: "idle",
        orderId: null,
        captureId: null,
        orderAmount: null,
        orderCurrency: null,
        errorMessage: null,
        onDismiss: () => {},
      })
    )

    expect(html).toBe("")
  })
})

describe("StatusBadge Component", () => {
  it("renders correct badge class for different statuses", () => {
    expect(renderToString(React.createElement(StatusBadge, { status: "completed" }))).toContain("badge-completed")
    expect(renderToString(React.createElement(StatusBadge, { status: "failed" }))).toContain("badge-failed")
    expect(renderToString(React.createElement(StatusBadge, { status: "declined" }))).toContain("badge-declined")
    expect(renderToString(React.createElement(StatusBadge, { status: "awaiting_approval" }))).toContain("badge-pending")
    expect(renderToString(React.createElement(StatusBadge, { status: "simulated_completed" }))).toContain("badge-simulated")
  })
})
