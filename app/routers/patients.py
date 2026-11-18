
from fastapi import APIRouter, Depends

from app.models import Patient
from app.dependencies import get_current_patient


router = APIRouter(
    prefix="/patients",
    tags=["Patients"]
)


@router.get("/me")
def get_my_profile(
    current_patient: Patient = Depends(get_current_patient)
):

    return {
        "patient_id": current_patient.id,
        "full_name": current_patient.full_name,
        "email": current_patient.email,
        "phone": current_patient.phone,
        "created_at": current_patient.created_at
    }
