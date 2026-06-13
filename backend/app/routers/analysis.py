import json
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contract, Clause, AnalysisRun
from app.schemas import AnalysisRequest, AnalysisResult, ClauseOut
from app.config import settings
from app.services.clause_extractor import extract_clauses, generate_summary
from app.services.playbook_engine import assess_clauses
from app.services.redliner import generate_redlined_docx

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/{contract_id}", response_model=AnalysisResult)
def analyze_contract(
    contract_id: str,
    req: AnalysisRequest,
    db: Session = Depends(get_db),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    if not contract.content_text:
        raise HTTPException(status_code=400, detail="Contract has no extracted text")

    analysis = AnalysisRun(
        id=str(uuid.uuid4()),
        contract_id=contract_id,
        playbook_id=req.playbook_id,
        status="running",
    )
    db.add(analysis)
    db.commit()

    try:
        clauses_data = extract_clauses(contract.content_text)
        clauses_data = assess_clauses(clauses_data, req.playbook_id, db)

        db.query(Clause).filter(Clause.contract_id == contract_id).delete()

        risk_counts = {"high": 0, "medium": 0, "low": 0, "info": 0}
        for cd in clauses_data:
            rl = cd.get("risk_level", "info") or "info"
            risk_counts[rl] = risk_counts.get(rl, 0) + 1

            clause = Clause(
                contract_id=contract_id,
                clause_type=cd.get("clause_type", "Unknown"),
                clause_text=cd.get("clause_text", ""),
                section_header=cd.get("section_header", ""),
                risk_level=rl,
                risk_reason=cd.get("risk_reason"),
                suggested_redline=cd.get("suggested_redline"),
            )
            db.add(clause)

        if not contract.summary:
            contract.summary = generate_summary(contract.content_text)

        total = len(clauses_data)
        risk_score = round(
            (risk_counts["high"] * 3 + risk_counts["medium"] * 2 + risk_counts["low"] * 1) / max(total * 3, 1) * 100,
            1,
        )
        contract.risk_score = risk_score
        contract.status = "analyzed"

        analysis.status = "completed"
        analysis.total_clauses = total
        analysis.high_risk_count = risk_counts["high"]
        analysis.medium_risk_count = risk_counts["medium"]
        analysis.low_risk_count = risk_counts["low"]

        redline_path = None
        if contract.file_path and Path(contract.file_path).suffix.lower() in (".docx", ".doc"):
            out_path = str(Path(settings.storage_dir) / f"{contract_id}_redlined.docx")
            try:
                generate_redlined_docx(contract.file_path, clauses_data, out_path)
                analysis.redline_path = out_path
                redline_path = out_path
            except Exception:
                pass

        db.commit()
        db.refresh(contract)

        clause_outs = [
            ClauseOut.model_validate(c) for c in contract.clauses
        ]

        return AnalysisResult(
            contract_id=contract_id,
            status="completed",
            total_clauses=total,
            high_risk_count=risk_counts["high"],
            medium_risk_count=risk_counts["medium"],
            low_risk_count=risk_counts["low"],
            risk_score=risk_score,
            clauses=clause_outs,
            redline_url=f"/api/contracts/{contract_id}/redline" if redline_path else None,
        )

    except Exception as e:
        analysis.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
