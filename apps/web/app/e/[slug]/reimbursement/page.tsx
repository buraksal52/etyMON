"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { apiRequest } from "../../../../lib/api";

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
};

export default function ReimbursementPage() {
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");
  const [reimbursements, setReimbursements] = useState<Reimbursement[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("");
  const [transportType, setTransportType] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const loadReimbursements = useCallback(async () => {
    if (!eventId) {
      setError("Missing event session.");
      setLoading(false);
      return;
    }
    try {
      const result = await apiRequest<{ reimbursements: Reimbursement[] }>(
        `/events/${eventId}/reimbursements/me`,
      );
      setReimbursements(result.reimbursements);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load reimbursements",
      );
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void loadReimbursements();
  }, [loadReimbursements]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId || !file) {
      setError("A receipt file is required.");
      return;
    }
    setError("");
    setMessage("");
    setSubmitting(true);
    const formData = new FormData();
    formData.append("file", file);
    if (amount) formData.append("amount", amount);
    if (currency) formData.append("currency", currency);
    if (transportType) formData.append("transportType", transportType);
    if (description) formData.append("description", description);
    try {
      await apiRequest(`/events/${eventId}/reimbursements`, {
        method: "POST",
        body: formData,
      });
      setFile(null);
      setAmount("");
      setCurrency("");
      setTransportType("");
      setDescription("");
      setMessage("Receipt submitted for review.");
      await loadReimbursements();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to submit receipt",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="screen reimbursement-screen">
      <section className="card">
        <p className="eyebrow">TRAVEL REIMBURSEMENT</p>
        <h1>Submit travel receipt</h1>
        <form onSubmit={submit} className="proof-form">
          <label htmlFor="receipt">Receipt or invoice</label>
          <input
            id="receipt"
            type="file"
            accept="image/jpeg,image/png,image/webp,application/pdf"
            onChange={(inputEvent) =>
              setFile(inputEvent.target.files?.[0] ?? null)
            }
            required
          />
          <label htmlFor="amount">Amount (optional)</label>
          <input
            id="amount"
            type="number"
            min="0"
            step="0.01"
            value={amount}
            onChange={(inputEvent) => setAmount(inputEvent.target.value)}
          />
          <label htmlFor="currency">Currency (optional)</label>
          <input
            id="currency"
            maxLength={3}
            value={currency}
            onChange={(inputEvent) => setCurrency(inputEvent.target.value)}
            placeholder="EUR"
          />
          <label htmlFor="transportType">Transport type (optional)</label>
          <input
            id="transportType"
            value={transportType}
            onChange={(inputEvent) => setTransportType(inputEvent.target.value)}
            placeholder="Train"
          />
          <label htmlFor="description">Description (optional)</label>
          <textarea
            id="description"
            value={description}
            onChange={(inputEvent) => setDescription(inputEvent.target.value)}
          />
          <button type="submit" disabled={submitting}>
            {submitting ? "Submitting…" : "Submit receipt"}
          </button>
        </form>
        {error && <p className="error">{error}</p>}
        {message && <p className="success">{message}</p>}
      </section>
      <section className="card reimbursement-list">
        <h2>My reimbursement requests</h2>
        {loading && <p>Loading…</p>}
        {!loading && reimbursements.length === 0 && <p>No requests yet.</p>}
        {reimbursements.map((reimbursement) => (
          <article className="reimbursement-item" key={reimbursement.id}>
            <div>
              <strong>{reimbursement.status}</strong>
              <p>
                {reimbursement.amount ?? "Amount not provided"}{" "}
                {reimbursement.currency ?? ""}
              </p>
            </div>
            <a href={reimbursement.receiptUrl} target="_blank" rel="noreferrer">
              Open receipt
            </a>
            {reimbursement.reviewNote && <p>{reimbursement.reviewNote}</p>}
          </article>
        ))}
      </section>
    </main>
  );
}
