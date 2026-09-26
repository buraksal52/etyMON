"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { apiRequest } from "../../../../lib/api";

type Progress = {
  score: number;
  counts: Record<string, number>;
};

type Me = {
  participant: { displayName: string | null; walletAddress: string | null };
};

type Reward = {
  id: string;
  status: "PENDING" | "SUBMITTED" | "CONFIRMED" | "FAILED";
  amount: string;
  token: string;
  task: { title: string } | null;
};

// Participants never deal with gas or tx hashes; only whether they got paid.
const REWARD_STATUS: Record<Reward["status"], string> = {
  PENDING: "Waiting",
  SUBMITTED: "Sending",
  CONFIRMED: "Paid",
  FAILED: "Delayed — organizer will retry",
};

const WALLET_PATTERN = /^0x[0-9a-fA-F]{40}$/;

export default function ProgressPage() {
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");
  const [progress, setProgress] = useState<Progress | null>(null);
  const [wallet, setWallet] = useState<string | null>(null);
  const [walletInput, setWalletInput] = useState("");
  const [walletMessage, setWalletMessage] = useState("");
  const [savingWallet, setSavingWallet] = useState(false);
  const [rewards, setRewards] = useState<Reward[]>([]);
  const [error, setError] = useState("");

  const loadRewards = useCallback(async () => {
    if (!eventId) return;
    const result = await apiRequest<{ rewards: Reward[] }>(
      `/events/${eventId}/rewards`,
    );
    setRewards(result.rewards);
  }, [eventId]);

  useEffect(() => {
    if (!eventId) {
      setError("Missing event session.");
      return;
    }
    apiRequest<Progress>(`/events/${eventId}/progress`)
      .then(setProgress)
      .catch((requestError: Error) => setError(requestError.message));
    apiRequest<Me>(`/events/${eventId}/me`)
      .then((me) => setWallet(me.participant.walletAddress))
      .catch(() => undefined);
    loadRewards().catch(() => undefined);
  }, [eventId, loadRewards]);

  async function saveWallet(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = walletInput.trim();
    if (!WALLET_PATTERN.test(value)) {
      setWalletMessage("Enter a valid wallet address (0x + 40 characters).");
      return;
    }
    setSavingWallet(true);
    setWalletMessage("");
    try {
      const result = await apiRequest<{ walletAddress: string }>(
        `/events/${eventId}/wallet`,
        {
          method: "PUT",
          body: JSON.stringify({ walletAddress: value }),
        },
      );
      setWallet(result.walletAddress);
      setWalletInput("");
      setWalletMessage("Wallet saved. Rewards will be sent here.");
      await loadRewards();
    } catch (requestError) {
      setWalletMessage(
        requestError instanceof Error
          ? requestError.message
          : "Unable to save wallet",
      );
    } finally {
      setSavingWallet(false);
    }
  }

  const waitingForWallet =
    !wallet && rewards.some((reward) => reward.status !== "CONFIRMED");

  return (
    <main className="screen">
      <section className="card progress-card">
        <p className="eyebrow">MY PROGRESS</p>
        {error && <p className="error">{error}</p>}
        {progress && (
          <>
            <h1>{progress.score} points</h1>
            <div className="progress-list">
              {Object.entries(progress.counts).map(([key, value]) => (
                <p key={key}>
                  <strong>{value}</strong> {key}
                </p>
              ))}
            </div>
          </>
        )}
      </section>
      {eventId && !error && (
        <section className="card progress-card">
          <p className="eyebrow">MON REWARDS</p>
          {rewards.length === 0 ? (
            <p>Approved missions with a MON reward will appear here.</p>
          ) : (
            <div className="progress-list">
              {rewards.map((reward) => (
                <p key={reward.id}>
                  <strong>
                    {Number(reward.amount)} {reward.token}
                  </strong>{" "}
                  {reward.task?.title ?? "Reward"} ·{" "}
                  {REWARD_STATUS[reward.status]}
                </p>
              ))}
            </div>
          )}
          {waitingForWallet && (
            <p className="error">
              Add your wallet to receive your pending rewards.
            </p>
          )}
          {wallet && (
            <p>
              Paying to{" "}
              <strong>
                {wallet.slice(0, 6)}…{wallet.slice(-4)}
              </strong>
            </p>
          )}
          <form onSubmit={saveWallet} className="proof-form">
            <label htmlFor="wallet-address">
              {wallet ? "Change wallet" : "Monad wallet address"}
            </label>
            <input
              id="wallet-address"
              value={walletInput}
              onChange={(event) => setWalletInput(event.target.value)}
              placeholder="0x…"
              autoComplete="off"
              spellCheck={false}
            />
            <button
              type="submit"
              disabled={savingWallet || !walletInput.trim()}
            >
              {savingWallet ? "Saving…" : "Save wallet"}
            </button>
          </form>
          {walletMessage && <p>{walletMessage}</p>}
        </section>
      )}
    </main>
  );
}
