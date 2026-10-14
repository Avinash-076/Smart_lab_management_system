from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy import delete, select, or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.usage_session import UsageSession
from app.schemas.usage_schema import (
    UsageSessionCreate,
    UsageUpload,
)

MAX_USAGE_SESSIONS = 2000

APP_NAME_MAP: dict[str, str] = {
    "chrome.exe": "Google Chrome",
    "code.exe": "Visual Studio Code",
    "msedge.exe": "Microsoft Edge",
    "explorer.exe": "File Explorer",
    "winword.exe": "MS Word",
    "notepad.exe": "Notepad",
    "wt.exe": "Windows Terminal",
    "cmd.exe": "Command Prompt",
    "powershell.exe": "PowerShell",
    "powerpnt.exe": "PowerPoint",
    "excel.exe": "Excel",
    "onedrive.exe": "OneDrive",
    "systemsettings.exe": "Settings",
    "brave.exe": "Brave Browser",
    "firefox.exe": "Mozilla Firefox",
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "antigravity ide.exe": "Antigravity IDE",
    "python.exe": "Python",
    "node.exe": "Node.js",
    "taskmgr.exe": "Task Manager",
    "teams.exe": "Microsoft Teams",
}


def resolve_friendly_name(app_raw: str, proc_raw: str | None = None) -> tuple[str, str]:
    """
    Returns (friendly_app_name, process_executable).
    """
    proc = proc_raw or app_raw or "unknown"
    key = proc.casefold()
    if key in APP_NAME_MAP:
        return APP_NAME_MAP[key], proc

    if not app_raw.lower().endswith(".exe"):
        return app_raw, proc

    # Strip .exe and title case
    base = app_raw[:-4].replace("_", " ").replace("-", " ").strip()
    return (base.title() if base else app_raw), proc


