# Platform — Technical Specification

## 1. Goal

This document defines the technical implementation of Platform.

The system must support a live hackathon with:

* participant onboarding through QR;
* email-based eligibility;
* organizer-controlled event state;
* randomized task assignment;
* proof submission;
* organizer verification;
* leaderboard calculation;
* travel reimbursement submissions;
* optional Monad-backed reward settlement.

Product decisions in `PROJECT_BRIEF.md` are authoritative.

If technical convenience conflicts with the product brief, the product brief wins.

---

# 2. Recommended Stack

## Frontend

Recommended:

* Next.js
* TypeScript
* Tailwind CSS
* React Query / TanStack Query

Alternative React frameworks are allowed only if they do not slow implementation.

---

## Backend

Required:

* Python 3.12+
* FastAPI
* Pydantic v2
* SQLAlchemy 2.x or SQLModel
* Alembic

The API is deployed as a Railway service. FastAPI owns authentication,
event state, task assignment, submissions, scoring, leaderboard,
reimbursements, and the Monad adapter.

---

## Database

PostgreSQL.

ORM recommendation:

* SQLAlchemy 2.x with Alembic migrations

---

## Object Storage

Required for:

* proof images;
* reimbursement receipts;
* uploaded documents.

Possible implementations:

* Railway Storage Buckets (preferred for this deployment);
* Amazon S3;
* Supabase Storage;
* another S3-compatible object storage provider.

Storage provider must be abstracted from business logic. Railway Storage
Buckets are S3-compatible and should be used for production proof images,
receipts, and uploaded documents. Railway Volumes may be used for local or
single-service persistent files, but must not be treated as a horizontally
shared object store for user uploads.

---

## Blockchain

Target network:

**Monad**

Use EVM-compatible smart contracts.

Contract language:

**Solidity**

Use a standard audited library such as OpenZeppelin where appropriate.

Do not expose blockchain complexity to participant UI.

---

# 3. High-Level Architecture

```text
Participant Browser
       |
       v
   Web Frontend
       |
       v
   FastAPI API
  /   |    \
 /    |     \
DB  Storage  Monad
             Contracts

Organizer Browser
       |
       v
   Admin Frontend
       |
       v
      API
```

---

# 4. Suggested Monorepo Structure

```text
/
├── apps/
│   ├── web/                 # Next.js, deployed to Vercel
│   └── api/                 # FastAPI, deployed to Railway
│
├── packages/
│   ├── db/                  # SQLAlchemy models and Alembic helpers
│   ├── contracts/
│   ├── shared/
│   └── config/
│
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── TECHNICAL_SPEC.md
│   └── AGENT_EXECUTION_PLAN.md
│
├── docker/
├── scripts/
├── railway.toml
├── .env.example
├── docker-compose.yml
├── package.json
└── README.md
```

---

# 5. Domain Entities

## Event

Fields:

```text
id
name
slug
description
timezone
state
registration_opens_at
starts_at
task_deadline_at
ended_at
created_at
updated_at
```

State enum:

```text
DRAFT
WAITING
ACTIVE
ENDED
```

---

## Participant

```text
id
email
display_name
created_at
updated_at
```

Email should be normalized before comparison.

Recommended normalization:

* lowercase;
* trim whitespace.

Do not apply provider-specific transformations such as removing Gmail dots.

---

## EventParticipant

Represents participant eligibility in one event.

```text
id
event_id
participant_id
eligible
checked_in_at
score
created_at
updated_at
```

Unique constraint:

```text
(event_id, participant_id)
```

---

## Task

```text
id
event_id
title
description
instructions
points
proof_type
starts_at
expires_at
assignment_weight
max_assignments
active
metadata_json
created_at
updated_at
```

---

## TaskAssignment

Immutable logical assignment.

```text
id
event_id
task_id
participant_id
status
assigned_at
submitted_at
resolved_at
created_at
updated_at
```

Statuses:

```text
ASSIGNED
SUBMITTED
APPROVED
REJECTED
EXPIRED
```

Unique constraints should prevent accidental duplicate active assignment.

---

## Submission

```text
id
assignment_id
participant_id
text_content
url
storage_key
metadata_json
submitted_at
reviewed_at
reviewed_by
review_note
status
```

Submission status:

```text
PENDING
APPROVED
REJECTED
```

---

## Organizer

```text
id
email
name
password_hash_or_auth_provider_id
role
created_at
updated_at
```

For hackathon MVP, a simple protected organizer authentication method is acceptable.

---

## TravelReimbursement

```text
id
event_id
participant_id
amount
currency
transport_type
description
storage_key
status
review_note
submitted_at
reviewed_at
reviewed_by
paid_at
```

