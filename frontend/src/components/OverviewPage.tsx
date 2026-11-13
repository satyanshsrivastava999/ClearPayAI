import React from "react"
import {
  type NavItem,
  type TransactionRecord,
  type RecoveryCaseRecord,
  type ActivityItem,
  type DashboardStats,
  DEMO_TRANSACTIONS,
  DEMO_CASES,
} from "../dashboardTypes"

interface OverviewPageProps {
  sessionTransactions: TransactionRecord[]
  recoveryCases: RecoveryCaseRecord[]
  activityLog: ActivityItem[]
  dashboardStats?: DashboardStats | null
  isLoading?: boolean
  error?: string | null
  onRefresh?: () => void
  showDemoData: boolean
  onToggleDemoData: (enabled: boolean) => void
  onNavigate: (item: NavItem) => void
  onCreateOrder: () => void
  isCreatingOrder: boolean
  onAnalyzeTransaction: (tx: TransactionRecord) => void
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  sessionTransactions,
  recoveryCases,
  activityLog,
  dashboardStats,
  isLoading,
  error,
  onRefresh,
  showDemoData,
  onToggleDemoData,
  onNavigate,
  onCreateOrder,
  isCreatingOrder,
  onAnalyzeTransaction,
}) => {
  const isDemoActive = showDemoData && sessionTransactions.length === 0
  const transactions = isDemoActive ? DEMO_TRANSACTIONS : sessionTransactions
  const cases = isDemoActive ? DEMO_CASES : recoveryCases

  // Compute stats: prefer database-backed stats when available
  const totalTransactions = isDemoActive
    ? transactions.length
    : (dashboardStats ? dashboardStats.totalTransactions : transactions.length)

  const successfulPayments = isDemoActive
    ? transactions.filter((t) => t.status === "completed" || t.status === "simulated_completed").length
    : (dashboardStats ? dashboardStats.successfulPayments : transactions.filter((t) => t.status === "completed" || t.status === "simulated_completed").length)

  const failedPayments = isDemoActive
    ? transactions.filter((t) => t.status === "failed" || t.status === "declined").length
    : (dashboardStats ? dashboardStats.failedPayments : transactions.filter((t) => t.status === "failed" || t.status === "declined").length)

  const pendingPayments = isDemoActive
    ? transactions.filter((t) => t.status === "awaiting_approval" || t.status === "processing").length
    : (dashboardStats ? dashboardStats.pendingPayments : transactions.filter((t) => t.status === "awaiting_approval" || t.status === "processing").length)

  const totalCases = isDemoActive
    ? cases.length
    : (dashboardStats ? dashboardStats.recoveryCases : cases.length)

  return (
    <div className="overview-page">
      {/* Notice Banner explaining database connection */}
      <div className="notice-banner notice-info">
        <span style={{ fontSize: "16px" }}>🗄️</span>
        <div style={{ flex: 1 }}>
          <strong>Database Connected:</strong> Metrics and payment records are synchronized with <code>clearpayai.db</code>.
          Transactions and AI recovery cases persist across reloads.
          {transactions.length === 0 && !showDemoData && (
            <span> Database is empty. Create a test order or preview demo data.</span>
          )}
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              disabled={isLoading}
              className="btn-secondary btn-sm"
              style={{ whiteSpace: "nowrap" }}
            >
              {isLoading ? "Syncing..." : "↻ Refresh DB"}
            </button>
          )}
          <button
            type="button"
            onClick={() => onToggleDemoData(!showDemoData)}
            className="btn-secondary btn-sm"
            style={{ whiteSpace: "nowrap" }}
          >
            {showDemoData ? "Hide Demo Data" : "Preview Demo Data"}
          </button>
        </div>
      </div>

      {error && (
        <div
          className="notice-banner notice-warning"
          style={{ marginBottom: "16px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b" }}
        >
          <span>⚠️</span>
          <div style={{ flex: 1 }}>
            <strong>Database Sync Notice:</strong> {error}
          </div>
          {onRefresh && (
            <button type="button" onClick={onRefresh} className="btn-secondary btn-sm">
              Retry
            </button>
          )}
        </div>
      )}

      {showDemoData && sessionTransactions.length === 0 && (
        <div
          style={{
            marginBottom: "16px",
            padding: "8px 12px",
            background: "#eff6ff",
            border: "1px dashed #3b82f6",
            borderRadius: "6px",
            fontSize: "12px",
            color: "#1d4ed8",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span className="status-badge badge-demo">[DEMO DATA MODE]</span>
          <span>Showing illustrative sample records for UI demonstration. Database records are empty.</span>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Total Transactions</span>
            <span style={{ fontSize: "18px" }}>💳</span>
          </div>
          <div className="kpi-value">{totalTransactions}</div>
          <div className="kpi-sub">
            {isDemoActive ? "Sample dataset" : "Database records"}
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Successful Payments</span>
            <span style={{ fontSize: "18px" }}>✅</span>
          </div>
          <div className="kpi-value" style={{ color: "#059669" }}>
            {successfulPayments}
          </div>
          <div className="kpi-sub">Confirmed captures</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Failed / Declined</span>
            <span style={{ fontSize: "18px" }}>❌</span>
          </div>
          <div className="kpi-value" style={{ color: "#dc2626" }}>
            {failedPayments}
          </div>
          <div className="kpi-sub">Requires recovery diagnosis</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Pending Approval</span>
            <span style={{ fontSize: "18px" }}>⏳</span>
          </div>
          <div className="kpi-value" style={{ color: "#d97706" }}>
            {pendingPayments}
          </div>
          <div className="kpi-sub">In checkout flow</div>
        </div>

        <div className="kpi-card">
          <div className="kpi-header">
            <span className="kpi-label">Recovery Cases</span>
            <span style={{ fontSize: "18px" }}>🤖</span>
          </div>
          <div className="kpi-value" style={{ color: "#2563eb" }}>
            {totalCases}
          </div>
          <div className="kpi-sub">AI Copilot diagnoses</div>
        </div>
      </div>

      {/* Quick Action Bar */}
      <div
        className="dashboard-card"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          background: "linear-gradient(to right, var(--card-bg), var(--bg))",
        }}
      >
        <div>
          <h3 style={{ fontSize: "15px", marginBottom: "4px" }}>Test PayPal Sandbox Payment Flow</h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
            Create a standard $10.00 USD PayPal Sandbox order, review approval redirect, and test payment capture.
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="btn-primary"
            onClick={onCreateOrder}
            disabled={isCreatingOrder}
          >
            {isCreatingOrder ? "Creating Order..." : "+ Create Test Order ($10.00)"}
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => onNavigate("copilot")}
          >
            Open Copilot
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px", alignItems: "start" }}>
        {/* Left Column: Recent Transactions */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <h3 className="card-title">Recent Transactions</h3>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={() => onNavigate("transactions")}
            >
              View All ({transactions.length})
            </button>
          </div>

          {transactions.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <div className="empty-state-title">No transactions recorded yet</div>
              <div className="empty-state-desc">
                Create a PayPal Sandbox test order or toggle Demo Data to preview the transactions interface.
              </div>
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={onCreateOrder}
                disabled={isCreatingOrder}
              >
                Create First Test Order
              </button>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.slice(0, 5).map((tx) => (
                    <tr key={tx.id}>
                      <td>
                        <div style={{ fontFamily: "var(--mono)", fontSize: "13px", fontWeight: 600 }}>
                          {tx.orderId}
                        </div>
                        {tx.isDemo && (
                          <span className="status-badge badge-demo" style={{ fontSize: "10px", padding: "1px 6px" }}>
                            DEMO DATA
                          </span>
                        )}
                      </td>
                      <td>
                        <strong>{tx.amount}</strong> {tx.currency}
                      </td>
                      <td>
                        <StatusBadge status={tx.status} />
                      </td>
                      <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                        {tx.createdAt}
                      </td>
                      <td>
                        {(tx.status === "failed" || tx.status === "declined") ? (
                          <button
                            type="button"
                            className="btn-secondary btn-sm"
                            onClick={() => onAnalyzeTransaction(tx)}
                            title="Prefill Payment Recovery Copilot with this transaction"
                          >
                            Diagnose
                          </button>
                        ) : (
                          <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>Verified</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Right Column: Recovery Overview & Recent Activity */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Recovery Overview */}
          <div className="dashboard-card">
            <div className="card-header-row">
              <h3 className="card-title">Recovery Overview</h3>
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => onNavigate("cases")}
              >
                Cases ({cases.length})
              </button>
            </div>

            {cases.length === 0 ? (
              <div style={{ textAlign: "center", padding: "20px 10px", color: "var(--text-muted)" }}>
                <p style={{ fontSize: "13px", marginBottom: "8px" }}>No recovery cases active.</p>
                <button
                  type="button"
                  className="btn-secondary btn-sm"
                  onClick={() => onNavigate("copilot")}
                >
                  Analyze an Incident
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {cases.slice(0, 3).map((c) => (
                  <div
                    key={c.id}
                    style={{
                      padding: "10px 12px",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      background: "var(--bg)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 600, fontSize: "13px", color: "var(--text-h)" }}>
                        {c.title}
                      </span>
                      <span className="status-badge badge-pending" style={{ fontSize: "11px" }}>
                        {c.status}
                      </span>
                    </div>
                    <p style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "6px" }}>
                      {c.summary.length > 80 ? c.summary.slice(0, 80) + "..." : c.summary}
                    </p>
                    <button
                      type="button"
                      className="btn-secondary btn-sm"
                      style={{ width: "100%", fontSize: "11px" }}
                      onClick={() => onNavigate("cases")}
                    >
                      View Details & Next Steps
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Activity Feed */}
          <div className="dashboard-card">
            <h3 className="card-title" style={{ marginBottom: "14px" }}>Recent Activity</h3>
            {activityLog.length === 0 ? (
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                No activity recorded in this session.
              </p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {activityLog.slice(0, 5).map((act) => (
                  <div
                    key={act.id}
                    style={{
                      padding: "8px 10px",
                      borderLeft: "3px solid var(--primary)",
                      background: "var(--bg)",
                      borderRadius: "0 4px 4px 0",
                      fontSize: "12px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", marginBottom: "2px" }}>
                      <span>{act.timestamp}</span>
                      {act.badge && <span className="status-badge badge-neutral" style={{ fontSize: "10px" }}>{act.badge}</span>}
                    </div>
                    <div style={{ color: "var(--text-h)", fontWeight: 500 }}>
                      {act.description}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  switch (status.toLowerCase()) {
    case "completed":
      return <span className="status-badge badge-completed">● Completed</span>
    case "simulated_completed":
      return <span className="status-badge badge-simulated">🟡 Simulated</span>
    case "awaiting_approval":
      return <span className="status-badge badge-pending">🕒 Awaiting Approval</span>
    case "processing":
      return <span className="status-badge badge-pending">⏳ Processing</span>
    case "failed":
      return <span className="status-badge badge-failed">✕ Failed</span>
    case "declined":
      return <span className="status-badge badge-declined">✕ Declined</span>
    case "cancelled":
      return <span className="status-badge badge-neutral">Cancelled</span>
    default:
      return <span className="status-badge badge-neutral">{status}</span>
  }
}

