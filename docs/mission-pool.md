# MVP mission pool

The participant flow has three stages. Identity NEXT opens the mission terminal.
Tasks are assigned only on a wheel spin. Approval by an organizer is required
before answering the Python question to unlock the next mission. Three approved
missions finish the flow. Rejected or expired missions do not unlock progression.

Content is intentionally unconfigured. Existing tasks without `missionStage`
are excluded. Add tasks through the existing organizer task API and set their
`metadata` to include:

- `missionStage`: 1, 2, or 3. Populate progressively harder pools per stage.
- `pythonGate`: `{ "prompt": "", "answers": [] }` for stages 1 and 2.
  Fill in the Python question and accepted answer strings when content is ready.
  These are short answer/output questions; submitted code is never executed.
  Answers are matched on the server, case-sensitive, with outer whitespace removed.

The API hides `pythonGate` from participant task metadata and exposes only its
prompt after approval. Empty prompts/answers keep the next stage locked.
No sample mission or question content is seeded by this change.
