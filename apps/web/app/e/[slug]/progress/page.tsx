"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import { apiRequest } from "../../../../lib/api";

type Progress = {
  score: number;
  counts: Record<string, number>;
};

export default function ProgressPage() {
  const searchParams = useSearchParams();
  const eventId = searchParams.get("eventId");
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!eventId) {
      setError("Missing event session.");
      return;
    }
    apiRequest<Progress>(`/events/${eventId}/progress`)
      .then(setProgress)
      .catch((requestError: Error) => setError(requestError.message));
  }, [eventId]);

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
    </main>
  );
}
