
import json
import logging
from datetime import timedelta
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from pydantic import BaseModel
from livekit import api

from app.database import settings
from app.dependencies import get_current_patient
from app.models import Patient
from app.security import (
    create_voice_session_token,
    verify_voice_session_token,
    create_access_token
)


logger = logging.getLogger("voice-session")

router = APIRouter(
    prefix="/voice",
    tags=["Voice Assistant"]
)


# ==========================================================
# REQUEST SCHEMA
# ==========================================================

class VoiceVerificationRequest(BaseModel):
    voice_token: str
    room_name: str
    participant_identity: str


# ==========================================================
# CREATE LIVEKIT VOICE SESSION
# ==========================================================

@router.post("/session")
async def create_voice_session(
    current_patient: Patient = Depends(get_current_patient)
):

    if not all([
        settings.LIVEKIT_URL,
        settings.LIVEKIT_API_KEY,
        settings.LIVEKIT_API_SECRET,
        settings.LIVEKIT_AGENT_DEPLOYMENT
    ]):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LiveKit configuration is incomplete"
        )

    room_name = f"patient-room-{uuid4().hex}"

    participant_identity = f"patient-{uuid4().hex}"

    # Create a short-lived credential bound to this room
    # and participant identity.
    voice_token = create_voice_session_token(
        patient_id=current_patient.id,
        room_name=room_name,
        participant_identity=participant_identity
    )

    try:

        participant_token = (
            api.AccessToken(
                settings.LIVEKIT_API_KEY,
                settings.LIVEKIT_API_SECRET
            )
            .with_identity(participant_identity)
            .with_name("Hospital Patient")
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True
                )
            )
            .with_ttl(timedelta(minutes=10))
            .to_jwt()
        )

        async with api.LiveKitAPI(
            url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET
        ) as livekit_api:

            dispatch = await livekit_api.agent_dispatch.create_dispatch(
                api.CreateAgentDispatchRequest(
                    agent_name="healthcare-assistant",
                    room=room_name,
                    metadata=json.dumps({
                        "voice_token": voice_token,
                        "room_name": room_name,
                        "participant_identity": participant_identity
                    }),
                    deployment=settings.LIVEKIT_AGENT_DEPLOYMENT
                )
            )

        logger.info(
            "Voice session created: room=%s deployment=%s dispatch_id=%s",
            room_name,
            settings.LIVEKIT_AGENT_DEPLOYMENT,
            dispatch.id
        )

    except Exception:

        logger.exception(
            "Failed to create LiveKit voice session"
        )

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to create voice session. Please try again."
        )

    return {
        "message": "Voice session created successfully",
        "server_url": settings.LIVEKIT_URL,
        "participant_token": participant_token,
        "room_name": room_name,
        "participant_identity": participant_identity
    }


# ==========================================================
# VERIFY AGENT VOICE SESSION
# ==========================================================

@router.post("/verify")
async def verify_agent_voice_session(
    request: VoiceVerificationRequest
):

    patient_id = verify_voice_session_token(
        token=request.voice_token,
        room_name=request.room_name,
        participant_identity=request.participant_identity
    )

    if patient_id is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired voice session"
        )

    # Issue a short-lived normal API token.
    # Existing patient-protected endpoints can validate it.
    access_token = create_access_token(
        patient_id=patient_id,
        expires_minutes=10
    )

    logger.info(
        "Agent voice session verified for room=%s",
        request.room_name
    )

    return {
        "authenticated": True,
        "patient_id": patient_id,
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 600
    }
