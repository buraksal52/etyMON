# Platform — Agent Execution Plan

## 1. Purpose

This document is written specifically for coding agents.

The objective is to allow multiple agents to build Platform without changing product decisions or stepping on each other's work.

Read before editing code:

1. `docs/PROJECT_BRIEF.md`
2. `docs/TECHNICAL_SPEC.md`
3. this document.

---

# 2. Golden Rule

**Do not redesign the product.**

If a product decision appears strange but is explicitly documented, implement it.

Do not replace the existing concept with what you believe is a better hackathon product.

Do not add speculative features unless they are required for the implementation.

---

# 3. Priority

Order of importance:

```text
Working participant flow
>
Working organizer flow
>
Correct backend state
>
Reliable demo
>
Monad integration
>
Visual polish
>
Optional improvements
```

A beautiful UI with broken state transitions is failure.

---

# 4. MVP Critical Path

The critical path is:

```text
QR
↓
email
↓
waiting
↓
organizer start
↓
random task
↓
proof
↓
admin approval
↓
score
↓
leaderboard
↓
next task
```

Do not work on secondary features until this flow works end-to-end.

Travel reimbursement is required after the critical path.

---

# 5. Suggested Agent Ownership

## Agent A — Foundation / Backend

Own:

* monorepo;
* FastAPI application;
* database;
* migrations;
* auth/session;
* event APIs;
* participants;
* task assignment engine;
* scoring;
* leaderboard.

Primary directories:

```text
apps/api
packages/db
packages/shared
```

---

## Agent B — Participant Frontend

Own:

* QR landing;
* email flow;
* waiting screen;
* active task UI;
* proof upload;
* progress;
* leaderboard;
* event ended state;
* reimbursement UI.

Primary directory:

```text
apps/web
```

Participant-facing routes only.

---

## Agent C — Organizer Dashboard

Own:

* organizer authentication;
* event dashboard;
* participant import;
* event controls;
* task management;
* submission review;
* leaderboard view;
* reimbursement review.

Use clearly separated admin routes.

Example:

```text
/admin/*
```

---

## Agent D — Monad / Smart Contracts

Own:

* reward contract;
* deployment scripts;
* contract tests;
* backend settlement adapter;
* settlement retry flow;
* documentation.

Primary directories:

```text
packages/contracts
apps/api/app/blockchain
```

Must not block the core product.

---

## Agent E — QA / Integration

Own:

* end-to-end tests;
* test fixtures;
* seed data;
* regression checks;
* demo script;
* README validation.

This agent should integrate continuously rather than only at the end.

---

# 6. Phase 0 — Repository Bootstrap

Deliverables:

* package manager configured for the Next.js frontend;
* Python environment and lockfile configured for FastAPI;
* monorepo bootable;
* frontend boots;
* API boots;
* PostgreSQL boots;
* linting;
* formatting;
* TypeScript and Python configuration;
* `.env.example`;
* Docker Compose if useful for local development;
* Vercel frontend deployment configuration;
* Railway API/database deployment configuration.

Gate:

```text
install
database start
migration
seed
frontend start
api start
```

must all work.

---

# 7. Phase 1 — Database

Implement entities:

* Event
* Participant
* EventParticipant
* Task
* TaskAssignment
* Submission
* ScoreEntry
* Organizer
* TravelReimbursement
* PrizeConfig
* RewardSettlement
* AuditLog

Create migration.

Create development seed.

Gate:

seed database contains:

```text
1 event
1 organizer
10 participants
5 tasks
2 prize sets
```

---

# 8. Phase 2 — Participant Entry

Implement:

```text
GET /events/:slug
POST /events/:slug/join
GET /events/:eventId/status
GET /events/:eventId/me
```

Tests:

### Valid participant

Given:

```text
event = WAITING
email exists in eligibility list
```

Expected:

```text
join succeeds
session created
participant sees waiting screen
```

### Invalid participant

Given:

```text
email not registered
```

Expected:

```text
403 or equivalent product-safe rejection
no participant session
```

---

# 9. Phase 3 — Organizer Event Controls

Implement:

* organizer auth;
* dashboard;
* event status;
* Start button;
* End button.

Start test:

```text
WAITING → ACTIVE
```

End test:

```text
ACTIVE → ENDED
```

Invalid transitions must fail.

Examples:

```text
ENDED → ACTIVE
ACTIVE → WAITING
```

must not happen accidentally.

---

# 10. Phase 4 — Waiting Experience

Participant waiting page:

* reads backend event status;
* automatically transitions when active;
* does not require refresh.

Polling every 3–5 seconds is enough.

Gate:

Two browsers:

```text
Browser A = organizer
Browser B = participant
```

Participant waits.

Organizer clicks Start.

Participant browser enters active task experience automatically.

---

# 11. Phase 5 — Task Engine

Implement:

```text
POST /events/:eventId/tasks/next
GET /events/:eventId/tasks/current
```

Rules:

* only ACTIVE event;
* before deadline;
* one unresolved task maximum;
* no duplicate task for same participant;
* respect availability window;
* respect max assignments.

Task assignment must be persisted before response.

---

# 12. Phase 6 — Participant Task UI

Display:

```text
Task title
Task instructions
Points
Required proof
Submit button
```

Proof component must adapt based on:

```text
IMAGE
URL
TEXT
IMAGE_AND_URL
```

Do not create five separate page architectures.

Use reusable proof components.

---

# 13. Phase 7 — Submission Backend

Implement multipart upload.

Validate:

* participant owns assignment;
* assignment active;
* event active;
* deadline valid;
* proof requirements met.

Submission must create persistent record.

A participant refreshing the page must not lose submission state.

---

# 14. Phase 8 — Organizer Review

Organizer page lists pending submissions.

Card layout:

```text
Participant
Task
Proof
Submitted at
Approve
Reject
```

Approve must run inside transaction.

Expected effects:

```text
Submission → APPROVED
Assignment → APPROVED
ScoreEntry created
EventParticipant.score updated
AuditLog created
```

Unique ScoreEntry prevents double award.

---

# 15. Phase 9 — Leaderboard

Participant and admin leaderboard must use same backend ranking function.

Do not duplicate ranking logic in frontend.

Ordering:

```text
score DESC
approved tasks DESC
last approval ASC
```

Gate:

seed or test should deliberately create tied scores.

Tie order must remain deterministic.

---

# 16. Phase 10 — Next Task Flow

After approved task:

participant can request or automatically receive next task.

Recommended UX:

```text
Task approved
+50 points
[Next Task]
```

Avoid automatic task replacement before participant sees approval feedback.

---

# 17. Phase 11 — Reimbursement

Implement participant upload.

Fields:

```text
receipt
amount optional
currency optional
transport type optional
description optional
```

Organizer sees requests.

Organizer actions:

```text
Approve
Reject
Mark Paid
```

Files are private.

Use signed URLs.

---

# 18. Phase 12 — Monad Contract

Implement `RewardPool`.

Minimum contract tests:

### Deposit

Funds can enter reward pool.

### Authorized reward

Authorized account can reward participant.

### Unauthorized reward

Unauthorized account reverts.

### Duplicate reward

Same `reasonId` cannot pay twice.

### Event

Reward event emitted.

---

# 19. Phase 13 — Backend Monad Adapter

Create interface:

```ts
interface RewardSettlementProvider {
  sendReward(input: RewardInput): Promise<SettlementResult>;
}
```

Monad implementation goes behind this interface.

This allows application tests to mock blockchain.

Do not scatter ethers/viem calls across business logic.

---

# 20. Phase 14 — Reward Settlement

When backend decides a blockchain reward is due:

```text
create RewardSettlement(PENDING)
↓
submit tx
↓
status SUBMITTED
↓
tx confirmation
↓
status CONFIRMED
```

Failure:

```text
FAILED
```

Must be retryable.

Never award same settlement twice.

---

# 21. Phase 15 — Final Event Deadline

Backend must check deadline on:

* assignment;
* proof submission.

Create test using mocked time.

Example:

```text
deadline = 17:00
request time = 17:00:01
```

Expected:

```text
new task rejected
new submission rejected
```

Organizer can still review existing submissions.

---

# 22. UI Design Rules

Visual direction:

* clean;
* modern;
* Monad/event-friendly;
* mobile first;
* minimal number of controls;
* obvious primary action;
* readable in crowded physical environments.

Do not spend time building an elaborate design system.

Reusable primitives are enough:

* Button
* Card
* Modal
* Input
* StatusBadge
* FileUploader
* Timer
* TaskCard
* SubmissionCard
* LeaderboardRow

---

# 23. Participant Route Suggestion

```text
/e/:slug
/e/:slug/join
/e/:slug/waiting
/e/:slug/task
/e/:slug/progress
/e/:slug/leaderboard
/e/:slug/travel
/e/:slug/ended
```

Actual framework implementation may consolidate routes.

Behavior matters more than exact URL structure.

---

# 24. Admin Route Suggestion

```text
/admin
/admin/events/:id
/admin/events/:id/tasks
/admin/events/:id/participants
/admin/events/:id/submissions
/admin/events/:id/leaderboard
/admin/events/:id/reimbursements
```

---

# 25. Task Seed Data

Create tasks based directly on approved concepts.

## Task A

Title:

```text
Monad Vibes
```

Instructions:

```text
Take a photo with X.
Post it on X with the phrase:
"monad vibes only"
Submit the post URL and photo.
```

Proof:

```text
IMAGE_AND_URL
```

---

## Task B

Title:

```text
Hidden Object
```

Instructions:

```text
Find the hidden object in the event area.
Upload a photo of the object.
```

Proof:

```text
IMAGE
```

---

## Task C

Title:

```text
Badge Post
```

Instructions:

```text
Take a photo of your event badge.
Post it on X and tag Monad.
Submit the post URL.
```

Proof:

```text
URL
```

---

## Task D

Title:

```text
Coffee Stand Meetup
```

Instructions:

```text
Meet person B near the coffee stand during the configured time window.
Upload visual proof.
```

Proof:

```text
IMAGE
```

Time constrained.

---

## Task E

Title:

```text
Teach Web3
```

Instructions:

```text
Write or submit an article about a Web3 topic you know.
```

Proof:

```text
TEXT or URL
```

---

# 26. Import Format

Participants are not preloaded by CSV. They join through the event QR URL or
event code and enter an email; the API creates the participant record and event
membership at that point.

---

# 27. Demo Data

Demo event:

```text
Name: Monad Hackathon
Timezone: event local timezone
State: WAITING
Task deadline: 17:00
```

Have at least:

* 10 participants;
* 5 tasks;
* multiple pending submissions;
* approved score entries;
* one reimbursement request.

This ensures every dashboard screen has useful content.

---

# 28. End-to-End Acceptance Test

## Test E2E-001

### Setup

Event is WAITING.

Participant email is registered.

### Steps

1. Open event QR URL.
2. Enter registered email.
3. Observe waiting screen.
4. Open organizer dashboard.
5. Click Start.
6. Participant automatically leaves waiting state.
7. Participant receives task.
8. Upload valid proof.
9. Organizer sees submission.
10. Organizer approves.
11. Participant receives points.
12. Leaderboard updates.
13. Participant opens next task.
14. Participant uploads travel receipt.
15. Organizer sees reimbursement.
16. Organizer approves reimbursement.
17. Organizer ends event.
18. Participant attempts new task.

### Expected

Final task request rejected because event is ended.

If all steps pass, MVP critical path is valid.

---

# 29. Failure Tests

Agents must test at least:

* unknown email;
* duplicate join;
* two simultaneous next-task requests;
* task submission from wrong participant;
* submission after deadline;
* double approval;
* invalid file type;
* oversized upload;
* event end while participant has open task;
* RPC unavailable;
* duplicate blockchain payout.

---

# 30. README Requirements

README must contain:

```text
Project description
Architecture
Prerequisites
Environment variables
Install
Database startup
Migration
Seed
Frontend start
FastAPI start
Vercel deployment
Railway deployment and migration
Contract test
Contract deploy
Demo credentials
Demo walkthrough
```

No undocumented magic steps.

---

# 31. Commit Discipline

Agents should make logically scoped commits.

Examples:

```text
feat(db): add event and participant schema
feat(tasks): implement random assignment
feat(admin): add submission review
feat(rewards): add Monad reward pool
test(e2e): cover participant lifecycle
```

Avoid one giant final commit.

---

# 32. Agent Change Policy

Before altering another agent's module:

1. inspect existing interface;
2. preserve public contract where possible;
3. update tests;
4. document breaking changes.

Do not rewrite another module purely because you prefer a different style.

---

# 33. Implementation Assumptions

Agents may choose implementation details when not specified.

Examples:

* UI component library;
* exact ORM helper layout;
* polling implementation;
* exact storage provider;
* exact test framework.

They may NOT choose different product behavior.

---

# 34. No-Guess Areas

If the following are not provided, keep them configurable:

* prize currency;
* meaning of Prize Set A vs Prize Set B;
* exact Monad RPC;
* production contract address;
* organizer credentials;
* exact people represented by X and B;
* event timezone;
* reward token.

Never invent business meaning.

---

# 35. Final Definition of Done

The product is done for hackathon MVP when:

* participant can join;
* invalid users cannot join;
* participant waits for organizer;
* organizer starts event;
* random task is assigned;
* participant submits proof;
* organizer reviews proof;
* approved score is persistent;
* score cannot duplicate;
* leaderboard works;
* next task works;
* deadline works;
* event ending works;
* receipt upload works;
* reimbursement review works;
* Monad contract works;
* at least one reward can settle;
* blockchain failure does not break core event;
* app runs from clean setup;
* demo flow is documented;
* automated tests cover critical state transitions.

Do not call the project complete before the full E2E acceptance test passes.
