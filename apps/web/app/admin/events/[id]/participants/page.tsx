"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiRequest } from "../../../../../lib/api";

type Participant = {
  id: string;
  email: string;
  displayName: string | null;
  eligible: boolean;
  score: number;
};

export default function ParticipantListPage() {
  const params = useParams<{ id: string }>();
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    try {
      const result = await apiRequest<{ participants: Participant[] }>(
        `/admin/events/${params.id}/participants`,
      );
      setParticipants(result.participants);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load participants",
      );
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function importFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      const result = await apiRequest<{ imported: number; skipped: number }>(
        `/admin/events/${params.id}/participants/import`,
        { method: "POST", body: formData },
      );
      setMessage(`Imported ${result.imported}; skipped ${result.skipped}.`);
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to import participants",
      );
    }
  }

  return (
    <main className="screen admin-screen">
      <section className="card">
        <p className="eyebrow">Participant list</p>
        <h1>Import participants</h1>
        <p>CSV format: email,display_name</p>
        <input type="file" accept=".csv,text/csv" onChange={importFile} />
        {message && <p className="success">{message}</p>}
        {error && <p className="error">{error}</p>}
      </section>
      <section className="card participant-list">
        <h2>{participants.length} participants</h2>
        {participants.map((participant) => (
          <div className="participant-row" key={participant.id}>
            <div>
              <strong>{participant.displayName ?? participant.email}</strong>
              <p>{participant.email}</p>
            </div>
            <span>{participant.score} pts</span>
          </div>
        ))}
      </section>
    </main>
  );
}
