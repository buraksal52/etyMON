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
    <main className="screen">
      <section className="card leaderboard-card">
        <p className="eyebrow">Progress</p>
        <h1>Leaderboard</h1>
        {error ? (
          <p className="error">{error}</p>
        ) : (
          <LeaderboardTable rows={rows} />
        )}
      </section>
    </main>
  );
}
