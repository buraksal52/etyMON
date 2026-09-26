"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ProofForm } from "../../../../components/proof-form";
import { apiRequest } from "../../../../lib/api";

type Assignment = {
  id: string;
  status: string;
  task: {
    title: string;
    description: string;
    instructions: string;
    points: number;
    proofType: string;
  };
};
type Session = {
  assignment: Assignment | null;
  lastAssignment: Assignment | null;
  missionNumber: number;
  completed: number;
  pythonQuestion?: string | null;
};
const emptySession: Session = {
  assignment: null,
  lastAssignment: null,
  missionNumber: 1,
  completed: 0,
};

export default function TaskPage() {
  const { slug } = useParams<{ slug: string }>();
  const eventId = useSearchParams().get("eventId");
  const [session, setSession] = useState<Session>(emptySession);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [spinning, setSpinning] = useState(false);
  const [rotation, setRotation] = useState(0);
  const [selected, setSelected] = useState(false);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const locked = useRef(false);
  const assignment = session.assignment;
  const approved = session.lastAssignment?.status === "APPROVED";
  const finished = session.completed >= 3;

  useEffect(() => {
    let active = true;
    async function refresh(initial = false) {
      if (!eventId) {
        setLoading(false);
        return;
      }
      try {
        const result = await apiRequest<Session>(
          `/events/${eventId}/tasks/current`,
        );
        if (active) {
          setSession(result);
          if (initial) setError("");
        }
      } catch (cause) {
        if (active)
          setError(
            cause instanceof Error ? cause.message : "Unable to load mission.",
          );
      } finally {
        if (active) setLoading(false);
      }
    }
    void refresh(true);
    const interval = setInterval(() => {
      if (!locked.current) void refresh();
    }, 4000);
    return () => {
      active = false;
      clearInterval(interval);
      if (timer.current) clearTimeout(timer.current);
    };
  }, [eventId]);

  async function spin() {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setError("");
    try {
      let next: Assignment | null = null;
      if (eventId) {
        try {
          const result = await apiRequest<{ assignment: Assignment }>(
            `/events/${eventId}/tasks/next`,
            { method: "POST", body: JSON.stringify({ answer }) },
          );
          next = result.assignment;
        } catch (cause) {
          if (
            !(cause instanceof Error) ||
            cause.message !== "No task is currently available" ||
            approved
          )
            throw cause;
        }
      }
      setSpinning(true);
      const number = approved ? session.missionNumber + 1 : 1;
      setRotation(
        (old) =>
          old + 1440 + ((360 - (number - 1) * 120 - (old % 360) + 360) % 360),
      );
      timer.current = setTimeout(
        () => {
          setSelected(true);
          if (next)
            setSession((old) => ({
              ...old,
              assignment: next,
              lastAssignment: null,
              missionNumber: number,
              pythonQuestion: null,
            }));
          setAnswer("");
          setSpinning(false);
          setBusy(false);
          locked.current = false;
        },
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : 2600,
      );
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to select mission.",
      );
      setBusy(false);
      locked.current = false;
    }
  }

  async function submitProof(proof: {
    file?: File;
    text?: string;
    url?: string;
  }) {
    if (!assignment || locked.current) return;
    locked.current = true;
    setBusy(true);
    setError("");
    const body = new FormData();
    if (proof.file) body.append("file", proof.file);
    if (proof.text) body.append("text", proof.text);
    if (proof.url) body.append("url", proof.url);
    try {
      await apiRequest(`/assignments/${assignment.id}/submit`, {
        method: "POST",
        body,
      });
      setSession((old) => ({
        ...old,
        assignment: { ...assignment, status: "SUBMITTED" },
      }));
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Unable to submit proof.",
      );
    } finally {
      setBusy(false);
      locked.current = false;
    }
  }

  return (
    <main className="mission-terminal">
      <header className="mission-hero">
        <div>
          <h1>
            SPIN.
            <br />
            <span>UNLOCK.</span>
          </h1>
          <p>Three missions. One at a time.</p>
        </div>
        <ol className="mission-steps" aria-label="Mission progress">
          {[1, 2, 3].map((number) => (
            <li
              key={number}
              aria-current={
                number === session.missionNumber ? "step" : undefined
              }
              className={number <= session.completed ? "is-complete" : ""}
            >
              {number <= session.completed ? "✓" : `0${number}`}
            </li>
          ))}
        </ol>
      </header>
      <div className="mission-grid">
        <section
          className="mission-panel selector-panel"
          aria-label="Task selector"
        >
          <div className="mission-wheel-wrap">
            <div
              className="mission-wheel"
              role="img"
              aria-label="Mission wheel with three numbered sectors"
              style={{ transform: `rotate(${rotation}deg)` }}
            />
          </div>
          <button
            onClick={() => void spin()}
            disabled={
              loading || busy || !!assignment || !!session.lastAssignment
            }
          >
            {spinning
              ? "SELECTING…"
              : assignment || session.lastAssignment
                ? "MISSION SELECTED"
                : "SPIN THE WHEEL ↗"}
          </button>
          <p className="mission-hint">
            Complete your mission. Solve Python. Unlock the next.
          </p>
        </section>
        <section
          className="mission-panel"
          aria-live="polite"
          aria-busy={loading || busy}
        >
          <div className="mission-panel-title">
            <span>YOUR CURRENT MISSION</span>
            <span>0{session.missionNumber} / 03</span>
          </div>
          {loading ? (
            <h2>Loading mission…</h2>
          ) : finished ? (
            <>
              <p className="mission-kicker">03 / 03 COMPLETE</p>
              <h2>All missions complete.</h2>
              <p>You made it through all three missions.</p>
            </>
          ) : assignment ? (
            <>
              <p className="mission-kicker">
                TASK 0{session.missionNumber} · +{assignment.task.points} PTS
              </p>
              <h2>{assignment.task.title}</h2>
              <p>{assignment.task.description}</p>
              <p className="mission-instructions">
                {assignment.task.instructions}
              </p>
              {assignment.status === "SUBMITTED" ? (
                <p className="mission-notice">
                  Proof submitted. Waiting for organizer approval.
                </p>
              ) : (
                <ProofForm
                  key={assignment.id}
                  proofType={assignment.task.proofType}
                  onSubmit={submitProof}
                  disabled={busy}
                />
              )}
            </>
          ) : approved ? (
            <>
              <p className="mission-kicker">TASK APPROVED ✓</p>
              <h2>Unlock mission 0{session.missionNumber + 1}.</h2>
              <p>Solve a Python question to continue.</p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  void spin();
                }}
              >
                <label htmlFor="python-answer">PYTHON // ACCESS CHECK</label>
                <pre className="mission-code">
                  {session.pythonQuestion || "Python question coming soon."}
                </pre>
                <textarea
                  id="python-answer"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  disabled={!session.pythonQuestion || busy}
                  placeholder="Your answer"
                  required
                  maxLength={2000}
                />
                <button
                  disabled={!session.pythonQuestion || busy || !answer.trim()}
                >
                  {spinning ? "UNLOCKING…" : "CHECK ANSWER & UNLOCK →"}
                </button>
              </form>
            </>
          ) : session.lastAssignment ? (
            <>
              <p className="mission-kicker">MISSION LOCKED</p>
              <h2>
                {session.lastAssignment.status === "REJECTED"
                  ? "Proof not approved."
                  : "Mission expired."}
              </h2>
              <p>
                The next mission stays locked. Contact the organizer for review.
              </p>
            </>
          ) : (
            <>
              <p className="mission-kicker">TASK 01</p>
              <h2>
                {selected ? "Mission details coming soon." : "Your first move."}
              </h2>
              <p>
                {selected
                  ? "The organizer will add the task here."
                  : "Spin the wheel to reveal your first mission."}
              </p>
              <fieldset disabled className="mission-placeholder">
                <label htmlFor="future-proof">UPLOAD YOUR PROOF</label>
                <input id="future-proof" type="file" />
                <p className="mission-hint">
                  Proof submission opens when a mission is available.
                </p>
                <button>SUBMIT PROOF</button>
              </fieldset>
            </>
          )}
          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}
        </section>
      </div>
      {eventId && (
        <nav className="mission-links">
          <Link
            href={`/e/${slug}/progress?eventId=${encodeURIComponent(eventId)}`}
          >
            My progress ↗
          </Link>
          <Link
            href={`/e/${slug}/leaderboard?eventId=${encodeURIComponent(eventId)}`}
          >
            Leaderboard ↗
          </Link>
        </nav>
      )}
    </main>
  );
}
