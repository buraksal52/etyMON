"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { apiRequest } from "../../../../lib/api";

export default function NewEventPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [timezone, setTimezone] = useState("event-local");
  const [deadline, setDeadline] = useState("");
  const [error, setError] = useState("");

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      const result = await apiRequest<{ event: { id: string } }>(
        "/admin/events",
        {
          method: "POST",
          body: JSON.stringify({
            name,
            slug,
            timezone,
            task_deadline_at: new Date(deadline).toISOString(),
          }),
        },
      );
      router.push(`/admin/events/${result.event.id}`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to create event",
      );
    }
  }

  return (
    <main className="screen">
      <section className="card">
        <p className="eyebrow">Event setup</p>
        <h1>Create event</h1>
        <form onSubmit={create} className="proof-form">
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Event name"
            required
          />
          <input
            value={slug}
            onChange={(event) => setSlug(event.target.value)}
            placeholder="event-slug"
            pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
            required
          />
          <input
            value={timezone}
            onChange={(event) => setTimezone(event.target.value)}
            placeholder="Timezone"
            required
          />
          <label htmlFor="deadline">Task deadline</label>
          <input
            id="deadline"
            type="datetime-local"
            value={deadline}
            onChange={(event) => setDeadline(event.target.value)}
            required
          />
          <button type="submit">Create event</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>
    </main>
  );
}
