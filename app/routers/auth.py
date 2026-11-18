
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import Patient
from app.schemas.auth import PatientRegister, PatientLogin, TokenResponse
from app.security import (
    hash_password,
    verify_password,
    create_access_token
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# PATIENT REGISTRATION
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
def register_patient(
    patient_data: PatientRegister,
    db: Session = Depends(get_db)
):

    # Check whether email already exists
    existing_email = db.query(Patient).filter(
        Patient.email == patient_data.email
    ).first()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )

    # Check whether phone number already exists
    existing_phone = db.query(Patient).filter(
        Patient.phone == patient_data.phone
    ).first()

    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phone number already registered"
        )

    # Hash password
    hashed_password = hash_password(
        patient_data.password
    )

    # Create patient
    new_patient = Patient(
        full_name=patient_data.full_name,
        email=patient_data.email,
        phone=patient_data.phone,
        password_hash=hashed_password
    )

    try:
        db.add(new_patient)
        db.commit()
        db.refresh(new_patient)

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or phone number already registered"
        )

    return {
        "message": "Patient registered successfully",
        "patient_id": new_patient.id,
        "full_name": new_patient.full_name,
        "email": new_patient.email
    }


# PATIENT LOGIN
@router.post(
    "/login",
    response_model=TokenResponse
)
def login_patient(
    login_data: PatientLogin,
    db: Session = Depends(get_db)
):

    # Find patient using email
    patient = db.query(Patient).filter(
        Patient.email == login_data.email
    ).first()

    # Verify email and password
    if not patient or not verify_password(
        login_data.password,
        patient.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # Generate JWT access token
    access_token = create_access_token(
        patient.id
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