Statuses:

```text
SUBMITTED
APPROVED
REJECTED
PAID
```

`amount` and `currency` may be nullable if the initial upload form does not require them.

---

## PrizeConfig

```text
id
event_id
name
rank
reward_type
amount
currency
description
metadata_json
```

Reward types:

```text
CASH
TOKEN
MERCH
OTHER
```

This prevents hard-coded assumptions around the two existing prize sets.

---

# 6. Authentication

## Participant Authentication

MVP authentication is event-email based.

Flow:

```text
POST /events/:slug/join
{
  "email": "participant@example.com"
}
```

Server:

1. normalize email;
2. check event state;
3. check participant eligibility;
4. create participant session;
5. return event session token/cookie.

Use:

* secure;
* httpOnly;
* sameSite;

session cookies when possible.

Do not expose participant IDs as authentication credentials.

The Next.js frontend is deployed to Vercel and calls the Railway API through
the environment-configured `NEXT_PUBLIC_API_URL`. The FastAPI service must
configure CORS for the Vercel production domain and required preview domains.
For cross-origin sessions, use secure httpOnly cookies with an explicit
CSRF strategy and validate the allowed origins server-side.

## Deployment Topology

```text
Vercel
  └── Next.js participant and organizer frontend
          │ HTTPS API requests
          ▼
Railway
  ├── FastAPI API service
  ├── PostgreSQL service
  └── optional worker service for reward settlement/retries

Railway Storage Bucket (S3-compatible)
  └── proof images, receipts, and uploaded documents
```

Vercel handles frontend previews and production deployments from the web
application. Railway handles the API, database, migrations, and background
worker. The API and worker must share the same database and environment
configuration. Blockchain settlement must be asynchronous and retryable.

---

# 7. QR Code

QR contains a URL.

Example:

```text
https://platform.example/e/monad-blitz
```

The QR does NOT contain secret authentication information.

The QR only identifies the event.

Participant eligibility comes from email matching.

---

# 8. Event Start

Organizer endpoint:

```http
POST /admin/events/:eventId/start
```

Required checks:

* organizer authorized;
* event currently WAITING;
* task pool not empty.

Transaction:

```text
event.state = ACTIVE
event.starts_at = now()
```

Participants waiting on the event page must detect this automatically.

Recommended:

* polling every 3–5 seconds for MVP;
* WebSocket/SSE optional.

Polling is acceptable and safer for a rushed hackathon MVP.

---

# 9. Event End

Automatic deadline enforcement is mandatory.

Even if organizer forgets to press End, backend must reject actions after `task_deadline_at`.

Never rely on frontend timer.

Organizer endpoint:

```http
POST /admin/events/:eventId/end
```

sets:

```text
state = ENDED
ended_at = now()
```

---

# 10. Task Assignment Algorithm

Endpoint:

```http
POST /events/:eventId/tasks/next
```

Rules:

1. user authenticated;
2. event ACTIVE;
3. current time before deadline;
4. participant eligible;
5. participant does not already have unresolved active assignment;
6. candidate tasks selected.

Candidate query excludes:

* inactive tasks;
* tasks before starts_at;
* expired tasks;
* tasks already assigned to participant;
* tasks whose max_assignments have been reached.

Then select random task.

Recommended SQL-safe implementation:

* fetch bounded eligible candidate IDs;
* perform weighted choice in backend;
* create assignment inside DB transaction.

Avoid:

```text
ORDER BY RANDOM()
```

if dataset becomes large.

For MVP-sized events it is acceptable, but backend weighted selection is cleaner.

---

# 11. Assignment Concurrency

Two simultaneous requests from the same participant must NOT create two assignments.

Use one of:

* database transaction + lock;
* unique partial index;
* idempotency key;
* advisory lock.

Recommended:

transaction + unique constraint.

Concept:

```text
participant can have max one unresolved assignment per event
```

---

# 12. Proof Submission

Endpoint:

```http
POST /assignments/:assignmentId/submit
```

Possible multipart fields:

```text
file
text
url
```

Backend must verify:

* assignment belongs to participant;
* assignment is ASSIGNED;
* event deadline has not passed;
* required proof fields exist;
* file size/type acceptable.

Then:

```text
assignment.status = SUBMITTED
submission.status = PENDING
```

---

# 13. Proof Upload Security

Allowed initial media types:

```text
image/jpeg
image/png
image/webp
application/pdf
```

PDF primarily needed for receipts.

Recommended maximum:

* images: 10 MB;
* receipts/PDF: 15 MB.

