from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings
from app.security import enforce_request_origin
from app.routes.events import router as events_router
from app.routes.admin import router as admin_router
from app.routes.tasks import router as tasks_router
from app.routes.submissions import router as submissions_router
from app.routes.leaderboard import router as leaderboard_router
from app.routes.reimbursements import router as reimbursements_router
from app.routes.storage import router as storage_router


app = FastAPI(title="Platform API", version="0.1.0")

app.middleware("http")(enforce_request_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)
app.include_router(admin_router)
app.include_router(tasks_router)
app.include_router(submissions_router)
app.include_router(leaderboard_router)
app.include_router(reimbursements_router)
app.include_router(storage_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
