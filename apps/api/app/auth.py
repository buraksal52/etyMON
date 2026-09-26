from dataclasses import dataclass
import base64
import hashlib
import hmac
import secrets

from fastapi import Cookie, Depends, HTTPException, status
from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.db.models import EventParticipant, Organizer, Participant
from app.db.session import get_db
from app.settings import settings

SESSION_COOKIE = "platform_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12
ADMIN_SESSION_COOKIE = "platform_admin_session"


@dataclass(frozen=True)
class ParticipantSession:
    event_id: str
    participant_id: str


@dataclass(frozen=True)
class OrganizerSession:
    organizer_id: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return "scrypt${}${}".format(
        base64.urlsafe_b64encode(salt).decode(), base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, salt_value, digest_value = encoded_hash.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = base64.urlsafe_b64decode(salt_value.encode())
        expected = base64.urlsafe_b64decode(digest_value.encode())
        actual = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="participant-session")


def _admin_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="organizer-session")


def create_session_token(event_id: str, participant_id: str) -> str:
    return _serializer().dumps({"event_id": event_id, "participant_id": participant_id})


def read_session_token(token: str) -> ParticipantSession:
    try:
        payload = _serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except BadSignature as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session"
        ) from exc
    return ParticipantSession(
        event_id=payload["event_id"], participant_id=payload["participant_id"]
    )


def create_admin_session_token(organizer_id: str) -> str:
    return _admin_serializer().dumps({"organizer_id": organizer_id})


def get_current_organizer(
    session_cookie: str | None = Cookie(default=None, alias=ADMIN_SESSION_COOKIE),
    db: Session = Depends(get_db),
) -> tuple[OrganizerSession, Organizer]:
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Organizer session required"
        )
    try:
        payload = _admin_serializer().loads(session_cookie, max_age=SESSION_MAX_AGE_SECONDS)
    except BadSignature as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid organizer session"
        ) from exc
    organizer = db.get(Organizer, payload.get("organizer_id"))
    if organizer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid organizer session"
        )
    return OrganizerSession(organizer_id=organizer.id), organizer


def get_participant_session(
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> ParticipantSession:
    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Participant session required"
        )
    return read_session_token(session_cookie)


def get_current_participant(
    session: ParticipantSession = Depends(get_participant_session),
    db: Session = Depends(get_db),
) -> tuple[ParticipantSession, Participant, EventParticipant]:
    participant = db.get(Participant, session.participant_id)
    event_participant = (
        db.query(EventParticipant)
        .filter_by(event_id=session.event_id, participant_id=session.participant_id)
        .one_or_none()
    )
    if participant is None or event_participant is None or not event_participant.eligible:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid participant session"
        )
    return session, participant, event_participant
