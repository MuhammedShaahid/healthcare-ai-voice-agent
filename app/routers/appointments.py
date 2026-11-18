
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from app.schemas.appointment import AppointmentReschedule
from app.database import get_db
from app.dependencies import get_current_patient

from app.models import (
    Patient,
    Doctor,
    DoctorSchedule,
    Appointment
)

from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentResponse
)


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)


# ==========================================
# BOOK APPOINTMENT
# ==========================================

@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED
)
def book_appointment(
    appointment_data: AppointmentCreate,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):

    # Check doctor
    doctor = db.query(Doctor).filter(
        Doctor.id == appointment_data.doctor_id,
        Doctor.is_active.is_(True)
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found or inactive"
        )

    # Validate appointment date
    appointment_date = appointment_data.appointment_date
    today = datetime.now().date()

    if appointment_date < today:
        raise HTTPException(
            status_code=400,
            detail="Cannot book an appointment for a past date"
        )

    # Get doctor's schedule
    day_of_week = appointment_date.weekday()

    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor.id,
        DoctorSchedule.day_of_week == day_of_week,
        DoctorSchedule.is_active.is_(True)
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=400,
            detail="Doctor is not available on this day"
        )

    # Validate appointment time
    start_time = appointment_data.start_time

    if start_time.tzinfo is not None:
        raise HTTPException(
            status_code=400,
            detail="Use local time without timezone information"
        )

    if start_time < schedule.start_time or start_time >= schedule.end_time:
        raise HTTPException(
            status_code=400,
            detail="Selected time is outside doctor's working hours"
        )

    # Validate slot interval
    slot_minutes = schedule.slot_duration_minutes

    schedule_start = datetime.combine(
        appointment_date,
        schedule.start_time
    )

    requested_start = datetime.combine(
        appointment_date,
        start_time
    )

    elapsed_minutes = int(
        (requested_start - schedule_start).total_seconds() / 60
    )

    if elapsed_minutes % slot_minutes != 0:
        raise HTTPException(
            status_code=400,
            detail="Selected time is not a valid appointment slot"
        )

    # Calculate appointment end time
    requested_end = requested_start + timedelta(
        minutes=slot_minutes
    )

    end_time = requested_end.time()

    if end_time > schedule.end_time:
        raise HTTPException(
            status_code=400,
            detail="Appointment extends beyond working hours"
        )

    # Prevent past time booking
    if appointment_date == today and requested_start <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Cannot book a past time slot"
        )

    # Check overlapping appointments
    existing_appointment = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == "BOOKED",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time
    ).first()

    if existing_appointment:
        raise HTTPException(
            status_code=409,
            detail="This appointment slot is already booked"
        )

    # Create appointment
    new_appointment = Appointment(
        patient_id=current_patient.id,
        doctor_id=doctor.id,
        appointment_date=appointment_date,
        start_time=start_time,
        end_time=end_time,
        status="BOOKED",
        reason=appointment_data.reason
    )

    try:
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="This appointment slot has already been booked"
        )

    return new_appointment


# ==========================================
# GET MY APPOINTMENTS
# ==========================================

@router.get("/my-appointments")
def get_my_appointments(
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):

    appointments = (
        db.query(Appointment)
        .options(
            joinedload(Appointment.doctor)
            .joinedload(Doctor.department)
        )
        .filter(
            Appointment.patient_id == current_patient.id
        )
        .order_by(
            Appointment.appointment_date.asc(),
            Appointment.start_time.asc()
        )
        .all()
    )

    result = []

    for appointment in appointments:

        doctor = appointment.doctor

        result.append({
            "appointment_id": appointment.id,
            "doctor_id": appointment.doctor_id,
            "doctor_name": doctor.name if doctor else None,
            "department": (
                doctor.department.name
                if doctor and doctor.department
                else None
            ),
            "appointment_date": appointment.appointment_date,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "status": appointment.status,
            "reason": appointment.reason
        })

    return {
        "patient_id": current_patient.id,
        "patient_name": current_patient.full_name,
        "total_appointments": len(result),
        "appointments": result
    }

