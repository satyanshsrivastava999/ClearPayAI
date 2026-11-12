import React from "react"
import { type NavItem } from "../dashboardTypes"

interface HeaderProps {
  currentNav: NavItem
  onToggleMobileNav: () => void
  backendHealthy: boolean | null
  isCheckingBackend: boolean
  onCheckBackend: () => void
  demoMode: boolean
  onToggleDemoMode: () => void
}

const NAV_TITLES: Record<NavItem, string> = {
  overview: "Overview Dashboard",
  copilot: "Payment Recovery Copilot",
  transactions: "Payment Transactions",
  cases: "Recovery Cases",
  settings: "Settings & System Status",
}

export const Header: React.FC<HeaderProps> = ({
  currentNav,
  onToggleMobileNav,
  backendHealthy,
  isCheckingBackend,
  onCheckBackend,
  demoMode,
  onToggleDemoMode,
}) => {
  return (
    <header className="dashboard-header">
      <div className="header-left">
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={onToggleMobileNav}
          aria-label="Toggle navigation"
        >
          ☰
        </button>
        <div>
          <h1 className="page-title">{NAV_TITLES[currentNav]}</h1>
        </div>
      </div>

      <div className="header-right">
        {/* Backend health status pill */}
        <button
          type="button"
          onClick={onCheckBackend}
          disabled={isCheckingBackend}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "5px 12px",
            borderRadius: "9999px",
            border: "1px solid var(--border)",
            background: "var(--card-bg)",
            fontSize: "12px",
            fontWeight: 500,
            cursor: "pointer",
            color: varStatusColor(backendHealthy),
          }}
          title="Click to re-check backend connection"
        >
          <span
            style={{
              width: "7px",
              height: "7px",
              borderRadius: "50%",
              backgroundColor: varStatusColor(backendHealthy),
              display: "inline-block",
            }}
          />
          {isCheckingBackend
            ? "Checking API..."
            : backendHealthy === true
            ? "API Online"
            : backendHealthy === false
            ? "API Offline"
            : "Check API"}
        </button>

        {/* Demo Mode Toggle */}
        <button
          type="button"
          onClick={onToggleDemoMode}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "5px 12px",
            borderRadius: "9999px",
            border: demoMode ? "1px solid #fde68a" : "1px solid var(--border)",
            background: demoMode ? "#fef3c7" : "var(--card-bg)",
            color: demoMode ? "#92400e" : "var(--text-muted)",
            fontSize: "12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
          title="Toggle Demo Mode (simulates transactions when PayPal Sandbox checkout is blocked)"
        >
          <span>{demoMode ? "🟡 Demo Mode: ON" : "⚪ Demo Mode: OFF"}</span>
        </button>
      </div>
    </header>
  )
}

function varStatusColor(status: boolean | null): string {
  if (status === true) return "#10b981"
  if (status === false) return "#ef4444"
  return "#6b7280"
}

