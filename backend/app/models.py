import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Float, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database import Base


def _uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String(256), unique=True, nullable=False, index=True)
    password_hash = Column(String(256), nullable=False)
    full_name = Column(String(256), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(32), default="admin")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    organization = relationship("Organization", back_populates="users")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String(512), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String(512), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False)
    email = Column(String(256))
    gstin = Column(String(32))
    address = Column(Text)
    created_at = Column(DateTime, default=_utcnow)

    users = relationship("User", back_populates="organization")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    contracts = relationship("Contract", back_populates="organization")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(String, primary_key=True, default=_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    filename = Column(String(512), nullable=False)
    file_path = Column(String(1024))
    file_type = Column(String(16))
    status = Column(String(32), default="uploaded")
    content_text = Column(Text)
    summary = Column(Text)
    risk_score = Column(Float)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    organization = relationship("Organization", back_populates="contracts")
    clauses = relationship("Clause", back_populates="contract", cascade="all, delete-orphan")


class Clause(Base):
    __tablename__ = "clauses"

    id = Column(String, primary_key=True, default=_uuid)
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False, index=True)
    clause_type = Column(String(128))
    clause_text = Column(Text)
    section_header = Column(String(256))
    risk_level = Column(String(16))
    risk_reason = Column(Text)
    suggested_redline = Column(Text)
    is_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)

    contract = relationship("Contract", back_populates="clauses")


class Playbook(Base):
    __tablename__ = "playbooks"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(256), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    rules = relationship("PlaybookRule", back_populates="playbook", cascade="all, delete-orphan")


class PlaybookRule(Base):
    __tablename__ = "playbook_rules"

    id = Column(String, primary_key=True, default=_uuid)
    playbook_id = Column(String, ForeignKey("playbooks.id"), nullable=False)
    clause_type = Column(String(128), nullable=False)
    preferred_position = Column(Text, nullable=False)
    risk_if_missing = Column(Text)
    risk_if_deviates = Column(Text)
    is_required = Column(Boolean, default=False)
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utcnow)

    playbook = relationship("Playbook", back_populates="rules")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True, default=_uuid)
    contract_id = Column(String, ForeignKey("contracts.id"), nullable=False)
    playbook_id = Column(String, ForeignKey("playbooks.id"), nullable=True)
    status = Column(String(32), default="pending")
    total_clauses = Column(Integer, default=0)
    high_risk_count = Column(Integer, default=0)
    medium_risk_count = Column(Integer, default=0)
    low_risk_count = Column(Integer, default=0)
    redline_path = Column(String(1024))
    created_at = Column(DateTime, default=_utcnow)


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False)
    description = Column(Text)
    price_inr = Column(Integer, default=0)
    price_usd = Column(Integer, default=0)
    max_contracts = Column(Integer, default=50)
    max_users = Column(Integer, default=1)
    features = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(String, primary_key=True, default=_uuid)
    organization_id = Column(String, ForeignKey("organizations.id"), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False)
    status = Column(String(32), default="active")
    start_date = Column(DateTime, default=_utcnow)
    end_date = Column(DateTime, nullable=True)
    contract_count = Column(Integer, default=0)

    organization = relationship("Organization", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, default=_uuid)
    subscription_id = Column(String, ForeignKey("subscriptions.id"), nullable=False)
    invoice_number = Column(String(64), unique=True)
    amount = Column(Integer, nullable=False)
    status = Column(String(32), default="pending")
    due_date = Column(DateTime)
    paid_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    subscription = relationship("Subscription", back_populates="invoices")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=_uuid)
    method = Column(String(16))
    path = Column(String(512))
    query_params = Column(String(512))
    status_code = Column(Integer)
    duration_ms = Column(Integer)
    ip_address = Column(String(64))
    user_agent = Column(String(512))
    created_at = Column(DateTime, default=_utcnow)


class DPDPConsent(Base):
    __tablename__ = "dpdp_consents"

    id = Column(String, primary_key=True, default=_uuid)
    principal_name = Column(String(256), nullable=False)
    principal_email = Column(String(256), nullable=False)
    organization = Column(String(256))
    purpose = Column(String(256), nullable=False)
    ip_address = Column(String(64))
    consent_version = Column(String(32), default="1.0")
    consented_at = Column(DateTime, default=_utcnow)
    withdrawn_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class DataSubjectRequest(Base):
    __tablename__ = "dpdp_data_requests"

    id = Column(String, primary_key=True, default=_uuid)
    request_type = Column(String(64), nullable=False)
    principal_name = Column(String(256), nullable=False)
    principal_email = Column(String(256), nullable=False)
    description = Column(Text)
    status = Column(String(32), default="pending")
    requested_at = Column(DateTime, default=_utcnow)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text)


class BreachNotification(Base):
    __tablename__ = "dpdp_breach_notifications"

    id = Column(String, primary_key=True, default=_uuid)
    breach_type = Column(String(128), nullable=False)
    description = Column(Text, nullable=False)
    affected_count = Column(Integer, default=0)
    notified_board = Column(Boolean, default=True)
    notified_principals = Column(Boolean, default=True)
    notification_sent_at = Column(DateTime, default=_utcnow)
    resolved_at = Column(DateTime, nullable=True)
