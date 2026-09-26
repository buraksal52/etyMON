"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiRequest } from "../../lib/api";

type Event = { id: string; name: string; slug: string; state: string };

export default function AdminHomePage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<{ events: Event[] }>("/admin/events")
      .then((result) => setEvents(result.events))
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  return (
    <main className="screen admin-screen">
      <section className="admin-header">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1>Events</h1>
        </div>
        <Link className="admin-link-button" href="/admin/events/new">
          Create event
        </Link>
      </section>
      {error && <p className="error">{error}</p>}
      <section className="submission-list">
        {events.map((event) => (
          <Link
            className="card event-link-card"
            href={`/admin/events/${event.id}`}
            key={event.id}
          >
            <p className="eyebrow">{event.state}</p>
            <h2>{event.name}</h2>
            <p>{event.slug}</p>
          </Link>
        ))}
      </section>
    </main>
  );
}
