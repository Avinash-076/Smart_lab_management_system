from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditResult

def log_action(
    db: Session,
    result: AuditResult,
    action: str, 
    user_id: int | None = None,
    target_type: str | None = None,
    target_id: int | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        user_id = user_id,
        action = action,
        result = result, 
        target_type = target_type, 
        target_id = target_id,
        ip_address = ip_address,
    )

    db.add(entry)
    db.commit()