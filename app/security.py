
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.database import settings


# ==========================================================
# PASSWORD HASHING
# ==========================================================

pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# ==========================================================
# NORMAL JWT ACCESS TOKEN
# ==========================================================

def create_access_token(
    patient_id: int,
    expires_minutes: int | None = None
) -> str:

    expiry_minutes = (
        expires_minutes
        if expires_minutes is not None
        else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expiry_minutes
    )

    payload = {
        "sub": str(patient_id),
        "exp": expire,
        "type": "access"
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


def verify_access_token(token: str):

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        # Normal API endpoints accept access tokens only.
        if payload.get("type") != "access":
            return None

        patient_id = payload.get("sub")

        if patient_id is None:
            return None

        return int(patient_id)

    except (JWTError, ValueError, TypeError):
        return None


# ==========================================================
# SHORT-LIVED LIVEKIT VOICE SESSION TOKEN
# ==========================================================

def create_voice_session_token(
    patient_id: int,
    room_name: str,
    participant_identity: str
) -> str:

    now = datetime.now(timezone.utc)

    expire = now + timedelta(minutes=10)

    payload = {
        "sub": str(patient_id),
        "type": "voice",
        "room": room_name,
        "participant": participant_identity,
        "iat": now,
        "exp": expire,
        "jti": uuid4().hex
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )


# ==========================================================
# VERIFY VOICE SESSION TOKEN
# ==========================================================

def verify_voice_session_token(
    token: str,
    room_name: str,
    participant_identity: str
):

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        if payload.get("type") != "voice":
            return None

        if payload.get("room") != room_name:
            return None

        if payload.get("participant") != participant_identity:
            return None

        patient_id = payload.get("sub")

        if patient_id is None:
            return None

        return int(patient_id)

    except (JWTError, ValueError, TypeError):
        return None
