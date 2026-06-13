import os
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Contract, Clause
from app.schemas import ContractOut, ContractListItem
from app.config import settings
from app.services.document_parser import parse_document_raw
from app.services.encryption import encrypt_file_bytes

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractListItem])
def list_contracts(db: Session = Depends(get_db)):
    contracts = db.query(Contract).order_by(Contract.created_at.desc()).all()
    return contracts


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return contract


@router.post("/upload", response_model=ContractOut)
async def upload_contract(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    raw_name = (file.filename or "upload")
    safe_name = Path(raw_name).name
    safe_name = re.sub(r'[^\w\-_. ]', '_', safe_name)
    safe_name = safe_name.lstrip('.') or "upload"

    allowed = {".pdf", ".docx", ".doc"}
    ext = Path(safe_name).suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    storage = Path(settings.storage_dir)
    storage.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid.uuid4())
    save_path = storage / f"{file_id}{ext}"
    content = await file.read()

    if len(content) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large")

    text = parse_document_raw(content, ext) or ""

    if settings.encrypt_documents:
        encrypted_content = encrypt_file_bytes(content)
        with open(save_path, "wb") as f:
            f.write(encrypted_content)
    else:
        with open(save_path, "wb") as f:
            f.write(content)

    contract = Contract(
        id=file_id,
        filename=safe_name,
        file_path=str(save_path),
        file_type=ext,
        content_text=text,
        status="parsed",
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


@router.get("/{contract_id}/redline")
def download_redline(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    redline_path = Path(settings.storage_dir) / f"{contract_id}_redlined.docx"
    if not redline_path.exists():
        raise HTTPException(status_code=404, detail="Redlined document not found. Run analysis first.")

    return FileResponse(
        path=str(redline_path),
        filename=f"{Path(contract.filename).stem}_redlined.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.delete("/{contract_id}")
def delete_contract(contract_id: str, db: Session = Depends(get_db)):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.file_path and os.path.exists(contract.file_path):
        os.remove(contract.file_path)

    redline_path = Path(settings.storage_dir) / f"{contract_id}_redlined.docx"
    if redline_path.exists():
        redline_path.unlink()

    db.delete(contract)
    db.commit()
    return {"ok": True}
