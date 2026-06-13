from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contract, Playbook, Plan, Clause
from app.config import settings
from app.services.document_parser import parse_document
from app.services.clause_extractor import extract_clauses, generate_summary, generate_compliance_report, PRIORITY_MAP
from app.services.playbook_engine import assess_clauses
from app.services.indian_contract_templates import INDIAN_CLAUSE_TYPES
from app.services.dpdp_compliance import record_consent, get_consent_history, withdraw_consent, create_data_subject_request, get_dpdp_summary

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")
router = APIRouter(tags=["web"])


def _group_clauses_by_risk(clauses):
    grouped = {"high": [], "medium": [], "low": [], "info": []}
    for c in clauses:
        level = (c.risk_level or "info").lower()
        if level not in grouped:
            level = "info"
        grouped[level].append(c)
    return grouped


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, db: Session = Depends(get_db)):
    contracts = db.query(Contract).order_by(Contract.created_at.desc()).all()
    plans = db.query(Plan).filter(Plan.is_active == True).all()
    analysed = db.query(Contract).filter(Contract.status == "analyzed").count()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "contracts": contracts,
        "plans": plans,
        "analysed_count": analysed,
        "indian_clause_count": len(INDIAN_CLAUSE_TYPES),
    })


@router.get("/dashboard/contracts", response_class=HTMLResponse)
def dashboard_contracts(request: Request, db: Session = Depends(get_db)):
    contracts = db.query(Contract).order_by(Contract.created_at.desc()).all()
    return templates.TemplateResponse("partials/contract_list.html", {
        "request": request,
        "contracts": contracts,
    })


@router.get("/contracts/new", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})


@router.get("/contracts/{contract_id}", response_class=HTMLResponse)
def contract_detail_page(request: Request, contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    playbooks = db.query(Playbook).all()
    grouped_clauses = _group_clauses_by_risk(contract.clauses)

    risk_distribution = {level: len(items) for level, items in grouped_clauses.items()}

    compliance = None
    if contract.content_text:
        compliance = generate_compliance_report(contract.content_text)

    return templates.TemplateResponse("contract_detail.html", {
        "request": request,
        "contract": contract,
        "playbooks": playbooks,
        "grouped_clauses": grouped_clauses,
        "risk_distribution": risk_distribution,
        "compliance": compliance,
        "priority_map": PRIORITY_MAP,
    })


@router.get("/billing", response_class=HTMLResponse)
def billing_page(request: Request, db: Session = Depends(get_db)):
    plans = db.query(Plan).filter(Plan.is_active == True).all()
    return templates.TemplateResponse("billing.html", {
        "request": request,
        "plans": plans,
    })


@router.post("/web/upload", response_class=HTMLResponse)
async def web_upload(request: Request, file: UploadFile = File(...), db: Session = Depends(get_db)):
    import uuid
    import re

    raw_name = (file.filename or "upload")
    safe_name = Path(raw_name).name
    safe_name = re.sub(r'[^\w\-_. ]', '_', safe_name)
    safe_name = safe_name.lstrip('.') or "upload"

    allowed = {".pdf", ".docx", ".doc"}
    ext = Path(safe_name).suffix.lower()
    if ext not in allowed:
        contracts = db.query(Contract).order_by(Contract.created_at.desc()).all()
        return templates.TemplateResponse("partials/contract_list.html", {
            "request": request,
            "contracts": contracts,
            "error": f"Unsupported file type: {ext}",
        })

    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    save_path = storage / f"{file_id}{ext}"
    content = await file.read()

    with open(save_path, "wb") as f:
        f.write(content)

    text = parse_document(str(save_path))
    contract = Contract(
        id=file_id, filename=safe_name, file_path=str(save_path),
        file_type=ext, content_text=text, status="parsed",
    )
    db.add(contract)
    db.commit()

    contracts = db.query(Contract).order_by(Contract.created_at.desc()).all()
    return templates.TemplateResponse("partials/contract_list.html", {
        "request": request,
        "contracts": contracts,
    })


@router.post("/web/analyze/{contract_id}", response_class=HTMLResponse)
def web_analyze(
    request: Request, contract_id: str,
    playbook_id: str = None, db: Session = Depends(get_db),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract or not contract.content_text:
        return HTMLResponse("Contract not found", status_code=404)

    clauses_data = extract_clauses(contract.content_text)
    clauses_data = assess_clauses(clauses_data, playbook_id, db)

    db.query(Clause).filter(Clause.contract_id == contract_id).delete()

    risk_counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
    for cd in clauses_data:
        rl = (cd.get("risk_level") or "info").lower()
        if rl not in risk_counts:
            rl = "info"
        risk_counts[rl] += 1

        risk_reason = cd.get("risk_reason") or ""
        statute = cd.get("statute", "")
        if statute and risk_reason and statute not in risk_reason:
            risk_reason = f"[{statute}] {risk_reason}"

        clause = Clause(
            contract_id=contract_id,
            clause_type=cd.get("clause_type", "Unknown"),
            clause_text=cd.get("clause_text", ""),
            section_header=cd.get("section_header", ""),
            risk_level=rl,
            risk_reason=risk_reason,
            suggested_redline=cd.get("suggested_redline"),
        )
        db.add(clause)

    if not contract.summary:
        contract.summary = generate_summary(contract.content_text)

    total = len(clauses_data)
    denominator = max(total * 3, 1)
    contract.risk_score = round(
        (risk_counts["high"] * 3 + risk_counts["medium"] * 2 + risk_counts["low"] * 1) / denominator * 100,
        1,
    )
    contract.status = "analyzed"
    db.commit()
    db.refresh(contract)

    grouped = _group_clauses_by_risk(contract.clauses)
    compliance = generate_compliance_report(contract.content_text)
    return templates.TemplateResponse("partials/clause_list.html", {
        "request": request,
        "contract": contract,
        "grouped_clauses": grouped,
        "risk_distribution": risk_counts,
        "compliance": compliance,
        "priority_map": PRIORITY_MAP,
    })


@router.get("/dpdp/privacy", response_class=HTMLResponse)
def dpdp_privacy(request: Request):
    return templates.TemplateResponse("dpdp/privacy.html", {"request": request, "settings": settings})


@router.get("/dpdp/consent", response_class=HTMLResponse)
def dpdp_consent(request: Request, db: Session = Depends(get_db)):
    email = request.query_params.get("email")
    consents = get_consent_history(db, email)
    return templates.TemplateResponse("dpdp/consent.html", {"request": request, "consents": consents})


@router.post("/dpdp/consent/{consent_id}/withdraw")
def dpdp_withdraw_consent(request: Request, consent_id: str, db: Session = Depends(get_db)):
    withdraw_consent(db, consent_id)
    return RedirectResponse(url="/dpdp/consent", status_code=303)


@router.get("/dpdp/data-request", response_class=HTMLResponse)
def dpdp_data_request_page(request: Request):
    return templates.TemplateResponse("dpdp/data_request.html", {"request": request})


@router.post("/dpdp/data-request")
def dpdp_submit_data_request(
    request: Request,
    request_type: str = Form("access"),
    principal_name: str = Form(...),
    principal_email: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
):
    result = create_data_subject_request(db, request_type, principal_name, principal_email, description)
    return templates.TemplateResponse("dpdp/data_request.html", {
        "request": request,
        "submitted": True,
        "result": result,
    })


@router.get("/dpdp/compliance", response_class=HTMLResponse)
def dpdp_compliance_dashboard(request: Request, db: Session = Depends(get_db)):
    summary = get_dpdp_summary(db)
    return templates.TemplateResponse("dpdp/compliance.html", {"request": request, "summary": summary})
