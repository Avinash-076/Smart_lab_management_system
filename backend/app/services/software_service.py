from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.software import Software
from app.schemas.software_schema import (
    SoftwareCategoryItem,
    SoftwareSummaryResponse,
    SoftwareUpload,
    TopPublisherItem,
)


MAX_SOFTWARE_ITEMS = 2000


def classify_software(name: str, publisher: str | None = None) -> str:
    """
    Classify software into predefined categories based on name and publisher keywords.
    Categories match reference design:
    - Web Browsers
    - Development
    - Multimedia
    - Office & Productivity
    - Security
    - System Utilities
    - Others
    """
    n = (name or "").lower()
    p = (publisher or "").lower()

    # 1. Web Browsers
    if any(k in n for k in ["chrome", "firefox", "edge", "browser", "brave", "opera", "vivaldi", "chromium", "tor"]):
        return "Web Browsers"

    # 2. Development
    if any(k in n for k in [
        "visual studio", "vs code", "python", "git", "node.js", "java", "jdk", "jre",
        "docker", "intellij", "pycharm", "postman", "eclipse", "android studio",
        "rust", "golang", "compiler", "sdk", "sublime text", "cmake", "llvm", "mingw"
    ]):
        return "Development"

    # 3. Multimedia
    if any(k in n for k in [
        "vlc", "spotify", "media player", "photoshop", "premiere", "audacity", "gimp",
        "obs studio", "blender", "handbrake", "itunes", "paint.net", "audio", "video",
        "codec", "davinci", "lightroom", "recorder"
    ]):
        return "Multimedia"

    # 4. Office & Productivity
    if any(k in n for k in [
        "office", "word", "excel", "powerpoint", "outlook", "onenote", "libreoffice",
        "acrobat", "foxit", "pdf", "slack", "teams", "zoom", "notion", "evernote",
        "trello", "skype", "openoffice"
    ]):
        return "Office & Productivity"

    # 5. Security
    if any(k in n for k in [
        "antivirus", "defender", "malware", "kaspersky", "bitdefender", "avast",
        "norton", "mcafee", "firewall", "vpn", "wireguard", "1password", "bitwarden",
        "keepass", "security", "endpoint"
    ]):
        return "Security"

    # 6. System Utilities
    if any(k in n for k in [
        "7-zip", "winrar", "notepad++", "ccleaner", "terminal", "driver", "intel",
        "realtek", "amd", "nvidia", "directx", "redistributable", "rufus", "filezilla",
        "anydesk", "teamviewer", "utility", "tools", "framework", "runtime"
    ]) or any(k in p for k in ["intel", "realtek", "nvidia", "amd"]):
        return "System Utilities"

    return "Others"


def replace_software_inventory(
    db: Session,
    computer_id: int,
    software_data: SoftwareUpload,
) -> tuple[list[Software], list[str]]:
    items = software_data.software[:MAX_SOFTWARE_ITEMS]

    try:
        # Check existing software names for differential alerting
        existing_names = set(
            db.scalars(
                select(Software.name).where(Software.computer_id == computer_id)
            ).all()
        )

        db.execute(
            delete(Software).where(
                Software.computer_id == computer_id
            )
        )

        software_records = []
        seen: set[tuple[str, str]] = set()

        for item in items:
            name = item.name.strip()
            if not name:
                continue

            version = item.version.strip() if item.version else None
            publisher = item.publisher.strip() if item.publisher else None
            install_date = item.install_date.strip() if item.install_date else None
            install_location = item.install_location.strip() if item.install_location else None
            architecture = item.architecture.strip() if item.architecture else None

            identity = (
                name.casefold(),
                (version or "").casefold(),
            )

            if identity in seen:
                continue

            seen.add(identity)

            record = Software(
                computer_id=computer_id,
                name=name,
                version=version,
                publisher=publisher,
                install_date=install_date,
                install_location=install_location,
                architecture=architecture,
            )

            db.add(record)
            software_records.append(record)

        db.commit()

        for record in software_records:
            db.refresh(record)

        # Detect newly installed software only if there was a prior baseline inventory
        new_names = []
        if existing_names:
            current_names = {r.name for r in software_records}
            new_names = sorted(list(current_names - existing_names))

        return software_records, new_names

    except IntegrityError:
        db.rollback()
        raise

    except SQLAlchemyError:
        db.rollback()
        raise


def _build_software_filter_conditions(
    computer_id: int,
    search: str | None = None,
    publisher: str | None = None,
    architecture: str | None = None,
    date_range: str | None = None,
) -> list[Any]:
    conditions: list[Any] = [Software.computer_id == computer_id]

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        conditions.append(
            func.lower(Software.name).like(term) |
            func.lower(Software.publisher).like(term)
        )

    if publisher and publisher.strip() and publisher.lower() != "all":
        conditions.append(func.lower(Software.publisher) == publisher.strip().lower())

    if architecture and architecture.strip() and architecture.lower() != "all":
        conditions.append(func.lower(Software.architecture) == architecture.strip().lower())

    if date_range and date_range.lower() != "all":
        now = datetime.now(timezone.utc)
        cutoff = None
        if date_range == "7d":
            cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        elif date_range == "30d":
            cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
        elif date_range == "90d":
            cutoff = (now - timedelta(days=90)).strftime("%Y-%m-%d")
        elif date_range == "365d":
            cutoff = (now - timedelta(days=365)).strftime("%Y-%m-%d")

        if cutoff:
            conditions.append(Software.install_date >= cutoff)

    return conditions


