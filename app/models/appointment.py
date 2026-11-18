
from sqlalchemy import (
    Column,
    Integer,
    Date,
    Time,
    String,
    ForeignKey,
    DateTime,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey("patients.id"),
        nullable=False
    )

    doctor_id = Column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=False
    )

    appointment_date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    status = Column(
        String(20),
        default="BOOKED",
        nullable=False
    )

    reason = Column(String(500), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    patient = relationship("Patient")
    doctor = relationship("Doctor")

    __table_args__ = (
        Index(
            "uq_doctor_appointment_slot",
            "doctor_id",
            "appointment_date",
            "start_time",
            unique=True,
            postgresql_where=text("status = 'BOOKED'")
        ),
        CheckConstraint(
            "end_time > start_time",
            name="ck_appointment_valid_time"
        ),
        CheckConstraint(
            "status IN ('BOOKED', 'CANCELLED', 'COMPLETED')",
            name="ck_appointment_status"
        ),
    )
