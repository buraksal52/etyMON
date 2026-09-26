from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base, Event, Organizer, Participant, PrizeConfig, Task
from app.db.seed import seed_development_data


def test_seed_does_not_create_mock_data() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        counts = seed_development_data(db)

        assert counts == {
            "events": 0,
            "organizers": 0,
            "participants": 0,
            "tasks": 0,
            "prize_configs": 0,
        }
        assert db.query(Event).count() == 0
        assert db.query(Organizer).count() == 0
        assert db.query(Participant).count() == 0
        assert db.query(Task).count() == 0
        assert db.query(PrizeConfig).count() == 0
