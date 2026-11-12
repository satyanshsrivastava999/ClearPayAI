import { useEffect, useRef, useState } from "react"
import "./App.css"
import { parsePayPalReturn } from "./paypalReturn"
import {
  validateFollowUpQuestion,
  validateIncidentForm,
  type AIAnalysisResponse,
} from "./aiCopilot"
import {
  type NavItem,
  type PaymentState,
  type TransactionRecord,
  type RecoveryCaseRecord,
  type ActivityItem,
  type SystemStatus,
} from "./dashboardTypes"
import { Sidebar } from "./components/Sidebar"
import { Header } from "./components/Header"
import { PayPalReturnBanner } from "./components/PayPalReturnBanner"
import { OverviewPage } from "./components/OverviewPage"
import { TransactionsPage } from "./components/TransactionsPage"
import { RecoveryCasesPage } from "./components/RecoveryCasesPage"
import { SettingsPage } from "./components/SettingsPage"
import { CopilotPage } from "./components/CopilotPage"

// PayPal return parameters parsed once at module load
const INITIAL_RETURN = parsePayPalReturn(window.location.search)

type HealthResponse = {
  status: string
}

type OrderRequest = {
  amount: string
  currency: string
}

type OrderResponse = {
  order_id: string
  approval_url: string
  amount: string
  currency: string
}

type CaptureResponse = {
  order_id: string
  status: string
  capture_id?: string
  amount?: string
  currency?: string
}

