import uuid
from datetime import date, datetime
from enum import StrEnum

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Enum, Float, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.core.database import Base


def boundary_column_type() -> Geometry | Text:
    if settings.database_url.startswith("sqlite"):
        return Text()
    return Geometry(geometry_type="POLYGON", srid=4326)


class IrrigationType(StrEnum):
    NONE = "none"
    RAINFED = "rainfed"
    PARTIAL = "partial"
    FULL = "full"


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    crop: Mapped[str] = mapped_column(String(120), nullable=False)
    planting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_harvest_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    irrigation_type: Mapped[IrrigationType] = mapped_column(
        Enum(
            IrrigationType,
            name="irrigation_type",
            values_callable=lambda values: [item.value for item in values],
        ),
        default=IrrigationType.RAINFED,
        nullable=False,
    )
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    boundary = mapped_column(boundary_column_type(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
