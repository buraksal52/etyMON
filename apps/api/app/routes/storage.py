from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth import (
    ADMIN_SESSION_COOKIE,
    SESSION_COOKIE,
    get_current_organizer,
    read_session_token,
)
from app.db.models import EventParticipant
from app.db.session import get_db
from app.storage import StorageProvider, get_storage_provider

router = APIRouter(tags=["storage"])


def participant_can_read(key: str, session_cookie: str | None, db: Session) -> bool:
    if not session_cookie:
        return False
    try:
        session = read_session_token(session_cookie)
    except HTTPException:
        return False
    prefix = f"events/{session.event_id}/participants/{session.participant_id}/"
    if not key.startswith(prefix):
        return False
    return (
        db.query(EventParticipant)
        .filter_by(event_id=session.event_id, participant_id=session.participant_id, eligible=True)
        .one_or_none()
        is not None
    )


@router.get("/storage/download")
def download_private_file(
    key: str = Query(min_length=1, max_length=512),
    participant_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    admin_cookie: str | None = Cookie(default=None, alias=ADMIN_SESSION_COOKIE),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> Response:
    is_admin = False
    if admin_cookie:
        try:
            get_current_organizer(admin_cookie, db)
            is_admin = True
        except HTTPException:
            is_admin = False
    if not is_admin and not participant_can_read(key, participant_cookie, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="File access denied")
    try:
        content, content_type = storage.get_bytes(key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    return Response(content=content, media_type=content_type)
