from datetime import datetime, timezone

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.computer import Computer
from app.models.issue import (
    Issue,
    IssueSeverity,
    IssueStatus,
    IssueSource,
)
from app.schemas.issue_schema import (
    IssueCreate,
    IssueUpdate,
)


def get_issue_by_id(
    db: Session,
    issue_id: int,
) -> Issue | None:

    return db.get(
        Issue,
        issue_id,
    )


def get_issues(
    db: Session,
    computer_id: int | None = None,
    status: IssueStatus | None = None,
    severity: IssueSeverity | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Issue]:

    limit = min(
        max(limit, 1),
        500,
    )

    offset = max(
        offset,
        0,
    )

    query = select(Issue)

    if computer_id is not None:
        query = query.where(
            Issue.computer_id == computer_id
        )

    if status is not None:
        query = query.where(
            Issue.status == status
        )

    if severity is not None:
        query = query.where(
            Issue.severity == severity
        )

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.outerjoin(
            Computer, Issue.computer_id == Computer.id
        ).where(
            or_(
                Issue.title.ilike(search_pattern),
                Issue.description.ilike(search_pattern),
                Computer.hostname.ilike(search_pattern),
            )
        )

    query = (
        query
        .order_by(
            Issue.created_at.desc(),
            Issue.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    return list(
        db.scalars(query).all()
    )


def get_issue_stats(
    db: Session,
    computer_id: int | None = None,
) -> dict:

    query = select(
        func.count(Issue.id).label("total"),
        func.count(case((Issue.status == IssueStatus.open, 1))).label("open"),
        func.count(case((Issue.status == IssueStatus.in_progress, 1))).label("in_progress"),
        func.count(case((Issue.status == IssueStatus.resolved, 1))).label("resolved"),
        func.count(case((Issue.severity == IssueSeverity.critical, 1))).label("critical"),
        func.count(case((Issue.severity == IssueSeverity.high, 1))).label("high"),
        func.count(case((Issue.severity == IssueSeverity.medium, 1))).label("medium"),
        func.count(case((Issue.severity == IssueSeverity.low, 1))).label("low"),
    )

    if computer_id is not None:
        query = query.where(Issue.computer_id == computer_id)

    row = db.execute(query).one()

    return {
        "total": row.total or 0,
        "open": row.open or 0,
        "in_progress": row.in_progress or 0,
        "resolved": row.resolved or 0,
        "critical": row.critical or 0,
        "high": row.high or 0,
        "medium": row.medium or 0,
        "low": row.low or 0,
    }



def create_issue(
    db: Session,
    issue_data: IssueCreate,
    created_by: int | None = None,
) -> Issue:

    title_clean = issue_data.title.strip()
    description_clean = issue_data.description.strip()

    if issue_data.idempotency_key:
        existing_key = db.scalars(
            select(Issue).where(
                Issue.idempotency_key == issue_data.idempotency_key
            )
        ).first()
        if existing_key:
            return existing_key

    if issue_data.source == IssueSource.agent:
        existing = db.scalars(
            select(Issue).where(
                Issue.computer_id == issue_data.computer_id,
                Issue.title == title_clean,
                Issue.status == IssueStatus.open,
            )
        ).first()
        if existing:
            existing.description = description_clean
            existing.severity = issue_data.severity
            existing.updated_at = datetime.now(timezone.utc)
            try:
                db.commit()
                db.refresh(existing)
                return existing
            except SQLAlchemyError:
                db.rollback()
                raise

    issue = Issue(
        computer_id=issue_data.computer_id,
        title=title_clean,
        description=description_clean,
        severity=issue_data.severity,
        status=IssueStatus.open,
        source=issue_data.source,
        idempotency_key=issue_data.idempotency_key,
        created_by=created_by,
    )

    try:
        db.add(issue)
        db.commit()
        db.refresh(issue)

        return issue

    except IntegrityError:
        db.rollback()
        if issue_data.idempotency_key:
            existing_key = db.scalars(
                select(Issue).where(
                    Issue.idempotency_key == issue_data.idempotency_key
                )
            ).first()
            if existing_key:
                return existing_key
        if issue_data.source == IssueSource.agent:
            existing = db.scalars(
                select(Issue).where(
                    Issue.computer_id == issue_data.computer_id,
                    Issue.title == title_clean,
                    Issue.status == IssueStatus.open,
                )
            ).first()
            if existing:
                return existing
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def update_issue(
    db: Session,
    issue: Issue,
    issue_data: IssueUpdate,
    user_id: int,
) -> Issue:

    update_data = issue_data.model_dump(
        exclude_unset=True,
    )

    for field, value in update_data.items():

        if isinstance(value, str):
            value = value.strip()

        setattr(
            issue,
            field,
            value,
        )

    if issue.status == IssueStatus.resolved:

        if issue.resolved_at is None:
            issue.resolved_at = datetime.now(
                timezone.utc
            )

        issue.resolved_by = user_id

    else:

        issue.resolved_at = None
        issue.resolved_by = None

        # Resolution information no longer applies
        # after the issue is reopened.
        issue.resolution_notes = None

    issue.updated_at = datetime.now(
        timezone.utc
    )

    try:
        db.commit()
        db.refresh(issue)

        return issue

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def resolve_issue(
    db: Session,
    issue: Issue,
    resolution_notes: str | None,
    user_id: int,
) -> Issue:

    issue.status = IssueStatus.resolved

    issue.resolution_notes = (
        resolution_notes.strip()
        if resolution_notes
        else None
    )

    issue.resolved_by = user_id

    issue.resolved_at = datetime.now(
        timezone.utc
    )

    issue.updated_at = datetime.now(
        timezone.utc
    )

    try:
        db.commit()
        db.refresh(issue)

        return issue

    except SQLAlchemyError:
        db.rollback()
        raise


def delete_issue(
    db: Session,
    issue: Issue,
) -> None:

    try:
        db.delete(issue)
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise