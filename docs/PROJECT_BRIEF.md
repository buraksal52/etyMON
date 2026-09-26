# Platform — Product & Project Brief

## 1. Project Definition

**Platform** is an event participation platform designed initially for Monad hackathons.

The product addresses two observed problems in local and global hackathons:

1. Most participants, especially students, leave the event with no financial or material reward unless they place in the top three.
2. Participants often leave without building enough meaningful connections with other attendees, organizers, sponsors, and ecosystem members.

Platform turns participation itself into an interactive task-based experience.

Participants join the event through a QR code, receive randomized tasks throughout the day, submit proof of task completion, and compete for rewards.

The first target use case is **Monad hackathons**.

---

# 2. Frozen Product Decisions

The following decisions are final.

Agents MUST NOT redesign, reinterpret, remove, or replace these product decisions unless explicitly instructed by the project owner.

## 2.1 Entry Flow

At the beginning of the event, **Port / Organizer** displays a QR code.

Participant flow:

1. Participant scans the QR code.
2. A web page opens.
3. Participant enters their email address.
4. The backend checks and matches the email against the event participant list.
5. If matched, the participant gains access to the platform.
6. Until Port starts the competition, the participant stays on a waiting screen.
7. When Port starts the competition, the task system becomes active.

No traditional account registration flow is required for MVP.

---

# 2.2 Competition Time

The competition is controlled by the organizer.

The organizer manually starts the event.

Once started, participants can perform tasks until:

**17:00 local event time**

After the task deadline:

* new tasks must not be assigned;
* unfinished tasks cannot be newly submitted unless submission began before the deadline and the backend explicitly allows it;
* leaderboard calculations may continue;
* organizer review may continue.

The deadline must be configurable in the system, but the initial event configuration is **17:00**.

---

# 2.3 Task Assignment

Tasks come from an organizer-defined task pool.

Tasks are assigned **randomly per participant**.

The system must not require participants to manually browse the entire task pool.

Participant receives a task.

After the task lifecycle ends, the next task may be assigned.

Task assignment must be server-controlled.

The client must never be trusted to choose or generate its own tasks.

---

# 2.4 Initial Task Examples

The following task concepts are approved.

### Task Example 1

Take a photo with person **X**.

Post it on X/Twitter.

Include:

> monad vibes only

Participant submits proof to the platform.

---

### Task Example 2

Find a hidden object placed somewhere in the event area.

Take a photograph.

Upload the photograph to the platform.

---

### Task Example 3

Take a photograph of the participant badge.

Post it on X/Twitter.

Tag Monad.

Submit proof to the platform.

---

### Task Example 4

At exactly or approximately **14:30**, participant must be together with person **B** near the coffee stand.

Participant submits visual evidence.

The task must support a time window.

Example:

14:25–14:35.

Exact event configuration may be changed by organizer.

---

### Task Example 5

Participant submits an article about a Web3 topic they know.

The article is uploaded or linked through the platform.

---

# 2.5 Proof Types

Tasks may require different proof types.

Supported initial proof types:

* image upload;
* URL;
* text submission;
* image + URL;
* timestamped proof;
* organizer manual verification.

Future proof types may be added without changing the core task model.

---

# 2.6 Prize Configuration

The currently defined prize values are:

## Prize Set A

1st place: **175**

2nd place: **125**

3rd place: **Merch**

## Prize Set B

1st place: **800**

2nd place: **500**

3rd place: **400**

Agents must NOT guess:

* currency;
* whether Set A and Set B belong to separate tracks;
* whether one is task rewards and one is final leaderboard rewards.

Implementation requirement:

Prize sets must be configuration-driven.

The product owner will attach semantic meaning and currency separately.

Do not hard-code currency into the core application.

---

# 2.7 Travel Reimbursement

Participants may upload invoices or receipts related to their travel expenses.

Examples:

* bus ticket;
* train ticket;
* airline ticket;
* transportation invoice;
* payment receipt.

The system must allow participants to submit:

* receipt/invoice file;
* optional amount;
* optional description;
* optional transportation type.

Organizer can review the request.

Initial statuses:

* submitted;
* approved;
* rejected;
* paid.

Travel reimbursement is part of the product scope.

It is NOT to be removed from the MVP specification.

---

# 3. Product Roles

## 3.1 Participant

Can:

* enter via event QR;
* authenticate through registered email;
* see waiting screen;
* receive tasks;
* submit proof;
* see submission status;
* receive subsequent tasks;
* see own score;
* see leaderboard;
* upload travel expense documentation.

Cannot:

* create tasks;
* modify event settings;
* approve own submissions;
* modify score;
* manually select arbitrary tasks.

---

# 3.2 Organizer / Port

Port and Organizer refer to the event administration side.

Organizer can:

* create or configure event;
* import participant emails;
* generate/show event QR;
* start competition;
* end competition;
* configure deadline;
* create task pool;
* edit tasks before competition;
* review proofs;
* approve/reject submissions;
* view leaderboard;
* inspect travel reimbursement requests;
* approve/reject reimbursement requests.