def get_software_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    publisher: str | None = None,
    architecture: str | None = None,
    date_range: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int | None = None,
    offset: int = 0,
) -> list[Software]:
    conditions = _build_software_filter_conditions(
        computer_id=computer_id,
        search=search,
        publisher=publisher,
        architecture=architecture,
        date_range=date_range,
    )

    stmt = select(Software).where(*conditions)

    # Sorting
    sort_col = Software.name
    if sort_by == "publisher":
        sort_col = Software.publisher
    elif sort_by == "version":
        sort_col = Software.version
    elif sort_by == "install_date":
        sort_col = Software.install_date
    elif sort_by == "architecture":
        sort_col = Software.architecture

    if sort_order.lower() == "desc":
        stmt = stmt.order_by(sort_col.desc(), Software.name.asc())
    else:
        stmt = stmt.order_by(sort_col.asc(), Software.name.asc())

    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)

    return list(db.scalars(stmt).all())


def get_software_count_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    publisher: str | None = None,
    architecture: str | None = None,
    date_range: str | None = None,
) -> int:
    conditions = _build_software_filter_conditions(
        computer_id=computer_id,
        search=search,
        publisher=publisher,
        architecture=architecture,
        date_range=date_range,
    )
    stmt = select(func.count(Software.id)).where(*conditions)
    return db.scalar(stmt) or 0


def get_software_summary_for_computer(
    db: Session,
    computer_id: int,
    search: str | None = None,
    publisher: str | None = None,
    architecture: str | None = None,
    date_range: str | None = None,
) -> SoftwareSummaryResponse:
    # 1. Fetch filtered items for analytics
    items = get_software_for_computer(
        db=db,
        computer_id=computer_id,
        search=search,
        publisher=publisher,
        architecture=architecture,
        date_range=date_range,
    )

    total_installed = len(items)

    # 2. Latest scan timestamp from database
    latest_scan_dt = db.scalar(
        select(func.max(Software.collected_at)).where(Software.computer_id == computer_id)
    )

    formatted_last_scan = "—"
    if latest_scan_dt:
        now = datetime.now(timezone.utc)
        # Check if today
        if latest_scan_dt.date() == now.date():
            formatted_last_scan = f"Today, {latest_scan_dt.strftime('%I:%M %p')}"
        else:
            formatted_last_scan = latest_scan_dt.strftime("%b %d, %I:%M %p")

    # 3. Recently installed within last 7 days
    seven_days_ago_str = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    recently_installed_7d = sum(
        1 for item in items
        if item.install_date and item.install_date >= seven_days_ago_str and item.install_date != "Unknown"
    )

    # 4. Software categories aggregation
    category_counts: dict[str, int] = {}
    for item in items:
        cat = classify_software(item.name, item.publisher)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    # Standard desired order matching reference
    desired_order = [
        "System Utilities",
        "Web Browsers",
        "Development",
        "Multimedia",
        "Office & Productivity",
        "Security",
        "Others",
    ]

    categories_list: list[SoftwareCategoryItem] = []
    for cat in desired_order:
        cnt = category_counts.get(cat, 0)
        pct = round((cnt / total_installed * 100)) if total_installed > 0 else 0
        categories_list.append(
            SoftwareCategoryItem(category=cat, count=cnt, percentage=pct)
        )

    # 5. Top Publishers aggregation
    publisher_counts: dict[str, int] = {}
    for item in items:
        pub = (item.publisher or "").strip() or "Unknown publisher"
        publisher_counts[pub] = publisher_counts.get(pub, 0) + 1

    sorted_pubs = sorted(publisher_counts.items(), key=lambda x: x[1], reverse=True)
    top_5 = sorted_pubs[:5]
    remaining = sorted_pubs[5:]
    others_count = sum(c for _, c in remaining)

    top_publishers_list: list[TopPublisherItem] = []
    for pub_name, cnt in top_5:
        pct = round((cnt / total_installed * 100)) if total_installed > 0 else 0
        top_publishers_list.append(
            TopPublisherItem(publisher=pub_name, count=cnt, percentage=pct)
        )

    if others_count > 0:
        others_pct = round((others_count / total_installed * 100)) if total_installed > 0 else 0
        top_publishers_list.append(
            TopPublisherItem(publisher="Others", count=others_count, percentage=others_pct)
        )

    # 6. Available filter options from all records of this computer
    all_raw_pubs = db.scalars(
        select(Software.publisher)
        .where(Software.computer_id == computer_id, Software.publisher.is_not(None))
        .distinct()
    ).all()
    available_publishers = sorted({p.strip() for p in all_raw_pubs if p and p.strip()})

    all_raw_archs = db.scalars(
        select(Software.architecture)
        .where(Software.computer_id == computer_id, Software.architecture.is_not(None))
        .distinct()
    ).all()
    available_architectures = sorted({a.strip() for a in all_raw_archs if a and a.strip()})
    if not available_architectures:
        available_architectures = ["64-bit", "32-bit"]

    return SoftwareSummaryResponse(
        computer_id=computer_id,
        total_installed=total_installed,
        recently_installed_7d=recently_installed_7d,
        potentially_outdated=None,  # Transparently unavailable without reliable external CVE/version catalog
        last_scan=latest_scan_dt,
        formatted_last_scan=formatted_last_scan,
        categories=categories_list,
        top_publishers=top_publishers_list,
        available_publishers=available_publishers,
        available_architectures=available_architectures,
    )


def delete_software_for_computer(
    db: Session,
    computer_id: int,
) -> None:
    try:
        db.execute(
            delete(Software).where(
                Software.computer_id == computer_id
            )
        )
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise