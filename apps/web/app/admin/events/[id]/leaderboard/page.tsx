"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { LeaderboardTable } from "../../../../../components/leaderboard-table";
import { apiRequest } from "../../../../../lib/api";

type Row = {
  rank: number;
  participant: string;
  score: number;
  approvedTasks: number;
};

export default function AdminLeaderboardPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [rows, setRows] = useState<Row[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<{ leaderboard: Row[] }>(`/admin/events/${params.id}/leaderboard`)
      .then((result) => setRows(result.leaderboard))
      .catch((requestError: Error) => {
        setError(requestError.message);
        if (requestError.message.toLowerCase().includes("session")) {
          router.push(
            `/admin/login?next=/admin/events/${params.id}/leaderboard`,
          );
        }
      });
  }, [params.id, router]);

  return (
    <main className="screen">
      <section className="card leaderboard-card">
        <p className="eyebrow">Organizer dashboard</p>
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
