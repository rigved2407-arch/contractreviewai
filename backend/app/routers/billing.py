import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Organization, Plan, Subscription, Invoice, User
from app.schemas import (
    OrganizationCreate, OrganizationOut,
    PlanOut, PlanCreate,
    SubscriptionOut, InvoiceOut,
)
from app.config import settings
from app.services.invoice_generator import generate_gst_invoice

logger = logging.getLogger("contract-review.billing")
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active == True).all()
    if not plans:
        seed_plans(db)
        plans = db.query(Plan).filter(Plan.is_active == True).all()
    return plans


@router.post("/plans", response_model=PlanOut)
def create_plan(data: PlanCreate, db: Session = Depends(get_db)):
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.post("/organizations", response_model=OrganizationOut)
def create_organization(data: OrganizationCreate, db: Session = Depends(get_db)):
    org = Organization(**data.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).all()


@router.get("/organizations/{org_id}", response_model=OrganizationOut)
def get_organization(org_id: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


@router.post("/organizations/{org_id}/subscribe/{plan_id}", response_model=SubscriptionOut)
def subscribe(org_id: str, plan_id: str, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    existing = db.query(Subscription).filter(
        Subscription.organization_id == org_id,
        Subscription.status.in_(["active", "trial"]),
    ).first()
    if existing:
        existing.status = "cancelled"

    sub = Subscription(
        organization_id=org_id,
        plan_id=plan_id,
        status="active",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(sub)
    db.flush()

    inv_num = f"INV-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"
    invoice_data = Invoice(
        subscription_id=sub.id,
        invoice_number=inv_num,
        amount=plan.price_inr,
        status="pending",
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(invoice_data)
    db.flush()

    # Generate GST invoice PDF
    try:
        invoice_path = generate_gst_invoice(
            invoice_number=inv_num,
            org_name=org.name,
            org_gstin=org.gstin or "",
            org_address=org.address or "",
            org_email=org.email or "",
            plan_name=plan.name,
            amount_inr=plan.price_inr,
        )
        logger.info("GST invoice generated: %s", invoice_path)
    except Exception as e:
        logger.warning("GST invoice generation failed: %s", e)

    # Send invoice email
    if settings.smtp_host:
        users = db.query(User).filter(
            User.organization_id == org_id,
            User.is_active == True,
        ).all()
        for u in users:
            try:
                from app.services.email import send_invoice_email
                import asyncio
                download_url = f"{settings.app_url}/api/billing/invoices/{invoice_data.id}/download"
                asyncio.create_task(
                    send_invoice_email(u.email, u.full_name, inv_num, plan.price_inr, download_url)
                )
            except Exception:
                logger.warning("Failed to send invoice email to %s", u.email)

    db.commit()
    db.refresh(sub)
    return sub


@router.get("/invoices/{invoice_id}/download")
def download_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    pdf_path = Path(settings.storage_dir) / "invoices" / f"{invoice.invoice_number}.docx"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Invoice PDF not yet generated")
    return FileResponse(
        path=str(pdf_path),
        filename=f"{invoice.invoice_number}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/subscriptions/{org_id}", response_model=list[SubscriptionOut])
def list_subscriptions(org_id: str, db: Session = Depends(get_db)):
    subs = (
        db.query(Subscription)
        .filter(Subscription.organization_id == org_id)
        .order_by(Subscription.start_date.desc())
        .all()
    )
    return subs


@router.get("/invoices/{sub_id}", response_model=list[InvoiceOut])
def list_invoices(sub_id: str, db: Session = Depends(get_db)):
    return db.query(Invoice).filter(Invoice.subscription_id == sub_id).all()


def seed_plans(db: Session):
    default_plans = [
        Plan(
            name="Starter",
            description="For solo practitioners and small teams",
            price_inr=30000,
            price_usd=350,
            max_contracts=200,
            max_users=1,
            features=["AI contract analysis", "Clause extraction", "Risk scoring", "Redline generation"],
            is_active=True,
        ),
        Plan(
            name="Professional",
            description="For growing law firms",
            price_inr=75000,
            price_usd=900,
            max_contracts=1000,
            max_users=5,
            features=["Everything in Starter", "Custom playbooks", "Bulk upload", "Priority support", "API access"],
            is_active=True,
        ),
        Plan(
            name="Enterprise",
            description="For large corporate law firms",
            price_inr=250000,
            price_usd=3000,
            max_contracts=5000,
            max_users=25,
            features=["Everything in Professional", "Dedicated account manager", "On-premise deployment", "Custom integrations", "SLA guarantee"],
            is_active=True,
        ),
    ]
    for p in default_plans:
        db.add(p)
    db.commit()
