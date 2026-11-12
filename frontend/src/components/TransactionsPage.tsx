import React, { useState } from "react"
import { type TransactionRecord, DEMO_TRANSACTIONS } from "../dashboardTypes"
import { StatusBadge } from "./OverviewPage"

interface TransactionsPageProps {
  sessionTransactions: TransactionRecord[]
  onCreateOrder: () => void
  isCreatingOrder: boolean
  onAnalyzeTransaction: (tx: TransactionRecord) => void
  showDemoData: boolean
  onToggleDemoData: (enabled: boolean) => void
}

export const TransactionsPage: React.FC<TransactionsPageProps> = ({
  sessionTransactions,
  onCreateOrder,
  isCreatingOrder,
  onAnalyzeTransaction,
  showDemoData,
  onToggleDemoData,
}) => {
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")

  // Use session transactions or demo preview if enabled
  const allTransactions = showDemoData && sessionTransactions.length === 0
    ? DEMO_TRANSACTIONS
    : sessionTransactions

  // Filter by search & status
  const filtered = allTransactions.filter((tx) => {
    const matchesSearch =
      searchTerm === "" ||
      tx.orderId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (tx.captureId && tx.captureId.toLowerCase().includes(searchTerm.toLowerCase()))

    const matchesStatus =
      statusFilter === "all" ||
      tx.status.toLowerCase() === statusFilter.toLowerCase()

    return matchesSearch && matchesStatus
  })

  return (
    <div className="transactions-page">
      {/* Information Notice */}
      <div className="notice-banner notice-info">
        <span style={{ fontSize: "16px" }}>ℹ️</span>
        <div style={{ flex: 1 }}>
          <strong>Session Transactions Notice:</strong> Displaying verified payment records from the current active
          browser session. Persistent database storage has not been connected in Phase 3. Transactions reset upon page reload.
        </div>
        <button
          type="button"
          onClick={() => onToggleDemoData(!showDemoData)}
          className="btn-secondary btn-sm"
          style={{ whiteSpace: "nowrap" }}
        >
          {showDemoData ? "Hide Demo Data" : "Preview Demo Data"}
        </button>
      </div>

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
          <span>Showing sample transactions. No database is currently implemented.</span>
        </div>
      )}

      {/* Control Bar: Search, Filter, Action */}
      <div className="dashboard-card" style={{ padding: "16px 20px", marginBottom: "20px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", flex: 1 }}>
            <input
              type="text"
              placeholder="Search by Order ID or Capture ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid var(--border)",
                minWidth: "260px",
                fontSize: "14px",
                background: "var(--card-bg)",
                color: "var(--text-h)",
              }}
            />

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid var(--border)",
                fontSize: "14px",
                background: "var(--card-bg)",
                color: "var(--text-h)",
              }}
            >
              <option value="all">All Statuses ({allTransactions.length})</option>
              <option value="completed">Completed</option>
              <option value="awaiting_approval">Awaiting Approval</option>
              <option value="failed">Failed</option>
              <option value="declined">Declined</option>
              <option value="cancelled">Cancelled</option>
              <option value="simulated_completed">Simulated (Demo)</option>
            </select>

            {(searchTerm || statusFilter !== "all") && (
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={() => {
                  setSearchTerm("")
                  setStatusFilter("all")
                }}
              >
                Clear Filters
              </button>
            )}
          </div>

          <button
            type="button"
            className="btn-primary"
            onClick={onCreateOrder}
            disabled={isCreatingOrder}
          >
            {isCreatingOrder ? "Creating Order..." : "+ New Sandbox Order ($10.00)"}
          </button>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="dashboard-card" style={{ padding: 0 }}>
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-title">
              {allTransactions.length === 0
                ? "No transactions in current session"
                : "No transactions match your search or filter"}
            </div>
            <div className="empty-state-desc">
              {allTransactions.length === 0
                ? "Create a PayPal Sandbox test order or toggle Demo Data to preview transaction management."
                : "Try resetting your search query or selecting a different status filter."}
            </div>
            {allTransactions.length === 0 && (
              <button
                type="button"
                className="btn-primary btn-sm"
                onClick={onCreateOrder}
                disabled={isCreatingOrder}
              >
                Create Test Order ($10.00 USD)
              </button>
            )}
          </div>
        ) : (
          <div className="table-container" style={{ border: "none" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Capture ID / Reason</th>
                  <th>Created At</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((tx) => (
                  <tr key={tx.id}>
                    <td>
                      <div style={{ fontFamily: "var(--mono)", fontWeight: 600, color: "var(--text-h)" }}>
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
                    <td style={{ fontSize: "13px" }}>
                      {tx.captureId ? (
                        <span style={{ fontFamily: "var(--mono)", color: "var(--success)" }}>
                          {tx.captureId}
                        </span>
                      ) : tx.failureReason ? (
                        <span style={{ color: "var(--danger)", fontWeight: 500 }}>
                          {tx.failureReason}
                        </span>
                      ) : (
                        <span style={{ color: "var(--text-muted)" }}>—</span>
                      )}
                    </td>
                    <td style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                      {tx.createdAt}
                    </td>
                    <td>
                      {tx.status === "failed" || tx.status === "declined" ? (
                        <button
                          type="button"
                          className="btn-primary btn-sm"
                          onClick={() => onAnalyzeTransaction(tx)}
                          style={{ fontSize: "12px" }}
                        >
                          Diagnose in Copilot
                        </button>
                      ) : (
                        <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                          No action required
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

