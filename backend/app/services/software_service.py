from datetime import datetime, timezone, timedelta
from typing import Any
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.software import Software
from app.schemas.software_schema import (
    SoftwareCategoryItem,
    SoftwareComputerInfo,
    SoftwareFleetItem,
    SoftwareFleetSummaryResponse,
    SoftwareOSDistribution,
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


def get_fleet_software_summary(
    db: Session,
) -> SoftwareFleetSummaryResponse:
    from app.models.computer import Computer

    total_software = int(db.scalar(select(func.count(Software.id))) or 0)
    unique_software = int(db.scalar(select(func.count(func.distinct(Software.name)))) or 0)
    total_computers = int(db.scalar(select(func.count(Computer.id))) or 0)
    computers_with_software = int(db.scalar(select(func.count(func.distinct(Software.computer_id)))) or 0)

    different_publishers = int(
        db.scalar(
            select(func.count(func.distinct(Software.publisher))).where(
                Software.publisher.is_not(None), Software.publisher != ""
            )
        )
        or 0
    )

    # Most common software
    top_row = db.execute(
        select(Software.name, Software.publisher, func.count(Software.id).label("cnt"))
        .group_by(Software.name, Software.publisher)
        .order_by(func.count(Software.id).desc())
        .limit(1)
    ).first()

    most_common_software = None
    if top_row:
        most_common_software = {
            "name": top_row.name,
            "publisher": top_row.publisher or "Unknown",
            "count": int(top_row.cnt),
        }

    # Top 5 software
    top_rows = db.execute(
        select(Software.name, Software.publisher, func.count(Software.id).label("cnt"))
        .group_by(Software.name, Software.publisher)
        .order_by(func.count(Software.id).desc())
        .limit(5)
    ).all()

    top_software = [
        {
            "name": r.name,
            "publisher": r.publisher or "Unknown",
            "count": int(r.cnt),
            "percentage": round(int(r.cnt) / total_computers * 100, 1) if total_computers > 0 else 0,
        }
        for r in top_rows
    ]

    # Software by Operating System
    os_query = (
        select(Computer.os_name, Computer.os_version, func.count(Software.id).label("cnt"))
        .join(Software, Software.computer_id == Computer.id)
        .group_by(Computer.os_name, Computer.os_version)
    )
    os_rows = db.execute(os_query).all()

    win10_cnt = 0
    win11_cnt = 0
    other_cnt = 0
    for r in os_rows:
        os_str = f"{r.os_name or ''} {r.os_version or ''}".lower()
        if "10" in os_str:
            win10_cnt += int(r.cnt)
        elif "11" in os_str:
            win11_cnt += int(r.cnt)
        else:
            other_cnt += int(r.cnt)

    by_os: list[SoftwareOSDistribution] = []
    if total_software > 0:
        by_os = [
            SoftwareOSDistribution(
                os_name="Windows 10",
                count=win10_cnt,
                percentage=round(win10_cnt / total_software * 100, 1),
            ),
            SoftwareOSDistribution(
                os_name="Windows 11",
                count=win11_cnt,
                percentage=round(win11_cnt / total_software * 100, 1),
            ),
            SoftwareOSDistribution(
                os_name="Other",
                count=other_cnt,
                percentage=round(other_cnt / total_software * 100, 1),
            ),
        ]

    # Top publishers
    pub_query = (
        select(Software.publisher, func.count(Software.id).label("cnt"))
        .where(Software.publisher.is_not(None), Software.publisher != "")
        .group_by(Software.publisher)
        .order_by(func.count(Software.id).desc())
    )
    pub_rows = db.execute(pub_query).all()
    top_4_pubs = pub_rows[:4]
    remaining_pubs = pub_rows[4:]
    others_pub_count = sum(int(r.cnt) for r in remaining_pubs)

    top_publishers: list[TopPublisherItem] = []
    for r in top_4_pubs:
        cnt = int(r.cnt)
        pct = round(cnt / total_software * 100) if total_software > 0 else 0
        top_publishers.append(TopPublisherItem(publisher=r.publisher, count=cnt, percentage=pct))
    if others_pub_count > 0:
        pct = round(others_pub_count / total_software * 100) if total_software > 0 else 0
        top_publishers.append(TopPublisherItem(publisher="Others", count=others_pub_count, percentage=pct))

    available_publishers = sorted(
        list(
            db.scalars(
                select(func.distinct(Software.publisher)).where(
                    Software.publisher.is_not(None), Software.publisher != ""
                )
            ).all()
        )
    )

    available_os = sorted(
        list(
            db.scalars(
                select(func.distinct(Computer.os_name)).where(
                    Computer.os_name.is_not(None), Computer.os_name != ""
                )
            ).all()
        )
    )

    return SoftwareFleetSummaryResponse(
        total_software=total_software,
        unique_software=unique_software,
        total_computers=total_computers,
        computers_with_software=computers_with_software,
        different_publishers=different_publishers,
        most_common_software=most_common_software,
        top_software=top_software,
        by_os=by_os,
        top_publishers=top_publishers,
        available_publishers=available_publishers,
        available_os=available_os,
        available_architectures=["64-bit", "32-bit"],
    )


def get_fleet_software_items(
    db: Session,
    search: str | None = None,
    publisher: str | None = None,
    computer_id: int | None = None,
    os_name: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = 10,
    offset: int = 0,
) -> tuple[list[SoftwareFleetItem], int]:
    from app.models.computer import Computer

    total_computers = int(db.scalar(select(func.count(Computer.id))) or 0)

    query = select(Software).join(Computer, Software.computer_id == Computer.id)

    if computer_id is not None:
        query = query.where(Software.computer_id == computer_id)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(Software.name).like(term)
            | func.lower(Software.publisher).like(term)
            | func.lower(Software.version).like(term)
        )

    if publisher and publisher.strip() and publisher.lower() != "all publishers":
        query = query.where(func.lower(Software.publisher) == publisher.strip().lower())

    if os_name and os_name.strip() and os_name.lower() != "all os":
        query = query.where(func.lower(Computer.os_name).like(f"%{os_name.strip().lower()}%"))

    records = list(db.scalars(query.order_by(Software.name.asc(), Software.id.asc())).all())

    # Group by (name.lower(), (publisher or '').lower())
    groups: dict[tuple[str, str], list[Software]] = {}
    for s in records:
        key = (s.name.strip().lower(), (s.publisher or "").strip().lower())
        if key not in groups:
            groups[key] = []
        groups[key].append(s)

    fleet_items: list[SoftwareFleetItem] = []
    for key, items in groups.items():
        primary = items[0]
        versions = [it.version for it in items if it.version]
        primary_version = versions[0] if versions else primary.version

        computers_list: list[SoftwareComputerInfo] = []
        os_set = set()
        for it in items:
            comp = it.computer
            if comp:
                os_str = f"{comp.os_name or ''} {comp.os_version or ''}".strip()
                if os_str:
                    os_set.add(os_str)
                status_str = "offline"
                if hasattr(comp, "status_info") and comp.status_info:
                    status_str = comp.status_info.status or "offline"
                computers_list.append(
                    SoftwareComputerInfo(
                        id=comp.id,
                        hostname=comp.hostname,
                        ip_address=comp.ip_address,
                        os=os_str,
                        status=status_str,
                        install_date=it.install_date,
                    )
                )

        os_display = " / ".join(sorted(os_set)) if os_set else "Windows 10/11"
        if not os_display:
            os_display = "Windows 10/11"

        fleet_items.append(
            SoftwareFleetItem(
                id=primary.id,
                name=primary.name,
                version=primary_version,
                publisher=primary.publisher,
                install_date=primary.install_date,
                install_location=primary.install_location,
                architecture=primary.architecture,
                collected_at=primary.collected_at,
                installed_count=len(computers_list),
                total_computers=total_computers,
                os_display=os_display,
                computers=computers_list,
            )
        )

    reverse = sort_order.lower() == "desc"
    if sort_by == "publisher":
        fleet_items.sort(key=lambda x: (x.publisher or "").lower(), reverse=reverse)
    elif sort_by == "version":
        fleet_items.sort(key=lambda x: (x.version or "").lower(), reverse=reverse)
    elif sort_by == "installed_count":
        fleet_items.sort(key=lambda x: x.installed_count, reverse=reverse)
    else:
        fleet_items.sort(key=lambda x: x.name.lower(), reverse=reverse)

    total_count = len(fleet_items)
    paged_items = fleet_items[offset : offset + limit] if limit else fleet_items
    return paged_items, total_count