---

# 4. Core User Journey

## Before Event Start

Participant:

Scan QR
→ enter email
→ email matched
→ authenticated event session
→ waiting screen

Waiting screen should communicate:

* successful registration;
* event name;
* competition has not started;
* optional countdown or status.

The system should automatically detect event start through polling, realtime subscription, or equivalent mechanism.

The participant should not have to refresh manually.

---

# 5. Competition Journey

Organizer presses:

**START**

Backend updates event state.

Participants automatically transition from waiting state to active state.

Participant:

Receive random task
→ understand task
→ perform task
→ submit required proof
→ wait for verification / receive status
→ task completed or rejected
→ receive next task according to event rules

---

# 6. Submission States

A task assignment may have the following states:

* assigned;
* submitted;
* approved;
* rejected;
* expired;
* skipped if future policy enables skipping.

Initial MVP does not need participant-controlled task skipping unless later requested.

---

# 7. Leaderboard

Leaderboard must support:

* participant ranking;
* participant display name or privacy-safe identifier;
* points;
* completed task count.

Final ranking is generated using score.

Tie behavior must be deterministic.

Recommended default:

1. higher score;
2. higher approved task count;
3. earlier timestamp of final approved submission.

Tie logic must live on the backend.

---

# 8. Task Model

Every task should support:

* id;
* event_id;
* title;
* description;
* instructions;
* points;
* proof_type;
* starts_at;
* expires_at;
* assignment_weight;
* max_assignments;
* active;
* metadata.

Task-specific metadata may include:

* required social platform;
* required phrase;
* required person;
* location description;
* target time;
* allowed time window;
* target account;
* required hashtag.

---

# 9. Random Task Rules

Random task selection must happen on the backend.

The algorithm must:

1. only choose active tasks;
2. respect task time windows;
3. avoid reassigning the exact same task to the same participant;
4. respect max assignment limits;
5. avoid assigning expired tasks;
6. create an immutable assignment record.

Random does not mean uncontrolled.

The system must be capable of later supporting weighted randomization.

For MVP:

weighted random selection is preferred but uniform random selection is acceptable if weight = 1 for all tasks.

---

# 10. Event Lifecycle

Supported states:

* draft;
* waiting;
* active;
* ended.

## Draft

Organizer prepares event.

## Waiting

QR entry is enabled.

Tasks are not active.

## Active

Tasks may be assigned and submitted.

## Ended

No new assignments or participant submissions.

Organizer review may continue.

---

# 11. Product Principles

## 11.1 Mobile First

The participant experience must be optimized for phones.

Primary target interaction:

scan QR → browser → participate.

No mobile app installation should be required for MVP.

---

## 11.2 Fast Interaction

Participants are physically attending an event.

The platform must not force them through long forms.

Every participant action should be short.

---

## 11.3 Proof-Oriented

The platform is based on verifiable participation.

Tasks must produce explicit submission records.

---

## 11.4 Organizer Controlled

The organizer determines:

* event;
* task pool;
* start time;
* deadline;
* points;
* validation.

---

# 12. MVP Screens

## Participant

1. QR landing page
2. Email verification page
3. Invalid email state
4. Waiting screen
5. Active task screen
6. Submission form
7. Submission pending screen/state
8. Submission rejected state
9. Task completed state
10. Leaderboard
11. My progress
12. Travel reimbursement upload
13. Event ended screen

## Organizer

1. Organizer login
2. Event dashboard
3. Participant list
4. Task management
5. Submission review
6. Leaderboard
7. Reimbursement requests
8. Competition controls

---

# 13. Organizer Dashboard Metrics

Minimum useful dashboard:

* total registered participants;
* total active participants;
* total assignments;
* total submissions;
* approved submissions;
* rejected submissions;
* tasks completed;
* current event state;
* time remaining;
* pending proof reviews;
* reimbursement requests.

---

# 14. Out of Scope Unless Explicitly Added

Agents must not independently add:

* complex AI systems;
* recommendation engines;
* NFT systems;
* social feeds;
* messaging;
* chat rooms;
* DAOs;
* token speculation;
* custom blockchain;
* unrelated gamification systems;
* avatars;
* unnecessary profile customization.

Build the approved product first.

---

# 15. Success Condition

A successful demo must show the following sequence:

1. Organizer creates/configures an event.
2. Participant scans event QR.
3. Participant enters an email and joins the waiting queue.
4. Participant enters waiting screen.
5. Organizer starts event.
6. Participant automatically receives a random task.
7. Participant submits proof.
8. Organizer sees submission.
9. Organizer approves it.
10. Participant score updates.
11. Leaderboard updates.
12. Participant receives another task.
13. Participant can upload a travel receipt.
14. Organizer can review that receipt.
15. Organizer ends event.
16. No further tasks can be assigned.

This full journey is the minimum product demo.
