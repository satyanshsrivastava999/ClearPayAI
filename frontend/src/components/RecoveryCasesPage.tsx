import React from "react"
import { type RecoveryCaseRecord, DEMO_CASES } from "../dashboardTypes"

interface RecoveryCasesPageProps {
  recoveryCases: RecoveryCaseRecord[]
  onOpenCaseInCopilot: (c: RecoveryCaseRecord) => void
  onNavigateToCopilot: () => void
  showDemoData: boolean
  onToggleDemoData: (enabled: boolean) => void
}

export const RecoveryCasesPage: React.FC<RecoveryCasesPageProps> = ({
  recoveryCases,
  onOpenCaseInCopilot,
  onNavigateToCopilot,
  showDemoData,
  onToggleDemoData,
}) => {
  const allCases = showDemoData && recoveryCases.length === 0
    ? DEMO_CASES
    : recoveryCases

  return (
    <div className="recovery-cases-page">
      {/* Scope and Non-persistence Notice */}
      <div className="notice-banner notice-warning">
        <span style={{ fontSize: "16px" }}>📁</span>
        <div style={{ flex: 1 }}>
          <strong>Non-Persistent Case Management Interface:</strong> Cases listed below are session-scoped payment
          incidents analyzed by the Payment Recovery Copilot during your active session. They are not stored in a persistent
          database and will reset if the page is refreshed. Case records are retained when switching tabs.
        </div>
        <button
          type="button"
          onClick={() => onToggleDemoData(!showDemoData)}
          className="btn-secondary btn-sm"
          style={{ whiteSpace: "nowrap" }}
        >
          {showDemoData ? "Hide Demo Cases" : "Preview Demo Cases"}
        </button>
      </div>

      {showDemoData && recoveryCases.length === 0 && (
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
          <span>Sample recovery cases displayed for UI inspection. No database storage exists.</span>
        </div>
      )}

      {/* Header Row */}
      <div className="dashboard-card" style={{ padding: "16px 20px", marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <h2 style={{ fontSize: "16px", marginBottom: "4px" }}>Active Recovery Cases ({allCases.length})</h2>
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
              Incidents diagnosed with Gemini AI with recommended merchant remediation steps.
            </p>
          </div>
          <button
            type="button"
            className="btn-primary"
            onClick={onNavigateToCopilot}
          >
            + Analyze New Incident
          </button>
        </div>
      </div>

      {/* Cases List */}
      {allCases.length === 0 ? (
        <div className="dashboard-card">
          <div className="empty-state">
            <div className="empty-state-icon">📂</div>
            <div className="empty-state-title">No recovery cases recorded in this session</div>
            <div className="empty-state-desc">
              When you submit a failed or held payment in the Payment Recovery Copilot, a structured case will automatically appear here with AI-generated next steps.
            </div>
            <button
              type="button"
              className="btn-primary btn-sm"
              onClick={onNavigateToCopilot}
            >
              Open Payment Recovery Copilot
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {allCases.map((c) => {
            const topAction =
              c.analysis?.recommended_actions && c.analysis.recommended_actions.length > 0
                ? c.analysis.recommended_actions[0]
                : "Review incident details"

            return (
              <div key={c.id} className="dashboard-card" style={{ marginBottom: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", marginBottom: "12px" }}>
                  <div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <h3 style={{ fontSize: "16px", color: "var(--text-h)" }}>{c.title}</h3>
                      {c.isDemo && (
                        <span className="status-badge badge-demo" style={{ fontSize: "10px" }}>
                          DEMO DATA
                        </span>
                      )}
                      <span className="status-badge badge-pending" style={{ fontSize: "11px" }}>
                        {c.status}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "var(--text-muted)", display: "flex", gap: "12px" }}>
                      <span>Case ID: <code>{c.id}</code></span>
                      {c.orderId && <span>Order ID: <code>{c.orderId}</code></span>}
                      <span>Recorded: {c.createdAt}</span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="btn-secondary btn-sm"
                    onClick={() => onOpenCaseInCopilot(c)}
                  >
                    View in Copilot ↗
                  </button>
                </div>

                <div
                  style={{
                    padding: "12px 14px",
                    background: "var(--bg)",
                    borderRadius: "6px",
                    border: "1px solid var(--border)",
                    marginBottom: "12px",
                    fontSize: "13px",
                    lineHeight: 1.5,
                  }}
                >
                  <strong style={{ color: "var(--text-h)" }}>Summary: </strong>
                  <span>{c.summary}</span>
                </div>

                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    flexWrap: "wrap",
                    gap: "12px",
                    fontSize: "13px",
                    paddingTop: "8px",
                    borderTop: "1px solid var(--border-subtle)",
                  }}
                >
                  <div>
                    <strong style={{ color: "#2563eb" }}>Recommended Next Action: </strong>
                    <span style={{ color: "var(--text)" }}>{topAction}</span>
                  </div>

                  <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                    AI Analysis: <span style={{ color: "#059669", fontWeight: 600 }}>● Active ({c.actionsCount} actions)</span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

