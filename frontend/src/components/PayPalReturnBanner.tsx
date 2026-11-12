import React from "react"
import { type PaymentState } from "../dashboardTypes"

interface PayPalReturnBannerProps {
  paymentState: PaymentState
  orderId: string | null
  captureId: string | null
  orderAmount: string | null
  orderCurrency: string | null
  errorMessage: string | null
  onDismiss: () => void
}

function getBannerStyle(state: PaymentState) {
  if (state === "completed" || state === "simulated_completed") {
    return { bg: "#ecfdf5", border: "#a7f3d0", color: "#065f46" }
  }
  if (state === "processing" || state === "awaiting_approval") {
    return { bg: "#eff6ff", border: "#bfdbfe", color: "#1e40af" }
  }
  if (state === "declined" || state === "cancelled") {
    return { bg: "#fffbeb", border: "#fde68a", color: "#92400e" }
  }
  return { bg: "#fef2f2", border: "#fecaca", color: "#991b1b" }
}

export const PayPalReturnBanner: React.FC<PayPalReturnBannerProps> = ({
  paymentState,
  orderId,
  captureId,
  orderAmount,
  orderCurrency,
  errorMessage,
  onDismiss,
}) => {
  if (paymentState === "idle" || paymentState === "creating") {
    return null
  }

  const isSuccess = paymentState === "completed" || paymentState === "simulated_completed"
  const isDeclined = paymentState === "declined"
  const isCancelled = paymentState === "cancelled"
  const isProcessing = paymentState === "processing"
  const isAwaiting = paymentState === "awaiting_approval"

  const { bg, border, color } = getBannerStyle(paymentState)

  return (
    <div
      style={{
        padding: "16px 20px",
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: "8px",
        marginBottom: "20px",
        color,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: "12px",
      }}
    >
      <div>
        <div style={{ fontWeight: 700, fontSize: "15px", display: "flex", alignItems: "center", gap: "8px" }}>
          {isSuccess && "✅ PayPal Payment Captured Successfully"}
          {paymentState === "simulated_completed" && "🟡 Simulated Payment Completed (Demo Mode)"}
          {isProcessing && "⏳ Verifying Payment Capture with PayPal..."}
          {isAwaiting && "🕒 Awaiting Buyer Approval on PayPal Sandbox"}
          {isDeclined && "⚠️ Payment Declined by Payer"}
          {isCancelled && "❌ Payment Cancelled by Buyer"}
          {paymentState === "failed" && "❌ Payment Operation Failed"}
        </div>

        <div style={{ fontSize: "13px", marginTop: "4px", display: "flex", gap: "16px", flexWrap: "wrap" }}>
          {orderId && <span><strong>Order ID:</strong> {orderId}</span>}
          {captureId && <span><strong>Capture ID:</strong> {captureId}</span>}
          {orderAmount && orderCurrency && (
            <span><strong>Amount:</strong> {orderAmount} {orderCurrency}</span>
          )}
          {errorMessage && <span><strong>Error:</strong> {errorMessage}</span>}
        </div>
      </div>

      <button
        type="button"
        onClick={onDismiss}
        className="btn-secondary btn-sm"
        style={{ borderColor: border, background: "transparent" }}
      >
        Dismiss
      </button>
    </div>
  )
}
