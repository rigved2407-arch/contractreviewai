import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Playbook, PlaybookRule
from app.services.indian_contract_templates import INDIAN_CLAUSE_TYPES

RISK_LEVEL_MAP = {
    "Indemnification": {"risk": "high", "statute": "Indian Contract Act 1872, Sections 124-125"},
    "Limitation of Liability": {"risk": "high", "statute": "Indian Contract Act 1872"},
    "Governing Law": {"risk": "high", "statute": "Indian Contract Act 1872; Limitation Act 1963"},
    "Jurisdiction": {"risk": "medium", "statute": "Code of Civil Procedure 1908"},
    "Termination": {"risk": "medium", "statute": "Indian Contract Act 1872"},
    "Confidentiality": {"risk": "medium", "statute": "Indian Contract Act 1872"},
    "Intellectual Property": {"risk": "high", "statute": "Indian Copyright Act 1957; Patents Act 1970; Trade Marks Act 1999"},
    "Payment Terms": {"risk": "medium", "statute": "Indian Contract Act 1872"},
    "Warranty": {"risk": "medium", "statute": "Indian Contract Act 1872; Sale of Goods Act 1930"},
    "Disclaimer": {"risk": "medium", "statute": "Indian Contract Act 1872"},
    "Force Majeure": {"risk": "low", "statute": "Section 56, Indian Contract Act 1872 (Doctrine of Frustration)"},
    "Assignment": {"risk": "low", "statute": "Indian Contract Act 1872"},
    "Non-Compete": {"risk": "high", "statute": "Section 27, Indian Contract Act 1872 — VOID unless sale of goodwill"},
    "Data Protection": {"risk": "high", "statute": "DPDP Act 2023; IT Act 2000 Section 43A"},
    "Arbitration": {"risk": "medium", "statute": "Arbitration and Conciliation Act 1996"},
}


_DEFAULT_PLAYBOOK_SEEDED = False


def seed_default_playbook(db: Session):
    global _DEFAULT_PLAYBOOK_SEEDED
    if _DEFAULT_PLAYBOOK_SEEDED:
        return
    existing = db.query(PlaybookRule).count()
    if existing > 0:
        _DEFAULT_PLAYBOOK_SEEDED = True
        return

    playbook = Playbook(
        name="India Market Standard",
        description="Default playbook with Indian law market standards for all clause types. Auto-generated.",
    )
    db.add(playbook)
    db.flush()

    for clause_type, info in RISK_LEVEL_MAP.items():
        risk = info["risk"]
        statute = info["statute"]
        rule = PlaybookRule(
            playbook_id=playbook.id,
            clause_type=clause_type,
            preferred_position=f"Standard market position for {clause_type} (India)",
            risk_if_missing=f"Missing {clause_type} clause creates uncertainty under Indian law ({statute})",
            risk_if_deviates=f"Non-standard {clause_type} may be unenforceable or increase liability exposure under Indian law ({statute})",
            is_required=risk == "high",
            priority=3 if risk == "high" else (2 if risk == "medium" else 1),
        )
        db.add(rule)

    for key, tmpl in INDIAN_CLAUSE_TYPES.items():
        rule = PlaybookRule(
            playbook_id=playbook.id,
            clause_type=key,
            preferred_position=tmpl["preferred"],
            risk_if_missing=tmpl["if_missing"],
            risk_if_deviates=tmpl["if_deviates"],
            is_required=tmpl["required"],
            priority=3 if tmpl["risk"] == "high" else (2 if tmpl["risk"] == "medium" else 1),
        )
        db.add(rule)

    db.commit()
    _DEFAULT_PLAYBOOK_SEEDED = True
    logging.getLogger("contract-review").info("Default playbook seeded with %d rules", len(RISK_LEVEL_MAP) + len(INDIAN_CLAUSE_TYPES))


def assess_clauses(clauses: list[dict], playbook_id: Optional[str], db: Session) -> list[dict]:
    seed_default_playbook(db)

    if playbook_id:
        playbook = db.query(Playbook).filter(Playbook.id == playbook_id).first()
        if playbook:
            rules = playbook.rules
        else:
            rules = db.query(PlaybookRule).all()
    else:
        rules = db.query(PlaybookRule).all()

    rules_by_type = {r.clause_type: r for r in rules}

    for clause in clauses:
        ctype = clause.get("clause_type", "")
        rule = rules_by_type.get(ctype)
        if rule:
            existing_risk = clause.get("risk_level", "low")
            if existing_risk in ("info", "low"):
                if rule.risk_if_deviates:
                    clause["risk_level"] = "medium"
                    clause["risk_reason"] = rule.risk_if_deviates
            if rule.is_required and not clause.get("clause_text", "").strip():
                clause["risk_level"] = "high"
                clause["risk_reason"] = rule.risk_if_missing or f"Required clause '{ctype}' is missing"
        else:
            if clause.get("risk_level") is None:
                clause["risk_level"] = "info"
                clause["risk_reason"] = None

    return clauses
