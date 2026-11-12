import React from "react"
import { type SystemStatus } from "../dashboardTypes"

interface SettingsPageProps {
  backendHealthy: boolean | null
  isCheckingBackend: boolean
  onCheckBackend: () => void
  systemStatus: SystemStatus | null
  demoMode: boolean
  onToggleDemoMode: () => void
}

export const SettingsPage: React.FC<SettingsPageProps> = ({
  backendHealthy,
  isCheckingBackend,
  onCheckBackend,
  systemStatus,
  demoMode,
  onToggleDemoMode,
}) => {
  return (
    <div className="settings-page">
      {/* Scope and Security Notice */}
      <div className="notice-banner notice-info">
        <span style={{ fontSize: "16px" }}>🔒</span>
        <div style={{ flex: 1 }}>
          <strong>Security & Credentials Policy:</strong> API keys, client secrets, and authentication credentials are
          managed strictly via server-side environment variables in <code>backend/.env</code>. They are never exposed
          to client applications, network payloads, or logs.
        </div>
      </div>

      <div style={{ display: "grid", gap: "20px" }}>
        {/* Backend Connection Card */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-title">FastAPI Backend Service</h3>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Core service handling PayPal OAuth, Sandbox orders, payment capture, and Gemini AI queries.
              </p>
            </div>
            <button
              type="button"
              className="btn-secondary btn-sm"
              onClick={onCheckBackend}
              disabled={isCheckingBackend}
            >
              {isCheckingBackend ? "Pinging..." : "Ping /health"}
            </button>
          </div>

          <div
            style={{
              padding: "14px 16px",
              background: "var(--bg)",
              borderRadius: "6px",
              border: "1px solid var(--border)",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "16px",
              fontSize: "13px",
            }}
          >
            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Connection Status</div>
              <div style={{ fontWeight: 600 }}>
                {backendHealthy === true && (
                  <span style={{ color: "#059669" }}>● Online & Healthy (HTTP 200)</span>
                )}
                {backendHealthy === false && (
                  <span style={{ color: "#dc2626" }}>✕ Unreachable (Check if Uvicorn is running)</span>
                )}
                {backendHealthy === null && (
                  <span style={{ color: "#9ca3af" }}>○ Not yet checked</span>
                )}
              </div>
            </div>

            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>API Base URL</div>
              <div style={{ fontFamily: "var(--mono)", fontWeight: 500 }}>
                http://127.0.0.1:8000
              </div>
            </div>

            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>CORS Origin</div>
              <div style={{ fontFamily: "var(--mono)", fontWeight: 500 }}>
                http://localhost:5173
              </div>
            </div>
          </div>
        </div>

        {/* AI & Provider Configuration Status */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-title">AI & Payment Integration Status</h3>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Read-only status reported safely from the backend server.
              </p>
            </div>
          </div>

          <div
            style={{
              padding: "14px 16px",
              background: "var(--bg)",
              borderRadius: "6px",
              border: "1px solid var(--border)",
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "16px",
              fontSize: "13px",
            }}
          >
            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>AI Provider</div>
              <div style={{ fontWeight: 600, color: "var(--text-h)" }}>
                Google Gemini API
              </div>
              <div style={{ fontSize: "12px", color: systemStatus?.gemini_configured ? "#059669" : "#dc2626", marginTop: "2px" }}>
                {systemStatus?.gemini_configured ? "● Key Configured in backend/.env" : "○ Not Configured"}
              </div>
            </div>

            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Gemini Model</div>
              <div style={{ fontFamily: "var(--mono)", fontWeight: 600, color: "var(--text-h)" }}>
                {systemStatus?.model || "gemini-3.5-flash"}
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                Configurable via GEMINI_MODEL env var
              </div>
            </div>

            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Payment Gateway</div>
              <div style={{ fontWeight: 600, color: "var(--text-h)" }}>
                PayPal Sandbox (Orders API v2)
              </div>
              <div style={{ fontSize: "12px", color: systemStatus?.paypal_configured ? "#059669" : "#dc2626", marginTop: "2px" }}>
                {systemStatus?.paypal_configured ? "● Credentials Configured" : "○ Missing Credentials"}
              </div>
            </div>

            <div>
              <div style={{ color: "var(--text-muted)", marginBottom: "4px" }}>Active Environment</div>
              <div style={{ fontWeight: 600, color: "#d97706" }}>
                SANDBOX / DEVELOPMENT
              </div>
              <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                Non-production environment
              </div>
            </div>
          </div>
        </div>

        {/* Demo Mode Configuration */}
        <div className="dashboard-card">
          <div className="card-header-row">
            <div>
              <h3 className="card-title">Demo Mode Simulation</h3>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Simulates successful payment creation and capture when real PayPal Sandbox checkout is blocked by
                cross-border account currency restrictions (e.g., India PayPal accounts).
              </p>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "16px",
              background: demoMode ? "#fffbeb" : "var(--bg)",
              border: demoMode ? "1px solid #fde68a" : "1px solid var(--border)",
              borderRadius: "6px",
              flexWrap: "wrap",
              gap: "12px",
            }}
          >
            <div>
              <div style={{ fontWeight: 600, color: demoMode ? "#92400e" : "var(--text-h)" }}>
                Current Status: {demoMode ? "🟡 Enabled (Simulated Payments)" : "⚪ Disabled (Live Sandbox API Calls)"}
              </div>
              <div style={{ fontSize: "13px", color: demoMode ? "#78350f" : "var(--text-muted)", marginTop: "2px" }}>
                {demoMode
                  ? "Orders and captures return simulated IDs (DEMO-ORDER-123) without calling external PayPal servers."
                  : "All orders and captures call PayPal's sandbox endpoint (https://api-m.sandbox.paypal.com)."}
              </div>
            </div>

            <button
              type="button"
              className={demoMode ? "btn-secondary" : "btn-primary"}
              onClick={onToggleDemoMode}
              style={{ whiteSpace: "nowrap" }}
            >
              {demoMode ? "Disable Demo Mode" : "Enable Demo Mode"}
            </button>
          </div>
        </div>

        {/* Database & Persistence Roadmap Note */}
        <div className="dashboard-card" style={{ opacity: 0.85 }}>
          <h3 className="card-title" style={{ marginBottom: "6px" }}>Database & Data Persistence (Future Phase)</h3>
          <p style={{ fontSize: "13px", color: "var(--text-muted)", lineHeight: 1.5 }}>
            Persistent storage (PostgreSQL, Redis caching, merchant authentication) is planned for the subsequent development phase.
            Current application state resides in browser memory and active session state.
          </p>
        </div>
      </div>
    </div>
  )
}

