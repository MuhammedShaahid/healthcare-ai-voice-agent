
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    departments,
    doctors,
    auth,
    patients,
    appointments,
    voice
)


app = FastAPI(
    title="QuantumLoop Hospital API",
    description="Hospital doctor and appointment management system",
    version="1.0.0"
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register API routers
app.include_router(departments.router)
app.include_router(doctors.router)
app.include_router(auth.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(voice.router)


@app.get("/", tags=["Home"])
def root():
    return {
        "message": "Welcome to QuantumLoop Hospital API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "application": "QuantumLoop Hospital API"
    }
