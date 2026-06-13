import datetime
import json
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

DPDP_NOTICE = """
**Digital Personal Data Protection Act, 2023 — Privacy Notice**

**1. Data Fiduciary:** [Your Firm Name] acts as the Data Fiduciary under the DPDP Act, 2023.

**2. Purpose of Processing:** We process personal data solely for the purpose of contract review / due diligence analysis as instructed by our clients (Data Principals). Data is processed only to the extent necessary for providing these legal technology services.

**3. Lawful Basis:** Processing is based on consent obtained from Data Principals and/or contractual necessity under Section 4 of the DPDP Act.

**4. Data Collected:** Name, email address, organizational affiliation, and document content uploaded for analysis. We do not collect sensitive personal data unless explicitly provided within uploaded documents.

**5. Data Retention:** Personal data is retained for a period of {retention_days} days from the date of collection, after which it is automatically deleted in accordance with Section 9 of the DPDP Act (Storage Limitation).

**6. Data Principal Rights:** Under Sections 11-14 of the DPDP Act, you have the right to:
   - Access your personal data
   - Correction of inaccurate data
   - Erasure of your data
   - Grievance redressal

**7. Cross-Border Transfer:** Personal data is stored and processed exclusively within India. No cross-border data transfer occurs, in compliance with Section 16 of the DPDP Act.

**8. Data Protection Officer:** For any DPDP-related queries, grievances, or to exercise your rights, contact the Data Protection Officer at: dpo@[yourdomain].com

**9. Breach Notification:** In the event of a data breach, we will notify the Data Protection Board of India and affected Data Principals within 72 hours as required under Section 8(6) of the DPDP Act.

**10. Consent Withdrawal:** You may withdraw your consent at any time by contacting the DPO. Withdrawal does not affect the lawfulness of processing before such withdrawal.
"""


def record_consent(
    db: Session,
    principal_name: str,
    principal_email: str,
    purpose: str,
    ip_address: str,
    organization: Optional[str] = None,
) -> dict:
    from app.models import DPDPConsent
    consent = DPDPConsent(
        principal_name=principal_name,
        principal_email=principal_email,
        organization=organization,
        purpose=purpose,
        ip_address=ip_address,
        consented_at=datetime.datetime.now(datetime.timezone.utc),
        consent_version="1.0",
        is_active=True,
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return {
        "id": consent.id,
        "principal_email": consent.principal_email,
        "purpose": consent.purpose,
        "consented_at": consent.consented_at.isoformat(),
        "status": "recorded",
    }


def verify_consent(db: Session, principal_email: str, purpose: str) -> bool:
    from app.models import DPDPConsent
    consent = db.query(DPDPConsent).filter(
        DPDPConsent.principal_email == principal_email,
        DPDPConsent.purpose == purpose,
        DPDPConsent.is_active == True,
    ).first()
    return consent is not None


def withdraw_consent(db: Session, consent_id: str) -> bool:
    from app.models import DPDPConsent
    consent = db.query(DPDPConsent).filter(DPDPConsent.id == consent_id).first()
    if consent:
        consent.is_active = False
        consent.withdrawn_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        return True
    return False


def create_data_subject_request(
    db: Session,
    request_type: str,
    principal_name: str,
    principal_email: str,
    description: str,
) -> dict:
    from app.models import DataSubjectRequest
    dsr = DataSubjectRequest(
        request_type=request_type,
        principal_name=principal_name,
        principal_email=principal_email,
        description=description,
        status="pending",
        requested_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(dsr)
    db.commit()
    db.refresh(dsr)
    return {
        "id": dsr.id,
        "request_type": dsr.request_type,
        "status": dsr.status,
        "message": f"Your {request_type} request has been received. We will process it within 30 days as required under Section 12 of the DPDP Act.",
    }


def get_consent_history(db: Session, email: Optional[str] = None) -> list[dict]:
    from app.models import DPDPConsent
    q = db.query(DPDPConsent)
    if email:
        q = q.filter(DPDPConsent.principal_email == email)
    results = []
    for c in q.order_by(DPDPConsent.consented_at.desc()).all():
        results.append({
            "id": c.id,
            "principal_name": c.principal_name,
            "principal_email": c.principal_email,
            "organization": c.organization,
            "purpose": c.purpose,
            "consented_at": c.consented_at.isoformat() if c.consented_at else None,
            "withdrawn_at": c.withdrawn_at.isoformat() if c.withdrawn_at else None,
            "is_active": c.is_active,
        })
    return results


def get_data_subject_requests(db: Session, email: Optional[str] = None) -> list[dict]:
    from app.models import DataSubjectRequest
    q = db.query(DataSubjectRequest)
    if email:
        q = q.filter(DataSubjectRequest.principal_email == email)
    results = []
    for r in q.order_by(DataSubjectRequest.requested_at.desc()).all():
        results.append({
            "id": r.id,
            "request_type": r.request_type,
            "principal_name": r.principal_name,
            "principal_email": r.principal_email,
            "description": r.description,
            "status": r.status,
            "requested_at": r.requested_at.isoformat() if r.requested_at else None,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })
    return results


def log_breach_notification(db: Session, breach_type: str, description: str, affected_count: int):
    from app.models import BreachNotification
    notice = BreachNotification(
        breach_type=breach_type,
        description=description,
        affected_count=affected_count,
        notified_board=True,
        notified_principals=True,
        notification_sent_at=datetime.datetime.now(datetime.timezone.utc),
    )
    db.add(notice)
    db.commit()


def check_retention_expiry(db: Session):
    from app.models import DPDPConsent, DataSubjectRequest
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=settings.data_retention_days or 365
    )

    expired_consents = db.query(DPDPConsent).filter(
        DPDPConsent.consented_at < cutoff,
        DPDPConsent.is_active == True,
    ).all()

    for c in expired_consents:
        c.is_active = False
        c.withdrawn_at = datetime.datetime.now(datetime.timezone.utc)

    expired_requests = db.query(DataSubjectRequest).filter(
        DataSubjectRequest.requested_at < cutoff,
        DataSubjectRequest.status == "pending",
    ).all()

    for r in expired_requests:
        r.status = "expired"

    if expired_consents or expired_requests:
        db.commit()

    return {
        "consents_expired": len(expired_consents),
        "requests_expired": len(expired_requests),
    }


def get_dpdp_summary(db: Session) -> dict:
    from app.models import DPDPConsent, DataSubjectRequest, BreachNotification
    active_consents = db.query(DPDPConsent).filter(DPDPConsent.is_active == True).count()
    total_consents = db.query(DPDPConsent).count()
    pending_requests = db.query(DataSubjectRequest).filter(
        DataSubjectRequest.status == "pending"
    ).count()
    total_requests = db.query(DataSubjectRequest).count()
    total_breaches = db.query(BreachNotification).count()
    return {
        "active_consents": active_consents,
        "total_consents": total_consents,
        "pending_data_requests": pending_requests,
        "total_data_requests": total_requests,
        "total_breaches": total_breaches,
        "retention_days": settings.data_retention_days or 365,
        "data_residency": settings.data_residency or "local",
        "dpdp_compliance": settings.dpdp_compliance,
        "encryption_enabled": settings.encrypt_documents,
    }
