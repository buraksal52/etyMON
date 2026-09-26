"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { EntrySuccess } from "../../../components/entry-success";

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
  const [joinedEventId, setJoinedEventId] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    setLoading(true);
    setError("");
    apiRequest<EventInfo>(`/events/${params.slug}`)
      .then(setEvent)
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, [params.slug, retry]);

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
      setJoinedEventId(result.eventId);
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

  useEffect(() => {
    if (!joinedEventId) return;
    router.prefetch(
      `/e/${params.slug}/waiting?eventId=${encodeURIComponent(joinedEventId)}`,
    );
    const timer = window.setTimeout(() => {
      router.replace(
        `/e/${params.slug}/waiting?eventId=${encodeURIComponent(joinedEventId)}`,
      );
    }, 3500);
    return () => window.clearTimeout(timer);
  }, [joinedEventId, params.slug, router]);

  if (joinedEventId) return <EntrySuccess />;

  if (loading && !event)
    return (
      <main className="screen">
        <p>Loading event…</p>
      </main>
    );
  if (!event)
    return (
      <main className="screen">
        <section className="card">
          <h1>Unable to load the event</h1>
          <p role="alert">
            {error === "Failed to fetch" || error === "Load failed"
              ? "Could not connect to the event server. Please try again shortly."
              : error || "Event not found"}
          </p>
          <button type="button" onClick={() => setRetry((value) => value + 1)}>
            Try again
          </button>
          <a href="/room">Back to event code</a>
        </section>
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
