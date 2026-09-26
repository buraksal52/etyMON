"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

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

export default function TaskPage() {
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!eventId) {
      setError("Missing event session.");
      setLoading(false);
      return;
    }

    let active = true;
    async function loadTask() {
      try {
        const current = await apiRequest<{ assignment: Assignment | null }>(
          `/events/${eventId}/tasks/current`,
        );
        if (current.assignment) {
          if (active) setAssignment(current.assignment);
          return;
        }
        const next = await apiRequest<{ assignment: Assignment }>(
          `/events/${eventId}/tasks/next`,
          {
            method: "POST",
          },
        );
        if (active) setAssignment(next.assignment);
      } catch (requestError) {
        if (active)
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to load task",
          );
      } finally {
        if (active) setLoading(false);
      }
    }

    void loadTask();
    return () => {
      active = false;
    };
  }, [eventId]);

  if (loading)
    return (
      <main className="screen">
        <p>Loading task…</p>
      </main>
    );
  if (error)
    return (
      <main className="screen">
        <section className="card">
          <p className="error">{error}</p>
        </section>
      </main>
    );
  if (!assignment)
    return (
      <main className="screen">
        <section className="card">
          <h1>No task available</h1>
          <p>Check back shortly.</p>
        </section>
      </main>
    );

  const { task } = assignment;
  return (
    <main className="screen">
      <section className="card task-card">
        <p className="eyebrow">ACTIVE TASK</p>
        <div className="task-heading">
          <h1>{task.title}</h1>
          <span className="points">+{task.points} pts</span>
        </div>
        <p>{task.description}</p>
        <div className="instructions">
          <strong>Instructions</strong>
          <p>{task.instructions}</p>
        </div>
        <p className="proof-type">Required proof: {task.proofType}</p>
        <ProofForm
          proofType={task.proofType}
          onSubmit={() =>
            setMessage(
              "Proof is ready to submit; upload processing is added in Phase 7.",
            )
          }
        />
        {message && <p className="success">{message}</p>}
      </section>
    </main>
  );
}
