"use client";

import { useCallback, useEffect, useState } from "react";
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

  return (
    <main className="screen admin-screen">
      <section className="card">
        <p className="eyebrow">Live participant list</p>
        <h1>Participants join with QR or event code</h1>
        <p>New participants appear here after they enter the event code or scan the QR code.</p>
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
