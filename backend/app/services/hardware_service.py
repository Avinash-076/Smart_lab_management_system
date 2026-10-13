from __future__ import annotations

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.computer_hardware import ComputerHardware
from app.schemas.computer_hardware_schema import ComputerHardwareUpload


def get_hardware_by_computer_id(
    db: Session,
    computer_id: int,
) -> ComputerHardware | None:
    return db.scalars(
        select(ComputerHardware).where(ComputerHardware.computer_id == computer_id)
    ).first()


def save_or_update_hardware(
    db: Session,
    computer_id: int,
    hardware_data: ComputerHardwareUpload,
) -> ComputerHardware:
    hardware = get_hardware_by_computer_id(db, computer_id)

    data_dict = hardware_data.model_dump(exclude_unset=True)

    if hardware is None:
        hardware = ComputerHardware(
            computer_id=computer_id,
            **data_dict,
        )
        db.add(hardware)
    else:
        for field, value in data_dict.items():
            setattr(hardware, field, value)
        hardware.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(hardware)
    return hardware
