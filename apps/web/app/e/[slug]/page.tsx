"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { apiRequest } from "../../../lib/api";

type EventInfo = {
  id: string;
  name: string;
  description: string | null;
  state: string;
};

export default function EventEntryPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const [event, setEvent] = useState<EventInfo | null>(null);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiRequest<EventInfo>(`/events/${params.slug}`)
      .then(setEvent)
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, [params.slug]);

  async function handleSubmit(submitEvent: FormEvent<HTMLFormElement>) {
    submitEvent.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await apiRequest<{ eventId: string }>(
        `/events/${params.slug}/join`,
        {
          method: "POST",
          body: JSON.stringify({ email }),
        },
      );
      router.push(`/e/${params.slug}/waiting?eventId=${result.eventId}`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to join event",
      );
    } finally {
      setLoading(false);
    }
  }

  if (loading && !event)
    return (
      <main className="screen">
        <p>Loading event…</p>
      </main>
    );
  if (!event)
    return (
      <main className="screen">
        <p>{error || "Event not found"}</p>
      </main>
    );

  return (
    <main className="screen">
      <section className="card">
      <p className="eyebrow">Platform event</p>
        <h1>{event.name}</h1>
        <p>
          {event.description ?? "Enter your email to join the event queue."}
        </p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(inputEvent) => setEmail(inputEvent.target.value)}
            placeholder="you@example.com"
            required
          />
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={loading}>
            {loading ? "Checking…" : "Join event"}
          </button>
        </form>
      </section>
    </main>
  );
}
