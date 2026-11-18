
from sqlalchemy import (
    Column,
    Integer,
    Time,
    Boolean,
    ForeignKey
)

from sqlalchemy.orm import relationship

from app.database import Base


class DoctorSchedule(Base):
    __tablename__ = "doctor_schedules"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False
    )

    # Monday = 0, Sunday = 6
    day_of_week = Column(Integer, nullable=False)

    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    slot_duration_minutes = Column(
        Integer,
        default=30,
        nullable=False
    )

    is_active = Column(Boolean, default=True, nullable=False)

    doctor = relationship("Doctor", back_populates="schedules")
