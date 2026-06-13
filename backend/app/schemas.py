from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ClauseOut(BaseModel):
    id: str
    contract_id: str
    clause_type: str
    clause_text: str
    section_header: Optional[str] = None
    risk_level: Optional[str] = None
    risk_reason: Optional[str] = None
    suggested_redline: Optional[str] = None
    is_accepted: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class ContractOut(BaseModel):
    id: str
    filename: str
    file_type: Optional[str] = None
    status: str
    summary: Optional[str] = None
    risk_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    clauses: list[ClauseOut] = []

    class Config:
        from_attributes = True


class ContractListItem(BaseModel):
    id: str
    filename: str
    file_type: Optional[str] = None
    status: str
    risk_score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PlaybookRuleCreate(BaseModel):
    clause_type: str
    preferred_position: str
    risk_if_missing: Optional[str] = None
    risk_if_deviates: Optional[str] = None
    is_required: bool = False
    priority: int = 0


class PlaybookRuleOut(BaseModel):
    id: str
    playbook_id: str
    clause_type: str
    preferred_position: str
    risk_if_missing: Optional[str] = None
    risk_if_deviates: Optional[str] = None
    is_required: bool
    priority: int
    created_at: datetime

    class Config:
        from_attributes = True


class PlaybookCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules: list[PlaybookRuleCreate] = []


class PlaybookOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    rules: list[PlaybookRuleOut] = []

    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    playbook_id: Optional[str] = None


class AnalysisResult(BaseModel):
    contract_id: str
    status: str
    total_clauses: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    risk_score: float
    clauses: list[ClauseOut]
    redline_url: Optional[str] = None


class OrganizationCreate(BaseModel):
    name: str
    email: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None


class OrganizationOut(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    gstin: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PlanOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price_inr: int
    price_usd: int
    max_contracts: int
    max_users: int
    features: list
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionOut(BaseModel):
    id: str
    organization_id: str
    plan_id: str
    status: str
    start_date: datetime
    end_date: Optional[datetime] = None
    contract_count: int
    plan: Optional[PlanOut] = None

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: str
    subscription_id: str
    invoice_number: str
    amount: int
    status: str
    due_date: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class IndianTemplateOut(BaseModel):
    key: str
    label: str
    preferred: str
    risk: str


class PlanCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_inr: int
    price_usd: int = 0
    max_contracts: int = 50
    max_users: int = 1
    features: list = []
    is_active: bool = True
