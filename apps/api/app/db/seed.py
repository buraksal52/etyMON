from sqlalchemy.orm import Session

from app.db.models import Event, Organizer, Participant, PrizeConfig, Task


def seed_development_data(db: Session) -> dict[str, int]:
    """Report existing data without inserting demo or mock records."""
    return {
        "events": db.query(Event).count(),
        "organizers": db.query(Organizer).count(),
        "participants": db.query(Participant).count(),
        "tasks": db.query(Task).count(),
        "prize_configs": db.query(PrizeConfig).count(),
    }