def format_duration(seconds: int) -> str:
    """Formats seconds into 'Xh Ym' or 'Ym'."""
    if not seconds or seconds <= 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def create_usage_session(
    db: Session,
    computer_id: int,
    session_data: UsageSessionCreate,
) -> UsageSession:

    duration = session_data.duration_seconds

    if duration == 0 and session_data.ended_at is not None:
        calculated = (session_data.ended_at - session_data.started_at).total_seconds()
        duration = max(0, int(calculated))

    app_name = session_data.application_name.strip()
    proc_name = (session_data.process_name or app_name).strip()

    record = UsageSession(
        computer_id=computer_id,
        application_name=app_name,
        process_name=proc_name,
        user=session_data.user.strip() if session_data.user else None,
        started_at=session_data.started_at,
        ended_at=session_data.ended_at,
        duration_seconds=duration,
    )

    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    except IntegrityError:
        db.rollback()
        existing = db.scalars(
            select(UsageSession).where(
                UsageSession.computer_id == computer_id,
                UsageSession.application_name == app_name,
                UsageSession.started_at == session_data.started_at,
            )
        ).first()
        if existing:
            return existing
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def create_usage_sessions(
    db: Session,
    computer_id: int,
    usage_data: UsageUpload,
) -> list[UsageSession]:

    records: list[UsageSession] = []
    seen_in_batch: dict[tuple[str, datetime], UsageSession] = {}

    try:
        for item in usage_data.sessions[:MAX_USAGE_SESSIONS]:
            application_name = item.application_name.strip()
            if not application_name:
                continue

            duration = item.duration_seconds
            if duration == 0 and item.ended_at is not None:
                calculated = (item.ended_at - item.started_at).total_seconds()
                duration = max(0, int(calculated))

            batch_key = (
                application_name.casefold(),
                item.started_at,
            )

            user_val = item.user.strip() if item.user else None
            proc_val = (item.process_name or application_name).strip()

            if batch_key in seen_in_batch:
                rec = seen_in_batch[batch_key]
                rec.ended_at = item.ended_at
                rec.duration_seconds = duration
                if user_val and not rec.user:
                    rec.user = user_val
                if proc_val and not rec.process_name:
                    rec.process_name = proc_val
                continue

            # Deduplicate if session already exists in database
            existing = db.scalars(
                select(UsageSession).where(
                    UsageSession.computer_id == computer_id,
                    UsageSession.application_name == application_name,
                    UsageSession.started_at == item.started_at,
                )
            ).first()

            if existing:
                existing.ended_at = item.ended_at
                existing.duration_seconds = duration
                if user_val and not existing.user:
                    existing.user = user_val
                if proc_val and not existing.process_name:
                    existing.process_name = proc_val
                seen_in_batch[batch_key] = existing
                records.append(existing)
                continue

            record = UsageSession(
                computer_id=computer_id,
                application_name=application_name,
                process_name=proc_val,
                user=user_val,
                started_at=item.started_at,
                ended_at=item.ended_at,
                duration_seconds=duration,
            )

            db.add(record)
            seen_in_batch[batch_key] = record
            records.append(record)

        db.commit()

        for record in records:
            db.refresh(record)

        return records

    except IntegrityError:
        db.rollback()
        resolved_records: list[UsageSession] = []
        for item in usage_data.sessions[:MAX_USAGE_SESSIONS]:
            app_name = item.application_name.strip()
            if not app_name:
                continue
            rec = db.scalars(
                select(UsageSession).where(
                    UsageSession.computer_id == computer_id,
                    UsageSession.application_name == app_name,
                    UsageSession.started_at == item.started_at,
                )
            ).first()
            if rec and rec not in resolved_records:
                resolved_records.append(rec)
        if resolved_records:
            return resolved_records
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def get_usage_for_computer(
    db: Session,
    computer_id: int,
    limit: int = 100,
    offset: int = 0,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user: str | None = None,
    application: str | None = None,
) -> list[UsageSession]:

    limit = min(max(limit, 1), 500)

    query = select(UsageSession).where(
        UsageSession.computer_id == computer_id
    )

    if start_time is not None:
        query = query.where(UsageSession.started_at >= start_time)

    if end_time is not None:
        query = query.where(UsageSession.started_at <= end_time)

    if user and user.lower() != "all" and user.lower() != "all users":
        query = query.where(UsageSession.user == user)

    if application and application.lower() != "all" and application.lower() != "all applications":
        query = query.where(
            or_(
                UsageSession.application_name.ilike(f"%{application}%"),
                UsageSession.process_name.ilike(f"%{application}%"),
            )
        )

    query = query.order_by(
        UsageSession.started_at.desc(),
        UsageSession.id.desc(),
    ).limit(limit).offset(offset)

    return list(db.scalars(query).all())


def get_usage_count_for_computer(
    db: Session,
    computer_id: int,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user: str | None = None,
    application: str | None = None,
) -> int:
    query = select(UsageSession.id).where(UsageSession.computer_id == computer_id)

    if start_time is not None:
        query = query.where(UsageSession.started_at >= start_time)

    if end_time is not None:
        query = query.where(UsageSession.started_at <= end_time)

    if user and user.lower() != "all" and user.lower() != "all users":
        query = query.where(UsageSession.user == user)

    if application and application.lower() != "all" and application.lower() != "all applications":
        query = query.where(
            or_(
                UsageSession.application_name.ilike(f"%{application}%"),
                UsageSession.process_name.ilike(f"%{application}%"),
            )
        )

    return len(list(db.scalars(query).all()))


