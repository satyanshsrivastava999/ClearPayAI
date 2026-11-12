import React from "react"
import {
  formatDocumentItem,
  type AIAnalysisResponse,
} from "../aiCopilot"

interface CopilotPageProps {
  aiProvider: string
  setAiProvider: (val: string) => void
  aiStatus: string
  setAiStatus: (val: string) => void
  aiErrorCode: string
  setAiErrorCode: (val: string) => void
  aiErrorMessage: string
  setAiErrorMessage: (val: string) => void
  aiAmount: string
  setAiAmount: (val: string) => void
  aiCurrency: string
  setAiCurrency: (val: string) => void
  aiPreviousAttempts: number
  setAiPreviousAttempts: (val: number) => void
  aiIncidentDescription: string
  setAiIncidentDescription: (val: string) => void
  aiAdditionalDiagnostics: string
  setAiAdditionalDiagnostics: (val: string) => void
  aiLoading: boolean
  aiError: string | null
  aiResult: AIAnalysisResponse | null
  aiFollowUpQuestion: string
  setAiFollowUpQuestion: (val: string) => void
  aiFollowUpLoading: boolean
  aiFollowUpError: string | null
  aiHistory: { question: string; answer: string }[]
  onAnalyzePayment: () => void
  onAskFollowUp: () => void
  onResetAnalysis: () => void
}