Generate unique storage keys.

Never trust original filename as storage path.

Example:

```text
events/{eventId}/participants/{participantId}/proofs/{uuid}.jpg
```

---

# 14. Organizer Review

Endpoint:

```http
POST /admin/submissions/:submissionId/review
```

Payload:

```json
{
  "decision": "APPROVED",
  "note": ""
}
```

Approval transaction:

1. confirm PENDING status;
2. update submission APPROVED;
3. update assignment APPROVED;
4. add task points to participant score;
5. set resolution timestamp.

Rejection:

1. update submission REJECTED;
2. update assignment REJECTED;
3. no points.

Point updates must be transactional.

Double approval must not double-credit score.

---

# 15. Score Ledger

Do not rely exclusively on a mutable `score` column.

Recommended additional entity:

## ScoreEntry

```text
id
event_id
participant_id
assignment_id
points
reason
created_at
```

Unique:

```text
assignment_id
```

Participant score can be:

* cached in EventParticipant.score;
* recomputed from score ledger if necessary.

This prevents duplicate scoring.

---

# 16. Leaderboard API

```http
GET /events/:eventId/leaderboard
```

Response:

```json
[
  {
    "rank": 1,
    "participant": "Burak",
    "score": 420,
    "approvedTasks": 7
  }
]
```

Ordering:

```text
score DESC
approved_count DESC
last_approval_time ASC
```

---

# 17. Reimbursement API

Participant:

```http
POST /events/:eventId/reimbursements
```

multipart:

```text
file
amount?
currency?
transportType?
description?
```

List own:

```http
GET /events/:eventId/reimbursements/me
```

Organizer:

```http
GET /admin/events/:eventId/reimbursements
```

Review:

```http
POST /admin/reimbursements/:id/review
```

Mark paid:

```http
POST /admin/reimbursements/:id/paid
```

---

# 18. Admin Endpoints

Minimum:

```text
POST   /admin/events
GET    /admin/events/:id
PATCH  /admin/events/:id

POST   /admin/events/:id/start
POST   /admin/events/:id/end

POST   /admin/events/:id/participants/import
GET    /admin/events/:id/participants

POST   /admin/events/:id/tasks
GET    /admin/events/:id/tasks
PATCH  /admin/tasks/:id
DELETE /admin/tasks/:id

GET    /admin/events/:id/submissions
POST   /admin/submissions/:id/review

GET    /admin/events/:id/reimbursements
POST   /admin/reimbursements/:id/review
POST   /admin/reimbursements/:id/paid

GET    /admin/events/:id/leaderboard
```

---

# 19. Participant Endpoints

```text
GET  /events/:slug
POST /events/:slug/join

GET  /events/:eventId/status
GET  /events/:eventId/me

POST /events/:eventId/tasks/next
GET  /events/:eventId/tasks/current

POST /assignments/:id/submit

GET  /events/:eventId/leaderboard

POST /events/:eventId/reimbursements
GET  /events/:eventId/reimbursements/me
```

---

# 20. Monad Integration

Blockchain must remain behind the product.

The participant should not need to understand:

* wallet switching;
* chain IDs;
* gas;
* transaction hashes;
* RPC;
* smart contracts.

---

# 21. Contract Scope

Recommended initial smart contract:

## RewardPool

Responsibilities:

* hold event reward funds;
* allow authorized backend/organizer to distribute reward;
* prevent duplicate reward claims;
* emit payout events;
* allow owner withdrawal after event if needed.

Suggested conceptual interface:

```solidity
interface IRewardPool {
    function deposit() external payable;

    function rewardParticipant(
        bytes32 eventId,
        bytes32 participantId,
        bytes32 reasonId,
        address recipient,
        uint256 amount
    ) external;

    function isPaid(bytes32 reasonId)
        external
        view
        returns (bool);
}
```

If ERC-20 rewards are used, provide token-aware variant.

---

# 22. Blockchain Identity Mapping

Do NOT store participant email on-chain.

Use internal opaque identifiers.

Example:

```text
participant_hash = keccak256(
    event_specific_salt + internal_participant_uuid
)
```

Never derive the public hash directly from email without a salt.

---

# 23. Blockchain Settlement Record

Create database entity:

## RewardSettlement

```text
id
event_id
participant_id
assignment_id
amount
currency_or_token
status
tx_hash
chain_id
created_at
confirmed_at
```

Statuses:

```text
PENDING
SUBMITTED
CONFIRMED
FAILED
```

---

# 24. Reward Settlement Flow

