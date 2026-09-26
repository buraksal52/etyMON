"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";

import { LeaderboardTable } from "../../../../components/leaderboard-table";
import { apiRequest } from "../../../../lib/api";

type Row = {
  rank: number;
  participant: string;
  score: number;
  approvedTasks: number;
};

export default function ParticipantLeaderboardPage() {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!eventId) {
      setError("Missing event session.");
      return;
    }
    apiRequest<{ leaderboard: Row[] }>(`/events/${eventId}/leaderboard`)
      .then((result) => setRows(result.leaderboard))
      .catch((requestError: Error) => setError(requestError.message));
  }, [eventId, params.slug]);

  return (
    <main className="screen leaderboard-screen">
      <section className="card leaderboard-card leaderboard-terminal">
        <header className="leaderboard-titlebar">
          <span className="leaderboard-prompt" aria-hidden="true">
            &gt;_
          </span>
          <span>leaderboard.txt</span>
          <span className="leaderboard-window-icons" aria-hidden="true">
            − □ ×
          </span>
        </header>
        <div className="leaderboard-terminal-content">
          <h1>
            <span>Progress</span>
            <em>Leaderboard.</em>
          </h1>
          {error ? (
            <p className="error">{error}</p>
          ) : (
            <LeaderboardTable rows={rows} />
          )}
        </div>
      </section>
    </main>
  );
}
