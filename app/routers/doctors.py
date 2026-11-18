
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models import Doctor, DoctorSchedule, Appointment

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


@router.get("/")
def get_doctors(
    department_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Doctor).options(
        joinedload(Doctor.department)
    ).filter(Doctor.is_active == True)

    if department_id is not None:
        query = query.filter(
            Doctor.department_id == department_id
        )

    doctors = query.order_by(Doctor.id).all()

    return [
        {
            "id": doctor.id,
            "name": doctor.name,
            "department": doctor.department.name,
            "department_id": doctor.department_id,
            "qualification": doctor.qualification,
            "consultation_fee": float(doctor.consultation_fee),
            "is_active": doctor.is_active
        }
        for doctor in doctors
    ]


@router.get("/{doctor_id}")
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    doctor = (
        db.query(Doctor)
        .options(joinedload(Doctor.department))
        .filter(
            Doctor.id == doctor_id,
            Doctor.is_active == True
        )
        .first()
    )

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    return {
        "id": doctor.id,
        "name": doctor.name,
        "department": doctor.department.name,
        "department_id": doctor.department_id,
        "qualification": doctor.qualification,
        "consultation_fee": float(doctor.consultation_fee),
        "is_active": doctor.is_active
    }

@router.get("/{doctor_id}/availability")
def get_doctor_availability(
    doctor_id: int,
    appointment_date: date,
    db: Session = Depends(get_db)
):
    # 1. Check whether the doctor exists
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id,
        Doctor.is_active == True
    ).first()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # 2. Find the doctor's schedule for the requested weekday
    day_of_week = appointment_date.weekday()

    schedule = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.day_of_week == day_of_week,
        DoctorSchedule.is_active == True
    ).first()

    if schedule is None:
        return {
            "doctor_id": doctor_id,
            "doctor_name": doctor.name,
            "date": appointment_date,
            "available_slots": []
        }

    # 3. Retrieve existing booked appointments
    booked_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == appointment_date,
        Appointment.status == "BOOKED"
    ).all()

    booked_slots = {
        appointment.start_time
        for appointment in booked_appointments
    }

    # 4. Generate available appointment slots
    current_slot = datetime.combine(
        appointment_date,
        schedule.start_time
    )

    closing_time = datetime.combine(
        appointment_date,
        schedule.end_time
    )

    slot_duration = timedelta(
        minutes=schedule.slot_duration_minutes
    )

    available_slots = []

    while current_slot + slot_duration <= closing_time:
        slot_start = current_slot.time()
        slot_end = (current_slot + slot_duration).time()

        if slot_start not in booked_slots:
            available_slots.append({
                "start_time": slot_start,
                "end_time": slot_end
            })

        current_slot += slot_duration

    # 5. Return available slots
    return {
        "doctor_id": doctor_id,
        "doctor_name": doctor.name,
        "date": appointment_date,
        "available_slots": available_slots
    }