function App() {
  // Navigation & UI state
  const [currentNav, setCurrentNav] = useState<NavItem>(() => {
    // If returning from PayPal, show transactions/overview
    if (INITIAL_RETURN.token || INITIAL_RETURN.cancelled) return "overview"
    return "overview"
  })
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)
  const [showDemoData, setShowDemoData] = useState(false)

  // Session records (in-memory for active session)
  const [sessionTransactions, setSessionTransactions] = useState<TransactionRecord[]>([])
  const [recoveryCases, setRecoveryCases] = useState<RecoveryCaseRecord[]>([])
  const [activityLog, setActivityLog] = useState<ActivityItem[]>([
    {
      id: "act-init",
      timestamp: new Date().toLocaleTimeString(),
      type: "system",
      description: "ClearPay AI session started",
      badge: "INFO",
    },
  ])

  // Backend connection & system status
  const [isChecking, setIsChecking] = useState(false)
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)

  // Order / payment state
  const [paymentState, setPaymentState] = useState<PaymentState>(() => {
    if (INITIAL_RETURN.cancelled) return "cancelled"
    if (INITIAL_RETURN.token) return "processing"
    return "idle"
  })
  const [orderId, setOrderId] = useState<string | null>(INITIAL_RETURN.token)
  const [approvalUrl, setApprovalUrl] = useState<string | null>(null)
  const [orderAmount, setOrderAmount] = useState<string | null>(null)
  const [orderCurrency, setOrderCurrency] = useState<string | null>(null)
  const [captureId, setCaptureId] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(() => {
    return localStorage.getItem("clearpay_demo_mode") === "1"
  })

  // Copilot AI state (preserved in memory across nav switches)
  const [aiProvider, setAiProvider] = useState("PayPal")
  const [aiStatus, setAiStatus] = useState("FAILED")
  const [aiErrorCode, setAiErrorCode] = useState("")
  const [aiErrorMessage, setAiErrorMessage] = useState("")
  const [aiAmount, setAiAmount] = useState("")
  const [aiCurrency, setAiCurrency] = useState("USD")
  const [aiPreviousAttempts, setAiPreviousAttempts] = useState(0)
  const [aiIncidentDescription, setAiIncidentDescription] = useState("")
  const [aiAdditionalDiagnostics, setAiAdditionalDiagnostics] = useState("")
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [aiResult, setAiResult] = useState<AIAnalysisResponse | null>(null)
  const [aiFollowUpQuestion, setAiFollowUpQuestion] = useState("")
  const [aiFollowUpError, setAiFollowUpError] = useState<string | null>(null)
  const [aiFollowUpLoading, setAiFollowUpLoading] = useState(false)
  const [aiHistory, setAiHistory] = useState<{ question: string; answer: string }[]>([])

  // Capture order function
  const captureOrder = async (id: string) => {
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/orders/${id}/capture`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      )

      if (!response.ok) {
        let detail = `HTTP ${response.status}`
        try {
          const errorData = await response.json()
          if (errorData?.detail) {
            detail = errorData.detail
          }
        } catch {
          // ignore parse errors
        }
        throw new Error(detail)
      }

      const data: CaptureResponse = await response.json()

      if (data.status === "COMPLETED") {
        setCaptureId(data.capture_id ?? null)
        if (data.amount) setOrderAmount(data.amount)
        if (data.currency) setOrderCurrency(data.currency)
        setPaymentState("completed")

        // Update session transactions
        setSessionTransactions((prev) => {
          const exists = prev.find((t) => t.orderId === id)
          if (exists) {
            return prev.map((t) =>
              t.orderId === id
                ? { ...t, status: "completed", captureId: data.capture_id }
                : t
            )
          }
          return [
            {
              id: `tx-${Date.now()}`,
              orderId: id,
              amount: data.amount || "10.00",
              currency: data.currency || "USD",
              status: "completed",
              captureId: data.capture_id,
              createdAt: new Date().toLocaleTimeString(),
            },
            ...prev,
          ]
        })

        setActivityLog((prev) => [
          {
            id: `act-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            type: "payment",
            description: `Payment captured successfully: ${data.capture_id}`,
            badge: "COMPLETED",
          },
          ...prev,
        ])
      } else if (data.status === "SIMULATED_COMPLETED") {
        setCaptureId(data.capture_id ?? null)
        if (data.amount) setOrderAmount(data.amount)
        if (data.currency) setOrderCurrency(data.currency)
        setPaymentState("simulated_completed")

        setSessionTransactions((prev) => [
          {
            id: `tx-${Date.now()}`,
            orderId: id,
            amount: data.amount || "10.00",
            currency: data.currency || "USD",
            status: "simulated_completed",
            captureId: data.capture_id,
            createdAt: new Date().toLocaleTimeString(),
            isDemo: true,
          },
          ...prev,
        ])

        setActivityLog((prev) => [
          {
            id: `act-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            type: "payment",
            description: `Simulated payment captured (Demo Mode): ${data.capture_id}`,
            badge: "DEMO",
          },
          ...prev,
        ])
      } else {
        throw new Error(`Payment not completed. Status: ${data.status}`)
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to capture payment"
      setErrorMessage(message)
      const nextState: PaymentState = /declin/i.test(message) ? "declined" : "failed"
      setPaymentState(nextState)

      setSessionTransactions((prev) => [
        {
          id: `tx-${Date.now()}`,
          orderId: id,
          amount: "10.00",
          currency: "USD",
          status: nextState,
          failureReason: message,
          createdAt: new Date().toLocaleTimeString(),
        },
        ...prev,
      ])

      setActivityLog((prev) => [
        {
          id: `act-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type: "payment",
          description: `Capture rejected: ${message}`,
          badge: nextState.toUpperCase(),
        },
        ...prev,
      ])
    }
  }

  const checkBackendConnection = async () => {
    setIsChecking(true)
    try {
      const response = await fetch("http://127.0.0.1:8000/health", {
        method: "GET",
        headers: { "Content-Type": "application/json" },
        cache: "no-store",
      })

      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data: HealthResponse = await response.json()
      if (data.status === "healthy") {
        setBackendHealthy(true)
      } else {
        setBackendHealthy(false)
      }

      // Also fetch system status safely
      try {
        const sysRes = await fetch("http://127.0.0.1:8000/api/settings/status")
        if (sysRes.ok) {
          const sysData: SystemStatus = await sysRes.json()
          setSystemStatus(sysData)
        }
      } catch {
        // ignore optional system status failure
      }
    } catch {
      setBackendHealthy(false)
    } finally {
      setIsChecking(false)
    }
  }

  // Handle return from PayPal
  const hasHandledReturn = useRef(false)
  useEffect(() => {
    if (hasHandledReturn.current) return

    const { token, cancelled } = INITIAL_RETURN
    if (!token && !cancelled) return

    hasHandledReturn.current = true
    window.history.replaceState({}, "", window.location.pathname)

    if (token && !cancelled) {
      setTimeout(() => {
        void captureOrder(token)
      }, 0)
    } else if (cancelled) {
      setTimeout(() => {
        setActivityLog((prev) => [
          {
            id: `act-${Date.now()}`,
            timestamp: new Date().toLocaleTimeString(),
            type: "payment",
            description: "Payment cancelled by buyer on PayPal checkout page",
            badge: "CANCELLED",
          },
          ...prev,
        ])
      }, 0)
    }
  }, [])

  // Initial health check on mount
  useEffect(() => {
    const timer = setTimeout(() => {
      void checkBackendConnection()
    }, 0)
    return () => clearTimeout(timer)
  }, [])

  const toggleDemoMode = () => {
    const next = !demoMode
    setDemoMode(next)
    localStorage.setItem("clearpay_demo_mode", next ? "1" : "0")
  }

  // Create PayPal order
  const createOrder = async () => {
    setPaymentState("creating")
    setErrorMessage(null)
    setOrderId(null)
    setApprovalUrl(null)
    setOrderAmount(null)
    setOrderCurrency(null)
    setCaptureId(null)

    if (demoMode) {
      const demoId = `DEMO-ORDER-${Math.floor(Math.random() * 900 + 100)}`
      setPaymentState("simulated_completed")
      setOrderId(demoId)
      setApprovalUrl("http://localhost:5173?demo=true")
      setOrderAmount("10.00")
      setOrderCurrency("USD")
      setCaptureId("DEMO-CAPTURE-456")

      setSessionTransactions((prev) => [
        {
          id: `tx-${Date.now()}`,
          orderId: demoId,
          amount: "10.00",
          currency: "USD",
          status: "simulated_completed",
          captureId: "DEMO-CAPTURE-456",
          createdAt: new Date().toLocaleTimeString(),
          isDemo: true,
        },
        ...prev,
      ])

      setActivityLog((prev) => [
        {
          id: `act-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type: "payment",
          description: `Simulated order and capture: ${demoId}`,
          badge: "DEMO",
        },
        ...prev,
      ])
      return
    }

    const orderRequest: OrderRequest = {
      amount: "10.00",
      currency: "USD",
    }

    try {
      const response = await fetch("http://127.0.0.1:8000/api/orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(orderRequest),
      })

      if (!response.ok) {
        let detail = `HTTP ${response.status}`
        try {
          const errorData = await response.json()
          if (errorData?.detail) detail = errorData.detail
        } catch {
          // ignore parse errors
        }
        throw new Error(detail)
      }

      const data: OrderResponse = await response.json()
      setOrderId(data.order_id)
      setApprovalUrl(data.approval_url)
      setOrderAmount(data.amount)
      setOrderCurrency(data.currency)
      setPaymentState("awaiting_approval")

      // Add to session transactions
      setSessionTransactions((prev) => [
        {
          id: `tx-${Date.now()}`,
          orderId: data.order_id,
          amount: data.amount,
          currency: data.currency,
          status: "awaiting_approval",
          createdAt: new Date().toLocaleTimeString(),
        },
        ...prev,
      ])

      setActivityLog((prev) => [
        {
          id: `act-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type: "payment",
          description: `Created PayPal order: ${data.order_id} ($${data.amount} USD)`,
          badge: "AWAITING",
        },
        ...prev,
      ])
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to create PayPal order"
      setErrorMessage(message)
      setPaymentState("failed")
    }
  }

  // AI Copilot Analysis
  const analyzePayment = async () => {
    const validation = validateIncidentForm({
      provider: aiProvider,
      status: aiStatus,
      errorCode: aiErrorCode,
      errorMessage: aiErrorMessage,
      amount: aiAmount,
      currency: aiCurrency,
      previousAttempts: aiPreviousAttempts,
      incidentDescription: aiIncidentDescription,
      additionalDiagnostics: aiAdditionalDiagnostics,
    })

    if (!validation.valid) {
      setAiError(validation.error ?? "Invalid input parameters.")
      return
    }

    setAiLoading(true)
    setAiError(null)
    setAiResult(null)
    setAiFollowUpError(null)
    setAiHistory([])

    try {
      const response = await fetch("http://127.0.0.1:8000/api/ai/analyze-payment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: "PayPal",
          status: aiStatus,
          error_code: aiErrorCode || null,
          error_message: aiErrorMessage || null,
          amount: aiAmount || null,
          currency: aiCurrency || null,
          previous_attempts: aiPreviousAttempts,
          incident_description: aiIncidentDescription,
          additional_diagnostics: aiAdditionalDiagnostics || null,
        }),
      })

      if (!response.ok) {
        let detail = `HTTP ${response.status}`
        try {
          const errorData = await response.json()
          if (errorData?.detail) detail = errorData.detail
        } catch {
          // ignore parse errors
        }
        throw new Error(detail)
      }

      const data: AIAnalysisResponse = await response.json()
      setAiResult(data)

      // Register or update recovery case in session
      const newCase: RecoveryCaseRecord = {
        id: `case-${Date.now().toString().slice(-4)}`,
        orderId: aiErrorCode ? `INC-${aiErrorCode}` : undefined,
        status: "Action Required",
        title: data.issue_title || `${aiStatus} Payment Diagnosis`,
        summary: data.summary,
        actionsCount: data.recommended_actions?.length || 0,
        createdAt: new Date().toLocaleTimeString(),
        analysis: data,
      }

      setRecoveryCases((prev) => [newCase, ...prev])

      setActivityLog((prev) => [
        {
          id: `act-${Date.now()}`,
          timestamp: new Date().toLocaleTimeString(),
          type: "copilot",
          description: `AI Diagnosis complete: ${data.issue_title}`,
          badge: "DIAGNOSED",
        },
        ...prev,
      ])
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to analyze payment"
      setAiError(message)
    } finally {
      setAiLoading(false)
    }
  }

  const askFollowUp = async () => {
    const validation = validateFollowUpQuestion(aiFollowUpQuestion)
    if (!validation.valid) {
      setAiFollowUpError(validation.error ?? "Invalid question.")
      return
    }
    if (!aiResult || aiFollowUpLoading) return

    setAiFollowUpLoading(true)
    setAiFollowUpError(null)
    const currentQ = aiFollowUpQuestion.trim()

    try {
      const response = await fetch("http://127.0.0.1:8000/api/ai/follow-up", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis: aiResult,
          history: aiHistory.slice(-5),
          question: currentQ,
        }),
      })

      if (!response.ok) {
        let detail = `HTTP ${response.status}`
        try {
          const errorData = await response.json()
          if (errorData?.detail) detail = errorData.detail
        } catch {
          // ignore parse errors
        }
        throw new Error(detail)
      }

      const data = await response.json()
      setAiHistory((prev) => [
        ...prev,
        { question: currentQ, answer: data.answer },
      ])
      setAiFollowUpQuestion("")
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Failed to get follow-up answer"
      setAiFollowUpError(message)
    } finally {
      setAiFollowUpLoading(false)
    }
  }

  // Prefill Copilot from a transaction record
  const handleAnalyzeTransaction = (tx: TransactionRecord) => {
    setAiProvider("PayPal")
    setAiStatus(tx.status === "declined" ? "DECLINED" : "FAILED")
    setAiErrorCode(tx.failureReason || "INSTRUMENT_DECLINED")
    setAiErrorMessage(tx.failureReason ? `Transaction returned ${tx.failureReason}` : "")
    setAiAmount(tx.amount)
    setAiCurrency(tx.currency)
    setAiPreviousAttempts(1)
    setAiIncidentDescription(`Payment failure observed for order ${tx.orderId} in status ${tx.status}.`)
    setCurrentNav("copilot")
  }

  // Open existing case in Copilot
  const handleOpenCaseInCopilot = (c: RecoveryCaseRecord) => {
    if (c.analysis) {
      setAiResult(c.analysis)
    }
    setCurrentNav("copilot")
  }

  const resetAnalysisForm = () => {
    setAiResult(null)
    setAiError(null)
    setAiFollowUpError(null)
    setAiHistory([])
  }

  return (
    <div className="dashboard-layout">
      {/* Sidebar Navigation */}
      <Sidebar
        currentNav={currentNav}
        onNavigate={setCurrentNav}
        isOpen={isMobileNavOpen}
        onClose={() => setIsMobileNavOpen(false)}
        activeCasesCount={recoveryCases.length}
        sessionTxCount={sessionTransactions.length}
      />

      {/* Main Dashboard Panel */}
      <div className="dashboard-main">
        {/* Top Header */}
        <Header
          currentNav={currentNav}
          onToggleMobileNav={() => setIsMobileNavOpen(!isMobileNavOpen)}
          backendHealthy={backendHealthy}
          isCheckingBackend={isChecking}
          onCheckBackend={checkBackendConnection}
          demoMode={demoMode}
          onToggleDemoMode={toggleDemoMode}
        />

        {/* Page Content */}
        <main className="dashboard-content">
          {/* Top Return Banner: Displays verified PayPal capture outcomes */}
          <PayPalReturnBanner
            paymentState={paymentState}
            orderId={orderId}
            captureId={captureId}
            orderAmount={orderAmount}
            orderCurrency={orderCurrency}
            errorMessage={errorMessage}
            onDismiss={() => setPaymentState("idle")}
          />

          {/* Active Approval Notice with Link */}
          {paymentState === "awaiting_approval" && approvalUrl && (
            <div
              style={{
                marginBottom: "20px",
                padding: "16px 20px",
                background: "#fffbeb",
                border: "1px solid #fde68a",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: "12px",
              }}
            >
              <div>
                <strong>PayPal Sandbox Order Created:</strong> {orderId} (10.00 USD)
                <div style={{ fontSize: "13px", color: "#92400e", marginTop: "2px" }}>
                  Please log in with a USD Sandbox buyer account to approve this payment.
                </div>
              </div>
              <a
                href={approvalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary"
                style={{ textDecoration: "none", background: "#0070ba" }}
              >
                Approve Payment on PayPal ↗
              </a>
            </div>
          )}

          {/* Page Routing */}
          {currentNav === "overview" && (
            <OverviewPage
              sessionTransactions={sessionTransactions}
              recoveryCases={recoveryCases}
              activityLog={activityLog}
              showDemoData={showDemoData}
              onToggleDemoData={setShowDemoData}
              onNavigate={setCurrentNav}
              onCreateOrder={createOrder}
              isCreatingOrder={paymentState === "creating"}
              onAnalyzeTransaction={handleAnalyzeTransaction}
            />
          )}

          {currentNav === "copilot" && (
            <CopilotPage
              aiProvider={aiProvider}
              setAiProvider={setAiProvider}
              aiStatus={aiStatus}
              setAiStatus={setAiStatus}
              aiErrorCode={aiErrorCode}
              setAiErrorCode={setAiErrorCode}
              aiErrorMessage={aiErrorMessage}
              setAiErrorMessage={setAiErrorMessage}
              aiAmount={aiAmount}
              setAiAmount={setAiAmount}
              aiCurrency={aiCurrency}
              setAiCurrency={setAiCurrency}
              aiPreviousAttempts={aiPreviousAttempts}
              setAiPreviousAttempts={setAiPreviousAttempts}
              aiIncidentDescription={aiIncidentDescription}
              setAiIncidentDescription={setAiIncidentDescription}
              aiAdditionalDiagnostics={aiAdditionalDiagnostics}
              setAiAdditionalDiagnostics={setAiAdditionalDiagnostics}
              aiLoading={aiLoading}
              aiError={aiError}
              aiResult={aiResult}
              aiFollowUpQuestion={aiFollowUpQuestion}
              setAiFollowUpQuestion={setAiFollowUpQuestion}
              aiFollowUpLoading={aiFollowUpLoading}
              aiFollowUpError={aiFollowUpError}
              aiHistory={aiHistory}
              onAnalyzePayment={analyzePayment}
              onAskFollowUp={askFollowUp}
              onResetAnalysis={resetAnalysisForm}
            />
          )}

          {currentNav === "transactions" && (
            <TransactionsPage
              sessionTransactions={sessionTransactions}
              onCreateOrder={createOrder}
              isCreatingOrder={paymentState === "creating"}
              onAnalyzeTransaction={handleAnalyzeTransaction}
              showDemoData={showDemoData}
              onToggleDemoData={setShowDemoData}
            />
          )}

          {currentNav === "cases" && (
            <RecoveryCasesPage
              recoveryCases={recoveryCases}
              onOpenCaseInCopilot={handleOpenCaseInCopilot}
              onNavigateToCopilot={() => setCurrentNav("copilot")}
              showDemoData={showDemoData}
              onToggleDemoData={setShowDemoData}
            />
          )}

          {currentNav === "settings" && (
            <SettingsPage
              backendHealthy={backendHealthy}
              isCheckingBackend={isChecking}
              onCheckBackend={checkBackendConnection}
              systemStatus={systemStatus}
              demoMode={demoMode}
              onToggleDemoMode={toggleDemoMode}
            />
          )}
        </main>
      </div>
    </div>
  )
}

export default App
