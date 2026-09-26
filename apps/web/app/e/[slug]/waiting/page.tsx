"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import { apiRequest } from "../../../../lib/api";

type EventStatus = {
  state: "DRAFT" | "WAITING" | "ACTIVE" | "ENDED";
};

export default function WaitingPage() {
  const params = useParams<{ slug: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const eventId = searchParams.get("eventId");
  const [status, setStatus] = useState<EventStatus["state"]>("WAITING");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!eventId) {
      setError("Missing event session.");
      return;
    }

    let active = true;
    const checkStatus = async () => {
      try {
        const result = await apiRequest<EventStatus>(
          `/events/${eventId}/status`,
        );
        if (!active) return;
        setStatus(result.state);
        if (result.state === "ACTIVE") router.push(`/e/${params.slug}/task`);
        if (result.state === "ENDED") router.push(`/e/${params.slug}/ended`);
      } catch (requestError) {
        if (active)
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Unable to read event status",
          );
      }
    };

    void checkStatus();
    const interval = window.setInterval(checkStatus, 4000);
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [eventId, params.slug, router]);

  return (
    <main className="screen">
      <section className="card waiting-card">
        <p className="eyebrow">{status}</p>
        <h1>You’re checked in</h1>
        <p>Waiting for Port to start the competition.</p>
        <span className="status-dot" aria-label="Checking event status" />
        {error && <p className="error">{error}</p>}
      </section>
    </main>
  );
}
