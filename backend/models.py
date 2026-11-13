"""SQLAlchemy ORM models for ClearPay AI.

Models:
- PaymentTransaction: Tracks PayPal orders and capture status.
- RecoveryCase: Tracks payment recovery workflows and remediation cases.
- AIAnalysis: Persists Gemini AI diagnostic analyses, recommendations, and checklists.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from database import Base


def _utcnow() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class PaymentTransaction(Base):
    """Payment transaction entity storing PayPal orders and payment capture state."""

    __tablename__ = "payment_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(100), unique=True, index=True, nullable=False)
    capture_id = Column(String(100), nullable=True, index=True)
    amount = Column(String(32), nullable=False, default="10.00")
    currency = Column(String(10), nullable=False, default="USD")
    status = Column(String(50), nullable=False, default="CREATED", index=True)
    failure_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    recovery_cases = relationship(
        "RecoveryCase",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    analyses = relationship(
        "AIAnalysis",
        back_populates="transaction",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize transaction for API responses and dashboard consumption."""
        is_demo = self.order_id.startswith("DEMO-") if self.order_id else False
        created_str = (
            self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if self.created_at
            else ""
        )
        return {
            "id": str(self.id),
            "orderId": self.order_id,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.lower(),
            "captureId": self.capture_id,
            "failureReason": self.failure_reason,
            "createdAt": created_str,
            "isDemo": is_demo,
        }


class RecoveryCase(Base):
    """Payment recovery case entity representing open and resolved payment incidents."""

    __tablename__ = "recovery_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    transaction_id = Column(
        Integer,
        ForeignKey("payment_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id = Column(String(100), nullable=True, index=True)
    payment_reference = Column(String(100), nullable=True)
    problem_description = Column(Text, nullable=False, default="")
    status = Column(String(50), nullable=False, default="Action Required", index=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    transaction = relationship("PaymentTransaction", back_populates="recovery_cases")
    analyses = relationship(
        "AIAnalysis",
        back_populates="recovery_case",
        cascade="all, delete-orphan",
        order_by="desc(AIAnalysis.created_at)",
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize recovery case for API responses and dashboard views."""
        latest_analysis = self.analyses[0] if self.analyses else None
        analysis_data = latest_analysis.to_dict() if latest_analysis else None
        actions_count = (
            len(analysis_data.get("recommended_actions", []))
            if analysis_data and isinstance(analysis_data.get("recommended_actions"), list)
            else 0
        )
        created_str = (
            self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            if self.created_at
            else ""
        )
        is_demo = (
            self.order_id.startswith("DEMO-")
            if self.order_id
            else (self.case_number.startswith("case-demo") or "demo" in self.case_number.lower())
        )
        return {
            "id": str(self.id),
            "caseNumber": self.case_number,
            "orderId": self.order_id,
            "title": self.title,
            "summary": (
                latest_analysis.summary
                if latest_analysis and latest_analysis.summary
                else self.problem_description
            ),
            "status": self.status,
            "actionsCount": actions_count,
            "createdAt": created_str,
            "paymentReference": self.payment_reference,
            "analysis": analysis_data,
            "isDemo": is_demo,
        }


class AIAnalysis(Base):
    """Structured AI diagnostic analysis for a failed payment or recovery case."""

    __tablename__ = "ai_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(
        Integer,
        ForeignKey("recovery_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    transaction_id = Column(
        Integer,
        ForeignKey("payment_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    order_id = Column(String(100), nullable=True, index=True)
    problem_summary = Column(Text, nullable=False, default="")
    issue_title = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    confirmed_facts = Column(JSON, nullable=True)
    possible_causes = Column(JSON, nullable=True)
    recommended_actions = Column(JSON, nullable=True)
    retry_guidance = Column(Text, nullable=True)
    document_checklist = Column(JSON, nullable=True)
    customer_facing_message = Column(Text, nullable=True)
    additional_info_needed = Column(Text, nullable=True)
    source_references = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    recovery_case = relationship("RecoveryCase", back_populates="analyses")
    transaction = relationship("PaymentTransaction", back_populates="analyses")

    def to_dict(self) -> dict[str, Any]:
        """Serialize AI analysis to match AIAnalysisResponse schema."""
        return {
            "id": self.id,
            "issue_title": self.issue_title or "",
            "summary": self.summary or "",
            "confirmed_facts": self.confirmed_facts or [],
            "possible_causes": self.possible_causes or [],
            "recommended_actions": self.recommended_actions or [],
            "retry_guidance": self.retry_guidance or "",
            "document_checklist": self.document_checklist or [],
            "customer_facing_message": self.customer_facing_message or "",
            "additional_info_needed": self.additional_info_needed or "",
            "source_references": self.source_references or [],
        }