def get_usage_summary_for_computer(
    db: Session,
    computer_id: int,
    time_range_preset: str = "today",
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    user: str | None = None,
    application: str | None = None,
) -> dict[str, Any]:
    """
    Computes summary data for History tab:
    - total active time
    - top applications donut chart breakdown
    - hourly/daily trend bar chart intervals
    - available users & applications for filters
    """
    now = datetime.now(timezone.utc)

    # 1. Determine time bounds
    preset = (time_range_preset or "today").lower()
    if start_time is None or end_time is None:
        if preset == "today":
            start_time = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=timezone.utc)
        elif preset == "yesterday":
            y = now - timedelta(days=1)
            start_time = datetime(y.year, y.month, y.day, 0, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(y.year, y.month, y.day, 23, 59, 59, tzinfo=timezone.utc)
        elif preset in ("7d", "7 days", "last 7 days"):
            start_time = now - timedelta(days=7)
            end_time = now
        elif preset in ("30d", "30 days", "last 30 days"):
            start_time = now - timedelta(days=30)
            end_time = now
        elif preset == "all":
            start_time = None
            end_time = None
        else:
            # Fallback to last 24h
            start_time = now - timedelta(hours=24)
            end_time = now

    # 2. Query all sessions in range for this computer to aggregate
    query = select(UsageSession).where(UsageSession.computer_id == computer_id)
    if start_time is not None:
        query = query.where(UsageSession.started_at >= start_time)
    if end_time is not None:
        query = query.where(UsageSession.started_at <= end_time)

    # Filter by user if selected
    if user and user.lower() not in ("all", "all users"):
        query = query.where(UsageSession.user == user)

    # Filter by application if selected
    if application and application.lower() not in ("all", "all applications"):
        query = query.where(
            or_(
                UsageSession.application_name.ilike(f"%{application}%"),
                UsageSession.process_name.ilike(f"%{application}%"),
            )
        )

    query = query.order_by(UsageSession.started_at.asc())
    sessions = list(db.scalars(query).all())

    # Query distinct users & distinct applications across ALL sessions for this computer
    all_users_query = select(UsageSession.user).where(
        UsageSession.computer_id == computer_id,
        UsageSession.user.isnot(None),
    ).distinct()
    available_users = sorted([u for u in db.scalars(all_users_query).all() if u])

    all_apps_query = select(UsageSession.application_name).where(
        UsageSession.computer_id == computer_id
    ).distinct()
    available_apps = sorted([a for a in db.scalars(all_apps_query).all() if a])

    total_active_seconds = sum(s.duration_seconds for s in sessions)
    total_sessions = len(sessions)

    # 3. Top Applications aggregation
    app_durations: dict[str, dict[str, Any]] = {}
    for s in sessions:
        raw_name = s.application_name
        proc_name = s.process_name or raw_name
        friendly, proc = resolve_friendly_name(raw_name, proc_name)

        key = proc.casefold()
        if key not in app_durations:
            app_durations[key] = {
                "application_name": friendly,
                "process_name": proc,
                "duration_seconds": 0,
            }
        app_durations[key]["duration_seconds"] += s.duration_seconds

    # Sort descending by duration
    sorted_apps = sorted(app_durations.values(), key=lambda x: x["duration_seconds"], reverse=True)

    top_applications: list[dict[str, Any]] = []
    if sorted_apps and total_active_seconds > 0:
        # Take top 4, group remaining into "Others"
        top_slice = sorted_apps[:4]
        other_slice = sorted_apps[4:]

        for item in top_slice:
            pct = round((item["duration_seconds"] / total_active_seconds) * 100, 1)
            top_applications.append({
                "application_name": item["application_name"],
                "process_name": item["process_name"],
                "duration_seconds": item["duration_seconds"],
                "formatted_duration": format_duration(item["duration_seconds"]),
                "percentage": pct,
            })

        if other_slice:
            other_secs = sum(x["duration_seconds"] for x in other_slice)
            other_pct = round((other_secs / total_active_seconds) * 100, 1)
            top_applications.append({
                "application_name": "Others",
                "process_name": "Others",
                "duration_seconds": other_secs,
                "formatted_duration": format_duration(other_secs),
                "percentage": other_pct,
            })

    # 4. Trend Bar Chart Intervals
    trend_intervals: list[dict[str, Any]] = []
    norm_start = _ensure_utc(start_time)
    norm_end = _ensure_utc(end_time)

    if preset in ("today", "yesterday") and norm_start and norm_end:
        # 1-hour intervals e.g. 08:00 to 17:00 (or full day 00:00 to 23:00)
        # To match reference design nicely: 08:00 to 17:00 or current hour
        day_start = norm_start.replace(hour=8, minute=0, second=0)
        for h in range(8, 17):
            b_start = _ensure_utc(day_start.replace(hour=h))
            b_end = _ensure_utc(b_start + timedelta(hours=1))

            # Sum overlap of sessions in this bucket
            bucket_secs = 0
            for s in sessions:
                s_start = _ensure_utc(s.started_at)
                s_end = _ensure_utc(s.ended_at or (s_start + timedelta(seconds=s.duration_seconds)))
                if s_start and s_end and b_start and b_end:
                    overlap_start = max(b_start, s_start)
                    overlap_end = min(b_end, s_end)
                    if overlap_end > overlap_start:
                        bucket_secs += int((overlap_end - overlap_start).total_seconds())

            mins = round(bucket_secs / 60.0, 1)
            trend_intervals.append({
                "label": f"{h:02d}:00",
                "start_time": b_start,
                "end_time": b_end,
                "duration_minutes": mins,
            })
    elif preset in ("7d", "7 days", "last 7 days") and norm_start and norm_end:
        # Daily intervals (7 days)
        for d in range(7):
            b_start = _ensure_utc((norm_start + timedelta(days=d)).replace(hour=0, minute=0, second=0))
            b_end = _ensure_utc(b_start + timedelta(days=1))
            bucket_secs = 0
            for s in sessions:
                s_start = _ensure_utc(s.started_at)
                s_end = _ensure_utc(s.ended_at or (s_start + timedelta(seconds=s.duration_seconds)))
                if s_start and s_end and b_start and b_end:
                    overlap_start = max(b_start, s_start)
                    overlap_end = min(b_end, s_end)
                    if overlap_end > overlap_start:
                        bucket_secs += int((overlap_end - overlap_start).total_seconds())
            mins = round(bucket_secs / 60.0, 1)
            trend_intervals.append({
                "label": b_start.strftime("%a"),
                "start_time": b_start,
                "end_time": b_end,
                "duration_minutes": mins,
            })
    elif norm_start and norm_end:
        # Custom or 30d range: divide into 8 responsive buckets
        total_span = (norm_end - norm_start).total_seconds()
        bucket_count = 8
        step = total_span / bucket_count
        for i in range(bucket_count):
            b_start = _ensure_utc(norm_start + timedelta(seconds=i * step))
            b_end = _ensure_utc(norm_start + timedelta(seconds=(i + 1) * step))
            bucket_secs = 0
            for s in sessions:
                s_start = _ensure_utc(s.started_at)
                s_end = _ensure_utc(s.ended_at or (s_start + timedelta(seconds=s.duration_seconds)))
                if s_start and s_end and b_start and b_end:
                    overlap_start = max(b_start, s_start)
                    overlap_end = min(b_end, s_end)
                    if overlap_end > overlap_start:
                        bucket_secs += int((overlap_end - overlap_start).total_seconds())
            mins = round(bucket_secs / 60.0, 1)
            trend_intervals.append({
                "label": b_start.strftime("%m/%d %H:%M") if total_span > 86400 else b_start.strftime("%H:%M"),
                "start_time": b_start,
                "end_time": b_end,
                "duration_minutes": mins,
            })

    return {
        "computer_id": computer_id,
        "time_range": preset,
        "start_time": start_time,
        "end_time": end_time,
        "total_active_seconds": total_active_seconds,
        "formatted_total_active": format_duration(total_active_seconds),
        "total_sessions": total_sessions,
        "top_applications": top_applications,
        "trend_intervals": trend_intervals,
        "available_users": available_users,
        "available_applications": available_apps,
    }


def delete_usage_for_computer(
    db: Session,
    computer_id: int,
) -> None:

    try:
        db.execute(
            delete(UsageSession).where(
                UsageSession.computer_id == computer_id
            )
        )
        db.commit()

    except SQLAlchemyError:
        db.rollback()
        raise