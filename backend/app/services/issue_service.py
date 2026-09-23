from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

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
    limit: int = 100,
    offset: int = 0,
) -> list[Issue]:

    limit = min(
        max(limit, 1),
        500,
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

    query = (
        query
        .order_by(Issue.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return list(
        db.scalars(query).all()
    )


def create_issue(
    db: Session,
    issue_data: IssueCreate,
    created_by: int | None = None,
) -> Issue:

    issue = Issue(
        computer_id=issue_data.computer_id,
        title=issue_data.title.strip(),
        description=issue_data.description.strip(),
        severity=issue_data.severity,
        status=IssueStatus.open,
        source=issue_data.source,
        created_by=created_by,
    )

    try:
        db.add(issue)
        db.commit()
        db.refresh(issue)

        return issue

    except IntegrityError:
        db.rollback()
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