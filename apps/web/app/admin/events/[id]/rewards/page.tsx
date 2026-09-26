"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { CopyButton } from "../../../../../components/copy-button";
import { apiRequest } from "../../../../../lib/api";

type Reward = {
  id: string;
  status: "PENDING" | "SUBMITTED" | "CONFIRMED" | "FAILED";
  amount: string;
  token: string;
  txHash: string | null;
  lastError: string | null;
  createdAt: string;
  confirmedAt: string | null;
  participant: {
    id: string;
    displayName: string | null;
    walletAddress: string | null;
  } | null;
  task: { id: string; title: string } | null;
};

const STATUS_LABEL: Record<Reward["status"], string> = {
  PENDING: "Waiting to send",
  SUBMITTED: "Sent, awaiting confirmation",
  CONFIRMED: "Paid",
  FAILED: "Failed",
};

function shorten(value: string): string {
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

export default function RewardSettlementsPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);

  const loadRewards = useCallback(async () => {
    try {
      const result = await apiRequest<{ rewards: Reward[] }>(
        `/admin/events/${params.id}/rewards`,
      );
      setRewards(result.rewards);
      setError("");
    } catch (requestError) {
      const message =
        requestError instanceof Error
          ? requestError.message
          : "Unable to load rewards";
      setError(message);
      if (message.toLowerCase().includes("session"))
        router.push(`/admin/login?next=/admin/events/${params.id}/rewards`);
    } finally {
      setLoading(false);
    }
  }, [params.id, router]);

  useEffect(() => {
    void loadRewards();
  }, [loadRewards]);

  async function retry(id: string) {
    setRetrying(id);
    try {
      const result = await apiRequest<{ reward: Reward }>(
        `/admin/rewards/${id}/retry`,
        { method: "POST" },
      );
      setRewards((old) =>
        old.map((reward) => (reward.id === id ? result.reward : reward)),
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to retry reward",
      );
    } finally {
      setRetrying(null);
    }
  }

  if (loading)
    return (
      <main className="screen">
        <p>Loading rewards…</p>
      </main>
    );

  const totals = rewards.reduce(
    (sum, reward) => {
      if (reward.status === "CONFIRMED") sum.paid += Number(reward.amount);
      else sum.open += Number(reward.amount);
      return sum;
    },
    { paid: 0, open: 0 },
  );

  return (
    <main className="screen admin-screen">
      <section className="admin-header">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1>Monad rewards</h1>
          <p>
            Paid {Number(totals.paid.toFixed(8))} MON · Not yet paid{" "}
            {Number(totals.open.toFixed(8))} MON
          </p>
        </div>
        <button type="button" onClick={() => void loadRewards()}>
          Refresh
        </button>
      </section>
      {error && <p className="error">{error}</p>}
      {rewards.length === 0 && (
        <section className="card">
          <p>
            No rewards yet. Rewards are created when a task with a MON reward is
            approved.
          </p>
        </section>
      )}
      <section className="submission-list">
        {rewards.map((reward) => (
          <article className="card submission-card" key={reward.id}>
            <div className="submission-meta">
              <div>
                <p className="eyebrow">{STATUS_LABEL[reward.status]}</p>
                <h2>{reward.task?.title ?? "Reward"}</h2>
                <p>
                  {reward.participant?.displayName ?? "Anonymous participant"}
                  {" · "}
                  {reward.participant?.walletAddress
                    ? shorten(reward.participant.walletAddress)
                    : "no wallet yet"}
                </p>
              </div>
              <span className="points">
                {Number(reward.amount)} {reward.token}
              </span>
            </div>
            <p>
              Approved {new Date(reward.createdAt).toLocaleString()}
              {reward.confirmedAt &&
                ` · Paid ${new Date(reward.confirmedAt).toLocaleString()}`}
            </p>
            {reward.lastError && reward.status !== "CONFIRMED" && (
              <p className="error">{reward.lastError}</p>
            )}
            {reward.txHash && (
              <p className="proof-value">
                Tx {shorten(reward.txHash)}{" "}
                <CopyButton value={reward.txHash} label="Copy tx hash" />
              </p>
            )}
            {reward.status !== "CONFIRMED" && (
              <div className="review-actions">
                <button
                  type="button"
                  disabled={retrying === reward.id}
                  onClick={() => void retry(reward.id)}
                >
                  {retrying === reward.id
                    ? "Working…"
                    : reward.status === "SUBMITTED"
                      ? "Check confirmation"
                      : "Retry payment"}
                </button>
              </div>
            )}
          </article>
        ))}
      </section>
    </main>
  );
}
