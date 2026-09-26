"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiRequest } from "../../../../../lib/api";

type Submission = {
  id: string;
  status: string;
  participant: { displayName: string | null; id: string };
  task: { title: string; points: number };
  proof: {
    text: string | null;
    url: string | null;
    storageKey: string | null;
    downloadUrl: string | null;
  };
  submittedAt: string;
  reviewNote: string | null;
};

export default function SubmissionReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadSubmissions = useCallback(async () => {
    try {
      const result = await apiRequest<{ submissions: Submission[] }>(
        `/admin/events/${params.id}/submissions`,
      );
      setSubmissions(result.submissions);
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Unable to load submissions";
      setError(message);
      if (message.toLowerCase().includes("session"))
        router.push(`/admin/login?next=/admin/events/${params.id}/submissions`);
    } finally {
      setLoading(false);
    }
  }, [params.id, router]);

  useEffect(() => {
    void loadSubmissions();
  }, [loadSubmissions]);

  async function review(id: string, decision: "APPROVED" | "REJECTED") {
    await apiRequest(`/admin/submissions/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ decision, note: "" }),
    });
    await loadSubmissions();
  }

  if (loading)
    return (
      <main className="screen">
        <p>Loading submissions…</p>
      </main>
    );

  return (
    <main className="screen admin-screen">
      <section className="admin-header">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1>Submission review</h1>
        </div>
        <button type="button" onClick={() => void loadSubmissions()}>
          Refresh
        </button>
      </section>
      {error && <p className="error">{error}</p>}
      {submissions.length === 0 && (
        <section className="card">
          <p>No submissions yet.</p>
        </section>
      )}
      <section className="submission-list">
        {submissions.map((submission) => (
          <article className="card submission-card" key={submission.id}>
            <div className="submission-meta">
              <div>
                <p className="eyebrow">{submission.status}</p>
                <h2>{submission.task.title}</h2>
                <p>
                  {submission.participant.displayName ??
                    "Anonymous participant"}
                </p>
              </div>
              <span className="points">+{submission.task.points} pts</span>
            </div>
            <p>Submitted {new Date(submission.submittedAt).toLocaleString()}</p>
            {submission.proof.text && (
              <p className="proof-value">{submission.proof.text}</p>
            )}
            {submission.proof.url && (
              <a href={submission.proof.url} target="_blank" rel="noreferrer">
                Open submitted URL
              </a>
            )}
            {submission.proof.downloadUrl && (
              <a
                href={submission.proof.downloadUrl}
                target="_blank"
                rel="noreferrer"
              >
                Open uploaded proof
              </a>
            )}
            {submission.status === "PENDING" && (
              <div className="review-actions">
                <button
                  type="button"
                  onClick={() => void review(submission.id, "APPROVED")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => void review(submission.id, "REJECTED")}
                >
                  Reject
                </button>
              </div>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}
