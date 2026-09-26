from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import EventParticipant, Participant, ScoreEntry


@dataclass(frozen=True)
class LeaderboardRow:
    participant_id: str
    display_name: str
    score: int
    approved_tasks: int
    last_approval_at: datetime | None


def calculate_leaderboard(db: Session, event_id: str) -> list[LeaderboardRow]:
    participants = (
        db.query(EventParticipant, Participant)
        .join(Participant, EventParticipant.participant_id == Participant.id)
        .filter(EventParticipant.event_id == event_id, EventParticipant.eligible.is_(True))
        .all()
    )
    score_entries = db.query(ScoreEntry).filter_by(event_id=event_id).all()
    by_participant: dict[str, list[ScoreEntry]] = {}
    for entry in score_entries:
        by_participant.setdefault(entry.participant_id, []).append(entry)

    rows = []
    for event_participant, participant in participants:
        entries = by_participant.get(participant.id, [])
        rows.append(
            LeaderboardRow(
                participant_id=participant.id,
                display_name=participant.display_name or "Participant",
                score=sum(entry.points for entry in entries),
                approved_tasks=len(entries),
                last_approval_at=max((entry.created_at for entry in entries), default=None),
            )
        )

    def sort_key(row: LeaderboardRow) -> tuple[object, ...]:
        last_approval = row.last_approval_at
        if last_approval is None:
            last_approval = datetime.max.replace(tzinfo=timezone.utc)
        return (
            -row.score,
            -row.approved_tasks,
            last_approval,
            row.display_name.lower(),
            row.participant_id,
        )

    return sorted(rows, key=sort_key)


def serialize_leaderboard(rows: list[LeaderboardRow]) -> list[dict[str, object]]:
    return [
        {
            "rank": rank,
            "participant": row.display_name,
            "participantId": row.participant_id,
            "score": row.score,
            "approvedTasks": row.approved_tasks,
        }
        for rank, row in enumerate(rows, start=1)
    ]
