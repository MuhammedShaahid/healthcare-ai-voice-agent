
from datetime import date, time
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, field_validator


class AppointmentCreate(BaseModel):
    doctor_id: int = Field(gt=0)
    appointment_date: date
    start_time: time
    reason: Optional[str] = Field(
        default=None,
        max_length=500
    )

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError(
                "Use local time without timezone information, "
                "for example 10:00:00"
            )
        return value


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    start_time: time
    end_time: time
    status: str
    reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AppointmentReschedule(BaseModel):
    appointment_date: date
    start_time: time

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: time) -> time:
        if value.tzinfo is not None:
            raise ValueError(
                "Use local time without timezone information"
            )
        return value

