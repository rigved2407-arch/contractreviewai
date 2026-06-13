from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Playbook, PlaybookRule
from app.schemas import PlaybookCreate, PlaybookOut, PlaybookRuleCreate, PlaybookRuleOut

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


@router.get("", response_model=list[PlaybookOut])
def list_playbooks(db: Session = Depends(get_db)):
    return db.query(Playbook).order_by(Playbook.created_at.desc()).all()


@router.get("/{playbook_id}", response_model=PlaybookOut)
def get_playbook(playbook_id: str, db: Session = Depends(get_db)):
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return playbook


@router.post("", response_model=PlaybookOut)
def create_playbook(data: PlaybookCreate, db: Session = Depends(get_db)):
    playbook = Playbook(name=data.name, description=data.description)
    db.add(playbook)
    db.flush()

    for rule_data in data.rules:
        rule = PlaybookRule(
            playbook_id=playbook.id,
            clause_type=rule_data.clause_type,
            preferred_position=rule_data.preferred_position,
            risk_if_missing=rule_data.risk_if_missing,
            risk_if_deviates=rule_data.risk_if_deviates,
            is_required=rule_data.is_required,
            priority=rule_data.priority,
        )
        db.add(rule)

    db.commit()
    db.refresh(playbook)
    return playbook


@router.put("/{playbook_id}", response_model=PlaybookOut)
def update_playbook(playbook_id: str, data: PlaybookCreate, db: Session = Depends(get_db)):
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")

    playbook.name = data.name
    playbook.description = data.description

    db.query(PlaybookRule).filter(PlaybookRule.playbook_id == playbook_id).delete()

    for rule_data in data.rules:
        rule = PlaybookRule(
            playbook_id=playbook.id,
            clause_type=rule_data.clause_type,
            preferred_position=rule_data.preferred_position,
            risk_if_missing=rule_data.risk_if_missing,
            risk_if_deviates=rule_data.risk_if_deviates,
            is_required=rule_data.is_required,
            priority=rule_data.priority,
        )
        db.add(rule)

    db.commit()
    db.refresh(playbook)
    return playbook


@router.delete("/{playbook_id}")
def delete_playbook(playbook_id: str, db: Session = Depends(get_db)):
    playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    db.delete(playbook)
    db.commit()
    return {"ok": True}
