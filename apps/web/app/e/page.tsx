"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function EventCodeEntryPage() {
  const router = useRouter();
  const [code, setCode] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const normalizedCode = code.trim().toLowerCase();
    if (normalizedCode) router.push(`/e/${encodeURIComponent(normalizedCode)}`);
  }

  return (
    <main className="screen">
      <section className="card">
        <p className="eyebrow">Join event</p>
        <h1>Enter event code</h1>
        <p>Use the code shown by the organizer or scan the event QR code.</p>
        <form className="stack" onSubmit={submit}>
          <label htmlFor="event-code">Event code</label>
          <input
            id="event-code"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="event-code"
            autoCapitalize="none"
            required
          />
          <button type="submit">Continue</button>
        </form>
      </section>
    </main>
  );
}