```text
Task approved
      |
      v
Score granted
      |
      v
Eligible for reward?
      |
     Yes
      |
      v
Create settlement
      |
      v
Backend submits Monad transaction
      |
      v
Store tx hash
      |
      v
Confirm
```

Score approval must not depend on blockchain RPC latency.

Blockchain settlement should be asynchronous relative to score update if needed.

---

# 25. Idempotency

Critical actions must be idempotent.

Particularly:

* join;
* assign next task;
* submit proof;
* approve submission;
* reward settlement;
* reimbursement status updates.

No duplicate transaction should produce duplicate score or payment.

---

# 26. Frontend State Machine

Participant states:

```text
UNAUTHENTICATED
INVALID_EMAIL
WAITING
ACTIVE_NO_TASK
ACTIVE_TASK_ASSIGNED
SUBMISSION_PENDING
TASK_REJECTED
EVENT_ENDED
```

UI must derive state from backend.

Do not invent client-only event state.

---

# 27. Waiting Screen

Minimum:

```text
Event name
You're checked in
Waiting for Port to start the competition
```

Frontend polls:

```text
GET /events/:id/status
```

When:

```json
{
  "state": "ACTIVE"
}
```

navigate automatically to task screen.

---

# 28. Active Task Screen

Display:

* title;
* description;
* instructions;
* points;
* required proof;
* optional time remaining;
* submit action.

Do not clutter the page.

Mobile first.

---

# 29. Organizer Review Screen

Each card should display:

* participant;
* task;
* submission timestamp;
* image/link/text proof;
* approve;
* reject;
* optional note.

Pending submissions should appear first.

---

# 30. Security Requirements

Minimum:

* server-side authorization;
* secure session cookies;
* CSRF protection where necessary;
* upload validation;
* request size limits;
* rate limiting;
* MIME type validation;
* no email leakage in public APIs;
* no private receipt URLs exposed publicly;
* signed URLs for private files;
* admin routes protected.

---

# 31. Audit Log

Recommended entity:

```text
AuditLog
id
event_id
actor_type
actor_id
action
entity_type
entity_id
metadata_json
created_at
```

Track at minimum:

* event start;
* event end;
* task creation/edit;
* submission approval/rejection;
* reimbursement approval/rejection;
* payment actions.

---

# 32. Environment Variables

Suggested:

```text
DATABASE_URL=

API_BASE_URL=

NEXT_PUBLIC_API_URL=

ALLOWED_ORIGINS=

SESSION_SECRET=

APP_URL=

STORAGE_PROVIDER=
STORAGE_BUCKET=
STORAGE_ENDPOINT=
STORAGE_ACCESS_KEY=
STORAGE_SECRET_KEY=
STORAGE_PUBLIC_BASE_URL=

MONAD_RPC_URL=
MONAD_CHAIN_ID=
REWARD_POOL_CONTRACT_ADDRESS=
REWARD_SIGNER_PRIVATE_KEY=

ADMIN_EMAIL=
ADMIN_PASSWORD_HASH=

RAILWAY_ENVIRONMENT=
VERCEL_ENV=
```

Never commit secrets.

---

# 33. Seed Data

Development seed must create:

* one event;
* 10 participants;
* 5 example tasks;
* one organizer;
* prize configuration;
* event state WAITING.

Seeded tasks should correspond to approved task examples.

---

# 34. Testing

Minimum automated coverage:

## Unit

* email normalization;
* task candidate filtering;
* weighted random selection;
* leaderboard ordering;
* score calculation;
* deadline validation.

## Integration

* eligible participant join;
* invalid participant rejected;
* event start;
* one active assignment only;
* proof submission;
* approve exactly once;
* no double score;
* deadline enforcement;
* reimbursement submission.

## Contract

* deposit;
* authorized payout;
* unauthorized payout rejected;
* duplicate reason ID rejected;
* payout event emitted.

---

# 35. Demo Reliability

The product must work even if blockchain settlement is temporarily unavailable.

Do not allow a failed RPC request to destroy:

* task completion;
* score;
* submission;
* leaderboard.

Record settlement failure and allow retry.

---

# 36. Definition of Technical Completion

MVP is technically complete when:

* project runs locally from documented commands;
* PostgreSQL migrations work on Railway and locally;
* seed command works;
* participant QR flow works;
* email eligibility works;
* waiting state works;
* organizer start works;
* random task assignment works;
* proof upload works;
* organizer review works;
* scoring is idempotent;
* leaderboard works;
* travel receipt flow works;
* deadline is backend-enforced;
* event end works;
* contract deploys;
* one test reward transaction can be executed on Monad;
* README explains local setup, Vercel frontend deployment, Railway API/database deployment, and required environment variables.
