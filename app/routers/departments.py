
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Department

router = APIRouter(
    prefix="/departments",
    tags=["Departments"]
)


@router.get("/")
def get_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()

    return departments
