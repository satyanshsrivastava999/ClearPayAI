import React from "react"
import { type NavItem } from "../dashboardTypes"

interface SidebarProps {
  currentNav: NavItem
  onNavigate: (item: NavItem) => void
  isOpen: boolean
  onClose: () => void
  activeCasesCount?: number
  sessionTxCount?: number
}

export const Sidebar: React.FC<SidebarProps> = ({
  currentNav,
  onNavigate,
  isOpen,
  onClose,
  activeCasesCount = 0,
  sessionTxCount = 0,
}) => {
  const navItems: { id: NavItem; label: string; icon: string; count?: number }[] = [
    { id: "overview", label: "Overview", icon: "📊" },
    { id: "copilot", label: "Payment Recovery Copilot", icon: "🤖" },
    { id: "transactions", label: "Payment Transactions", icon: "💳", count: sessionTxCount },
    { id: "cases", label: "Recovery Cases", icon: "📁", count: activeCasesCount },
    { id: "settings", label: "Settings", icon: "⚙️" },
  ]

  return (
    <>
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}
      <aside className={`dashboard-sidebar ${isOpen ? "open" : ""}`}>
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <div className="brand-icon">CP</div>
            <div>
              <div className="brand-title">ClearPay AI</div>
              <div className="brand-sub">Recovery Copilot</div>
            </div>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const isActive = currentNav === item.id
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-item-btn ${isActive ? "active" : ""}`}
                onClick={() => {
                  onNavigate(item.id)
                  onClose()
                }}
              >
                <span className="nav-icon" style={{ fontSize: "16px" }}>
                  {item.icon}
                </span>
                <span style={{ flex: 1 }}>{item.label}</span>
                {typeof item.count === "number" && item.count > 0 && (
                  <span
                    style={{
                      fontSize: "11px",
                      background: isActive ? "#3b82f6" : "#374151",
                      color: "#ffffff",
                      padding: "2px 6px",
                      borderRadius: "10px",
                    }}
                  >
                    {item.count}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

        <div className="sidebar-footer">
          <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#9ca3af" }}>
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                backgroundColor: "#10b981",
                display: "inline-block",
              }}
            />
            <span>PayPal Sandbox Active</span>
          </div>
          <div style={{ marginTop: "6px", fontSize: "11px", color: "#6b7280" }}>
            ClearPay AI v0.3.0
          </div>
        </div>
      </aside>
    </>
  )
}

