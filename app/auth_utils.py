
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app.database import settings


def create_access_token(patient_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(patient_id),
        "exp": expire
    }

    token = jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return token


def verify_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        patient_id = payload.get("sub")

        if patient_id is None:
            return None

        return int(patient_id)

    except (JWTError, ValueError):
        return None