# ==========================================
# CANCEL APPOINTMENT
# ==========================================

@router.patch("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):

    # Find appointment belonging to logged-in patient
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == current_patient.id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Check appointment status
    if appointment.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled"
        )

    if appointment.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed appointments cannot be cancelled"
        )

    # Prevent cancellation after appointment has started
    appointment_start = datetime.combine(
        appointment.appointment_date,
        appointment.start_time
    )

    if appointment_start <= datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Past or ongoing appointments cannot be cancelled"
        )

    # Update appointment status
    appointment.status = "CANCELLED"

    db.commit()
    db.refresh(appointment)

    return {
        "message": "Appointment cancelled successfully",
        "appointment_id": appointment.id,
        "status": appointment.status
    }

# ==========================================
# RESCHEDULE APPOINTMENT
# ==========================================

@router.patch("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: int,
    reschedule_data: AppointmentReschedule,
    current_patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):

    # 1. Find appointment belonging to logged-in patient
    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == current_patient.id
    ).first()

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found"
        )

    # 2. Check appointment status
    if appointment.status != "BOOKED":
        raise HTTPException(
            status_code=400,
            detail="Only booked appointments can be rescheduled"
        )

    # 3. Validate new appointment date
    new_date = reschedule_data.appointment_date
    new_start_time = reschedule_data.start_time

    today = datetime.now().date()

    if new_date < today:
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule to a past date"
        )

    # 4. Get doctor's schedule for new date
    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == appointment.doctor_id,
        DoctorSchedule.day_of_week == new_date.weekday(),
        DoctorSchedule.is_active.is_(True)
    ).first()

    if not schedule:
        raise HTTPException(
            status_code=400,
            detail="Doctor is not available on this day"
        )

    # 5. Validate new time against schedule
    if (
        new_start_time < schedule.start_time
        or new_start_time >= schedule.end_time
    ):
        raise HTTPException(
            status_code=400,
            detail="Selected time is outside doctor's working hours"
        )

    slot_minutes = schedule.slot_duration_minutes

    schedule_start = datetime.combine(
        new_date,
        schedule.start_time
    )

    requested_start = datetime.combine(
        new_date,
        new_start_time
    )

    elapsed_minutes = int(
        (requested_start - schedule_start).total_seconds() / 60
    )

    if elapsed_minutes % slot_minutes != 0:
        raise HTTPException(
            status_code=400,
            detail="Selected time is not a valid appointment slot"
        )

    # 6. Calculate new end time
    requested_end = requested_start + timedelta(
        minutes=slot_minutes
    )

    new_end_time = requested_end.time()

    if new_end_time > schedule.end_time:
        raise HTTPException(
            status_code=400,
            detail="Appointment extends beyond working hours"
        )

    # 7. Prevent rescheduling to a past time
    if new_date == today and requested_start <= datetime.now():
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule to a past time"
        )

    # 8. Check overlapping appointments
    existing_appointment = db.query(Appointment).filter(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.appointment_date == new_date,
        Appointment.status == "BOOKED",
        Appointment.id != appointment.id,
        Appointment.start_time < new_end_time,
        Appointment.end_time > new_start_time
    ).first()

    if existing_appointment:
        raise HTTPException(
            status_code=409,
            detail="Selected appointment slot is already booked"
        )

    # 9. Update existing appointment
    appointment.appointment_date = new_date
    appointment.start_time = new_start_time
    appointment.end_time = new_end_time

    try:
        db.commit()
        db.refresh(appointment)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Selected appointment slot has already been booked"
        )

    return {
        "message": "Appointment rescheduled successfully",
        "appointment_id": appointment.id,
        "doctor_id": appointment.doctor_id,
        "appointment_date": appointment.appointment_date,
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "status": appointment.status
    }
