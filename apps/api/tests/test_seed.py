from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Event, EventParticipant, Organizer, Participant, PrizeConfig, Task
from app.db.seed import seed_development_data


def test_phase_one_seed_counts() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        counts = seed_development_data(db)

        assert counts == {
            "events": 1,
            "organizers": 1,
            "participants": 10,
            "tasks": 5,
            "prize_configs": 6,
        }
        assert db.query(Event).one().state == "WAITING"
        assert db.query(Organizer).count() == 1
        assert db.query(Participant).count() == 10
        assert db.query(Task).count() == 5
        assert db.query(PrizeConfig).count() == 6
        assert {prize.name for prize in db.query(PrizeConfig).all()} == {
            "Prize Set A",
            "Prize Set B",
        }

        db.query(EventParticipant).delete()
        db.commit()

        repaired = seed_development_data(db)
        assert repaired["participants"] == 10
        assert db.query(EventParticipant).count() == 10
