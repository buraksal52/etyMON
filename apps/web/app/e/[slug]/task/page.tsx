"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { ProofForm } from "../../../../components/proof-form";
import { apiRequest } from "../../../../lib/api";

type Assignment = {
  id: string;
  status: string;
  assignedAt?: string;
  task: {
    title: string;
    description: string;
    instructions: string;
    points: number;
    proofType: string;
  };
};

export default function TaskPage() {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [resolvedAssignment, setResolvedAssignment] =
    useState<Assignment | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [awaitingReview, setAwaitingReview] = useState(false);
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
        const current = await apiRequest<{
          assignment: Assignment | null;
          lastAssignment: Assignment | null;
        }>(`/events/${eventId}/tasks/current`);
        if (current.assignment) {
          if (active) {
            setAssignment(current.assignment);
            setResolvedAssignment(null);
            setAwaitingReview(current.assignment.status === "SUBMITTED");
          }
          return;
        }
        if (current.lastAssignment) {
          if (active) {
            setAssignment(null);
            setResolvedAssignment(current.lastAssignment);
            setAwaitingReview(false);
          }
          return;
        }
        const next = await apiRequest<{ assignment: Assignment }>(
          `/events/${eventId}/tasks/next`,
          {
            method: "POST",
          },
        );
        if (active) {
          setAssignment(next.assignment);
          setResolvedAssignment(null);
          setAwaitingReview(false);
        }
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

  useEffect(() => {
    if (!eventId || !awaitingReview) return;

    let active = true;
    const interval = window.setInterval(async () => {
      try {
        const current = await apiRequest<{
          assignment: Assignment | null;
          lastAssignment: Assignment | null;
        }>(`/events/${eventId}/tasks/current`);
        if (!active) return;
        if (current.assignment) {
          setAssignment(current.assignment);
          if (current.assignment.status !== "SUBMITTED") {
            setAwaitingReview(false);
          }
          return;
        }
        if (current.lastAssignment) {
          setAssignment(null);
          setResolvedAssignment(current.lastAssignment);
          setAwaitingReview(false);
        }
      } catch (requestError) {
        if (active) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to refresh task status",
          );
        }
      }
    }, 4000);

    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [eventId, awaitingReview]);

  async function requestNextTask() {
    if (!eventId) return;
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const next = await apiRequest<{ assignment: Assignment }>(
        `/events/${eventId}/tasks/next`,
        { method: "POST" },
      );
      setAssignment(next.assignment);
      setResolvedAssignment(null);
      setAwaitingReview(false);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load next task",
      );
    } finally {
      setLoading(false);
    }
  }

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
  if (resolvedAssignment)
    return (
      <main className="screen">
        <section className="card review-card">
          <p className="eyebrow">TASK REVIEW</p>
          <h1>
            {resolvedAssignment.status === "APPROVED"
              ? "Task approved"
              : "Task rejected"}
          </h1>
          {resolvedAssignment.status === "APPROVED" ? (
            <p className="success">
              +{resolvedAssignment.task.points} points added to your score.
            </p>
          ) : (
            <p>Your proof was not approved. You can try another task.</p>
          )}
          <button type="button" onClick={requestNextTask}>
            Next Task
          </button>
          {error && <p className="error">{error}</p>}
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

  const currentAssignment = assignment;
  const { task } = currentAssignment;
  async function submitProof(proof: {
    file?: File;
    text?: string;
    url?: string;
  }) {
    if (!eventId) return;
    setError("");
    setMessage("");
    setSubmitting(true);
    const formData = new FormData();
    if (proof.file) formData.append("file", proof.file);
    if (proof.text) formData.append("text", proof.text);
    if (proof.url) formData.append("url", proof.url);
    try {
      await apiRequest(`/assignments/${currentAssignment.id}/submit`, {
        method: "POST",
        body: formData,
      });
      setAssignment({ ...currentAssignment, status: "SUBMITTED" });
      setAwaitingReview(true);
      setMessage("Proof submitted. Waiting for organizer review.");
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to submit proof",
      );
    } finally {
      setSubmitting(false);
    }
  }

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
          onSubmit={submitProof}
          disabled={submitting || currentAssignment.status !== "ASSIGNED"}
        />
        {error && <p className="error">{error}</p>}
        {message && <p className="success">{message}</p>}
      </section>
      <nav className="participant-links">
        <Link href={`/e/${params.slug}/progress?eventId=${eventId}`}>
          My progress
        </Link>
        <Link href={`/e/${params.slug}/leaderboard?eventId=${eventId}`}>
          Leaderboard
        </Link>
        <Link href={`/e/${params.slug}/reimbursement?eventId=${eventId}`}>
          Travel reimbursement
        </Link>
      </nav>
    </main>
  );
}
