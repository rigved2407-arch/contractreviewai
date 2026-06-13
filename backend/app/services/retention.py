import os
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models import Contract, Clause, AnalysisRun, AuditLog
from app.config import settings


def delete_expired_data(db: Session) -> dict:
    if not settings.auto_delete_expired:
        return {"deleted": 0, "note": "auto_delete_expired is disabled"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.data_retention_days)
    count = 0

    contracts = db.query(Contract).filter(Contract.created_at < cutoff).all()
    for c in contracts:
        if c.file_path and os.path.exists(c.file_path):
            os.remove(c.file_path)
        db.delete(c)
        count += 1

    old_logs = db.query(AuditLog).filter(AuditLog.created_at < cutoff).all()
    for log in old_logs:
        db.delete(log)
        count += 1

    db.commit()
    return {"deleted": count, "retention_days": settings.data_retention_days}
