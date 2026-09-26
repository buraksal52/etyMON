"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiRequest } from "../../../../../lib/api";

type Reimbursement = {
  id: string;
  amount: string | null;
  currency: string | null;
  transportType: string | null;
  description: string | null;
  status: string;
  receiptUrl: string;
  submittedAt: string;
  reviewNote: string | null;
  participant: {
    id: string;
    displayName: string | null;
    email: string;
  };
};

export default function ReimbursementReviewPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [reimbursements, setReimbursements] = useState<Reimbursement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadReimbursements = useCallback(async () => {
    try {
      const result = await apiRequest<{ reimbursements: Reimbursement[] }>(
        `/admin/events/${params.id}/reimbursements`,
      );
      setReimbursements(result.reimbursements);
      setError("");
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Unable to load reimbursements";
      setError(message);
      if (message.toLowerCase().includes("session")) {
        router.push(
          `/admin/login?next=/admin/events/${params.id}/reimbursements`,
        );
      }
    } finally {
      setLoading(false);
    }
  }, [params.id, router]);

  useEffect(() => {
    void loadReimbursements();
  }, [loadReimbursements]);

  async function review(id: string, decision: "APPROVED" | "REJECTED") {
    try {
      await apiRequest(`/admin/reimbursements/${id}/review`, {
        method: "POST",
        body: JSON.stringify({ decision, note: "" }),
      });
      await loadReimbursements();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to review reimbursement",
      );
    }
  }

  async function markPaid(id: string) {
    try {
      await apiRequest(`/admin/reimbursements/${id}/paid`, { method: "POST" });
      await loadReimbursements();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to mark reimbursement paid",
      );
    }
  }

  if (loading) {
    return (
      <main className="screen">
        <p>Loading reimbursements…</p>
      </main>
    );
  }

  return (
    <main className="screen admin-screen">
      <section className="admin-header">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1>Travel reimbursements</h1>
        </div>
        <button type="button" onClick={() => void loadReimbursements()}>
          Refresh
        </button>
      </section>
      {error && <p className="error">{error}</p>}
      {reimbursements.length === 0 && (
        <section className="card">
          <p>No reimbursement requests yet.</p>
        </section>
      )}
      <section className="submission-list">
        {reimbursements.map((reimbursement) => (
          <article className="card submission-card" key={reimbursement.id}>
            <div className="submission-meta">
              <div>
                <p className="eyebrow">{reimbursement.status}</p>
                <h2>
                  {reimbursement.participant.displayName ??
                    reimbursement.participant.email}
                </h2>
                <p>
                  {reimbursement.transportType ?? "Transport not specified"}
                </p>
              </div>
              <span className="points">
                {reimbursement.amount ?? "—"} {reimbursement.currency ?? ""}
              </span>
            </div>
            <p>
              Submitted {new Date(reimbursement.submittedAt).toLocaleString()}
            </p>
            {reimbursement.description && <p>{reimbursement.description}</p>}
            <a href={reimbursement.receiptUrl} target="_blank" rel="noreferrer">
              Open receipt
            </a>
            {reimbursement.status === "SUBMITTED" && (
              <div className="review-actions">
                <button
                  type="button"
                  onClick={() => void review(reimbursement.id, "APPROVED")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => void review(reimbursement.id, "REJECTED")}
                >
                  Reject
                </button>
              </div>
            )}
            {reimbursement.status === "APPROVED" && (
              <button
                type="button"
                onClick={() => void markPaid(reimbursement.id)}
              >
                Mark paid
              </button>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}
