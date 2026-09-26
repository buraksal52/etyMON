from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.db.models import (
    Event,
    EventParticipant,
    EventState,
    Organizer,
    Participant,
    PrizeConfig,
    RewardType,
    Task,
)
from app.settings import settings


def seed_development_data(db: Session) -> dict[str, int]:
    """Create the deterministic Phase 1 development dataset."""
    existing_event = db.query(Event).filter_by(slug="monad-hackathon").one_or_none()
    if existing_event is not None:
        return {
            "events": db.query(Event).count(),
            "organizers": db.query(Organizer).count(),
            "participants": db.query(Participant).count(),
            "tasks": db.query(Task).count(),
            "prize_configs": db.query(PrizeConfig).count(),
        }

    now = datetime.now(timezone.utc)
    event = Event(
        name="Monad Hackathon",
        slug="monad-hackathon",
        description="Monad hackathon participation event",
        timezone=settings.event_timezone,
        state=EventState.WAITING.value,
        registration_opens_at=now,
        task_deadline_at=now.replace(hour=17, minute=0, second=0, microsecond=0),
    )
    db.add(event)

    organizer = Organizer(
        email="organizer@example.com",
        name="Platform Organizer",
        password_hash_or_auth_provider_id=hash_password("phase3-demo-password"),
    )
    db.add(organizer)

    participants = [
        Participant(email=f"participant{i}@example.com", display_name=f"Participant {i}")
        for i in range(1, 11)
    ]
    db.add_all(participants)
    db.flush()
    db.add_all(
        [
            EventParticipant(event=event, participant=participant, eligible=True)
            for participant in participants
        ]
    )

    tasks = [
        Task(
            event=event,
            title="Monad Vibes",
            description="Take a photo with X and post it on X.",
            instructions='Include the phrase "monad vibes only" and submit the post URL and photo.',
            points=50,
            proof_type="IMAGE_AND_URL",
            assignment_weight=1,
            metadata_json={"required_phrase": "monad vibes only", "social_platform": "X"},
        ),
        Task(
            event=event,
            title="Hidden Object",
            description="Find the hidden object in the event area.",
            instructions="Upload a photo of the hidden object.",
            points=40,
            proof_type="IMAGE",
            assignment_weight=1,
        ),
        Task(
            event=event,
            title="Badge Post",
            description="Take a photo of your event badge.",
            instructions="Post it on X, tag Monad, and submit the post URL.",
            points=35,
            proof_type="URL",
            assignment_weight=1,
            metadata_json={"social_platform": "X", "required_tag": "Monad"},
        ),
        Task(
            event=event,
            title="Coffee Stand Meetup",
            description="Meet person B near the coffee stand.",
            instructions="Meet during the configured time window and upload visual proof.",
            points=60,
            proof_type="IMAGE",
            starts_at=now + timedelta(hours=1),
            expires_at=now + timedelta(hours=2),
            assignment_weight=1,
            metadata_json={"location": "coffee stand", "target_person": "B"},
        ),
        Task(
            event=event,
            title="Teach Web3",
            description="Submit an article about a Web3 topic you know.",
            instructions="Write or submit an article as text or a URL.",
            points=75,
            proof_type="TEXT_OR_URL",
            assignment_weight=1,
        ),
    ]
    db.add_all(tasks)

    prize_sets = [
        (
            "Prize Set A",
            [
                (1, RewardType.CASH.value, Decimal("175")),
                (2, RewardType.CASH.value, Decimal("125")),
                (3, RewardType.MERCH.value, None),
            ],
        ),
        (
            "Prize Set B",
            [
                (1, RewardType.CASH.value, Decimal("800")),
                (2, RewardType.CASH.value, Decimal("500")),
                (3, RewardType.CASH.value, Decimal("400")),
            ],
        ),
    ]
    db.add_all(
        [
            PrizeConfig(
                event=event,
                name=set_name,
                rank=rank,
                reward_type=reward_type,
                amount=amount,
                currency=None,
            )
            for set_name, prizes in prize_sets
            for rank, reward_type, amount in prizes
        ]
    )

    db.commit()
    return {
        "events": 1,
        "organizers": 1,
        "participants": 10,
        "tasks": 5,
        "prize_configs": 6,
    }