export const CopilotPage: React.FC<CopilotPageProps> = ({
  aiProvider,
  setAiProvider,
  aiStatus,
  setAiStatus,
  aiErrorCode,
  setAiErrorCode,
  aiErrorMessage,
  setAiErrorMessage,
  aiAmount,
  setAiAmount,
  aiCurrency,
  setAiCurrency,
  aiPreviousAttempts,
  setAiPreviousAttempts,
  aiIncidentDescription,
  setAiIncidentDescription,
  aiAdditionalDiagnostics,
  setAiAdditionalDiagnostics,
  aiLoading,
  aiError,
  aiResult,
  aiFollowUpQuestion,
  setAiFollowUpQuestion,
  aiFollowUpLoading,
  aiFollowUpError,
  aiHistory,
  onAnalyzePayment,
  onAskFollowUp,
  onResetAnalysis,
}) => {
  return (
    <div className="copilot-page">
      {/* Advisory Notice */}
      <div className="notice-banner notice-info">
        <span style={{ fontSize: "16px" }}>ℹ️</span>
        <div>
          <strong>Notice:</strong> AI-generated recommendations based on the submitted information. Verify important
          decisions with the payment provider. AI recommendations do not modify transaction status or trigger payment
          capture, retries, or refunds.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: aiResult ? "1fr 1fr" : "1fr", gap: "24px", alignItems: "start" }}>
        {/* Incident Form Card */}
        <div className="dashboard-card" style={{ marginBottom: 0 }}>
          <div className="card-header-row">
            <div>
              <h2 className="card-title">Payment Incident Details</h2>
              <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                Submit transaction parameters for AI diagnosis.
              </p>
            </div>
            {aiResult && (
              <button
                type="button"
                className="btn-secondary btn-sm"
                onClick={onResetAnalysis}
              >
                Clear / New Incident
              </button>
            )}
          </div>

          <div style={{ display: "grid", gap: "12px" }}>
            <div>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                Payment Provider
              </label>
              <select
                value={aiProvider}
                onChange={(e) => setAiProvider(e.target.value)}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
              >
                <option value="PayPal">PayPal</option>
              </select>
            </div>

            <div>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                Transaction Status
              </label>
              <select
                value={aiStatus}
                onChange={(e) => setAiStatus(e.target.value)}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
              >
                <option value="FAILED">FAILED</option>
                <option value="DECLINED">DECLINED</option>
                <option value="PENDING">PENDING</option>
                <option value="ON_HOLD">ON_HOLD</option>
              </select>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                  Error Code (optional)
                </label>
                <input
                  type="text"
                  value={aiErrorCode}
                  onChange={(e) => setAiErrorCode(e.target.value)}
                  placeholder="e.g. INSTRUMENT_DECLINED"
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                  Error Message (optional)
                </label>
                <input
                  type="text"
                  value={aiErrorMessage}
                  onChange={(e) => setAiErrorMessage(e.target.value)}
                  placeholder="e.g. The instrument was declined."
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
                />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                  Amount (optional)
                </label>
                <input
                  type="text"
                  value={aiAmount}
                  onChange={(e) => setAiAmount(e.target.value)}
                  placeholder="e.g. 10.00"
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
                />
              </div>
              <div>
                <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                  Currency (optional)
                </label>
                <input
                  type="text"
                  value={aiCurrency}
                  onChange={(e) => setAiCurrency(e.target.value)}
                  placeholder="USD"
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                Previous Attempts
              </label>
              <input
                type="number"
                min={0}
                value={aiPreviousAttempts}
                onChange={(e) => setAiPreviousAttempts(Math.max(0, Number(e.target.value)))}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)" }}
              />
            </div>

            <div>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                Incident Description
              </label>
              <textarea
                value={aiIncidentDescription}
                onChange={(e) => setAiIncidentDescription(e.target.value)}
                placeholder="Describe what happened..."
                rows={3}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)", resize: "vertical" }}
              />
            </div>

            <div>
              <label style={{ display: "block", marginBottom: "4px", fontWeight: "bold", fontSize: "13px" }}>
                Additional Diagnostics (optional)
              </label>
              <textarea
                value={aiAdditionalDiagnostics}
                onChange={(e) => setAiAdditionalDiagnostics(e.target.value)}
                placeholder="Any additional non-sensitive diagnostic info..."
                rows={2}
                style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid var(--border)", background: "var(--card-bg)", color: "var(--text-h)", resize: "vertical" }}
              />
            </div>

            <button
              type="button"
              className="btn-primary"
              onClick={onAnalyzePayment}
              disabled={aiLoading}
              style={{ width: "100%", padding: "10px", marginTop: "4px" }}
            >
              {aiLoading ? "Analyzing Incident with Gemini..." : "⚡ Analyze Payment Failure"}
            </button>
          </div>

          {aiError && (
            <div
              style={{
                marginTop: "16px",
                padding: "12px",
                background: "#fee2e2",
                color: "#dc2626",
                borderRadius: "8px",
                fontSize: "13px",
              }}
            >
              <strong>Error:</strong> {aiError}
            </div>
          )}
        </div>

        {/* Structured AI Diagnosis Result */}
        {aiResult && (
          <div className="dashboard-card" style={{ marginBottom: 0 }}>
            <div
              style={{
                padding: "16px",
                background: "var(--bg)",
                borderRadius: "8px",
                border: "1px solid var(--border)",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ marginTop: 0, fontSize: "18px", color: "var(--text-h)" }}>
                {aiResult.issue_title || "Payment Issue Analysis"}
              </h3>
              <p style={{ color: "var(--text)", margin: 0, fontSize: "14px", lineHeight: 1.5 }}>
                {aiResult.summary || "No summary provided."}
              </p>
            </div>

            {/* Confirmed Facts */}
            {aiResult.confirmed_facts && aiResult.confirmed_facts.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "8px" }}>
                  Confirmed Facts (from submitted data)
                </h4>
                <ul style={{ paddingLeft: "20px", margin: 0 }}>
                  {aiResult.confirmed_facts.map((fact, i) => (
                    <li key={i} style={{ marginBottom: "4px", fontSize: "13px" }}>
                      {fact}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Possible Causes */}
            {aiResult.possible_causes && aiResult.possible_causes.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "8px" }}>
                  Possible Causes (AI Hypotheses — Not Verified Facts)
                </h4>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {aiResult.possible_causes.map((cause, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "10px 12px",
                        background: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: "6px",
                      }}
                    >
                      <div style={{ fontWeight: 600, fontSize: "13px", color: "var(--text-h)", display: "flex", justifyContent: "space-between" }}>
                        <span>{cause.description}</span>
                        <span style={{ color: cause.confidence >= 70 ? "#059669" : "#d97706" }}>
                          {cause.confidence}% confidence
                        </span>
                      </div>
                      <p style={{ margin: "4px 0 0", fontSize: "12px", color: "var(--text-muted)" }}>
                        <strong>Evidence:</strong> {cause.evidence}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Prioritized Recovery Actions */}
            {aiResult.recommended_actions && aiResult.recommended_actions.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "8px" }}>
                  Prioritized Recovery Actions (AI Recommendations)
                </h4>
                <ol style={{ paddingLeft: "20px", margin: 0 }}>
                  {aiResult.recommended_actions.map((action, i) => (
                    <li key={i} style={{ marginBottom: "6px", fontSize: "13px" }}>
                      {action}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {/* Retry Guidance */}
            <div style={{ marginTop: "16px" }}>
              <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "6px" }}>
                Retry Guidance (AI Guidance)
              </h4>
              <p style={{ color: "var(--text)", fontSize: "13px", margin: 0 }}>
                {aiResult.retry_guidance || "No specific retry guidance provided."}
              </p>
            </div>

            {/* Conditional Document Checklist */}
            {aiResult.document_checklist && aiResult.document_checklist.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "8px" }}>
                  Conditional Document Checklist (AI Guidance)
                </h4>
                {aiResult.document_checklist.map((rawDoc, i) => {
                  const doc = formatDocumentItem(rawDoc)
                  return (
                    <div
                      key={i}
                      style={{
                        marginBottom: "10px",
                        padding: "10px 12px",
                        background: "#fffbeb",
                        borderRadius: "6px",
                        fontSize: "13px",
                        border: "1px solid #fde68a",
                      }}
                    >
                      <p style={{ fontWeight: 600, margin: "0 0 4px 0", color: "#92400e" }}>
                        📄 {doc.name}
                      </p>
                      <p style={{ margin: "0 0 2px 0", color: "#78350f" }}>
                        <strong>Purpose:</strong> {doc.purpose}
                      </p>
                      {doc.condition && (
                        <p style={{ margin: "0 0 2px 0", color: "#78350f" }}>
                          <strong>Condition Needed:</strong> {doc.condition}
                        </p>
                      )}
                      {doc.nextStep && (
                        <p style={{ margin: "0 0 2px 0", color: "#78350f" }}>
                          <strong>Recommended Next Step:</strong> {doc.nextStep}
                        </p>
                      )}
                      {doc.source && (
                        <p style={{ margin: "0", color: "#78350f" }}>
                          <strong>Official Source:</strong>{" "}
                          <a href={doc.source} target="_blank" rel="noopener noreferrer" style={{ color: "#2563eb" }}>
                            {doc.source}
                          </a>
                        </p>
                      )}
                    </div>
                  )
                })}
              </div>
            )}

            {/* Customer Facing Message */}
            <div style={{ marginTop: "16px" }}>
              <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "6px" }}>
                Customer-Facing Message (Draft)
              </h4>
              <div style={{ padding: "10px 12px", background: "var(--bg)", border: "1px solid var(--border)", borderRadius: "6px", fontSize: "13px", fontStyle: "italic" }}>
                "{aiResult.customer_facing_message || "No customer message generated."}"
              </div>
            </div>

            {/* Additional Info Needed */}
            <div style={{ marginTop: "16px" }}>
              <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "6px" }}>
                Additional Information Needed
              </h4>
              <p style={{ color: "var(--text)", fontSize: "13px", margin: 0 }}>
                {aiResult.additional_info_needed || "None specified."}
              </p>
            </div>

            {/* Source References */}
            {aiResult.source_references && aiResult.source_references.length > 0 && (
              <div style={{ marginTop: "16px" }}>
                <h4 style={{ fontSize: "14px", textTransform: "uppercase", letterSpacing: "0.5px", color: "var(--text-muted)", marginBottom: "6px" }}>
                  Official Source References
                </h4>
                <ul style={{ paddingLeft: "20px", margin: 0 }}>
                  {aiResult.source_references.map((ref, i) => (
                    <li key={i} style={{ marginBottom: "4px", fontSize: "13px" }}>
                      <a href={ref} target="_blank" rel="noopener noreferrer" style={{ color: "#2563eb" }}>
                        {ref}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Follow-up Section */}
            <div style={{ marginTop: "24px", padding: "16px", background: "var(--bg)", borderRadius: "8px", border: "1px solid var(--border)" }}>
              <h4 style={{ marginTop: 0, fontSize: "15px" }}>Ask Follow-up Question</h4>
              <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "-2px", marginBottom: "12px" }}>
                Ask specific questions about this incident diagnosis without re-entering transaction details.
              </p>

              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  value={aiFollowUpQuestion}
                  onChange={(e) => setAiFollowUpQuestion(e.target.value)}
                  placeholder="e.g. What information should I collect before contacting the provider?"
                  style={{ flex: 1, padding: "8px 12px", borderRadius: "6px", border: "1px solid var(--border)", fontSize: "13px", background: "var(--card-bg)", color: "var(--text-h)" }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") void onAskFollowUp()
                  }}
                  disabled={aiFollowUpLoading}
                />
                <button
                  type="button"
                  className="btn-primary"
                  onClick={onAskFollowUp}
                  disabled={aiFollowUpLoading || !aiFollowUpQuestion.trim()}
                >
                  {aiFollowUpLoading ? "Asking..." : "Ask"}
                </button>
              </div>

              {aiFollowUpError && (
                <div style={{ marginTop: "12px", padding: "10px", background: "#fee2e2", color: "#dc2626", borderRadius: "6px", fontSize: "13px" }}>
                  Error: {aiFollowUpError}
                </div>
              )}

              {/* Conversation History */}
              {aiHistory.length > 0 && (
                <div style={{ marginTop: "16px", display: "grid", gap: "10px" }}>
                  {aiHistory.map((turn, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: "12px",
                        background: "var(--card-bg)",
                        borderRadius: "6px",
                        border: "1px solid var(--border)",
                        fontSize: "13px",
                      }}
                    >
                      <p style={{ margin: "0 0 6px 0", fontWeight: 600, color: "#2563eb" }}>
                        Q: {turn.question}
                      </p>
                      <p style={{ margin: 0, color: "var(--text)", whiteSpace: "pre-wrap" }}>
                        {turn.answer}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

