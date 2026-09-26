"use client";

import Link from "next/link";
import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { apiRequest } from "../../../../lib/api";

type Dashboard = {
  event: { id: string; name: string; slug: string; state: string };
  metrics: Record<string, number>;
};

type EventQr = { url: string; svg: string };

export default function AdminEventDashboardPage() {
  const params = useParams<{ id: string }>();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [eventQr, setEventQr] = useState<EventQr | null>(null);
  const [error, setError] = useState("");
  const metricLabels: Record<string, string> = {
    registeredParticipants: "Registered participants",
    joinedParticipants: "Joined participants",
    waitingParticipants: "Waiting participants",
    activeParticipants: "Active participants",
    activeTasks: "Active tasks",
    totalAssignments: "Task assignments",
    totalSubmissions: "Submissions",
    approvedSubmissions: "Approved submissions",
  };

  const load = useCallback(async () => {
    try {
      setDashboard(await apiRequest<Dashboard>(`/admin/events/${params.id}`));
      setEventQr(await apiRequest<EventQr>(`/admin/events/${params.id}/qr`));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to load dashboard",
      );
    }
  }, [params.id]);

  useEffect(() => {
    void load();
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [load]);

  async function changeState(action: "start" | "end" | "publish") {
    try {
      if (action === "publish") {
        await apiRequest(`/admin/events/${params.id}`, {
          method: "PATCH",
          body: JSON.stringify({ state: "WAITING" }),
        });
      } else {
        await apiRequest(`/admin/events/${params.id}/${action}`, {
          method: "POST",
        });
      }
      await load();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Unable to update event",
      );
    }
  }

  if (!dashboard) {
    return (
      <main className="screen">
        <p>{error || "Loading dashboard…"}</p>
      </main>
    );
  }

  return (
    <main className="screen admin-screen">
      <section className="admin-header">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1>{dashboard.event.name}</h1>
          <p>State: {dashboard.event.state}</p>
        </div>
        <div className="admin-actions">
          {dashboard.event.state === "DRAFT" && (
            <button type="button" onClick={() => void changeState("publish")}>
              Publish
            </button>
          )}
          {dashboard.event.state === "WAITING" && (
            <button type="button" onClick={() => void changeState("start")}>
              Start
            </button>
          )}
          {dashboard.event.state === "ACTIVE" && (
            <button type="button" onClick={() => void changeState("end")}>
              End
            </button>
          )}
        </div>
      </section>
      {error && <p className="error">{error}</p>}
      <section className="metrics-grid">
        {Object.entries(dashboard.metrics).map(([key, value]) => (
          <article className="card metric-card" key={key}>
            <p className="eyebrow">{metricLabels[key] ?? key}</p>
            <strong>{value}</strong>
          </article>
        ))}
      </section>
      {eventQr && (
        <section className="card event-qr-card">
          <div>
            <p className="eyebrow">Participant entry</p>
            <h2>Event QR</h2>
            <p>
              Scan the QR code or enter this event code to join the waiting
              queue.
            </p>
            <p>
              <strong>Event code:</strong> <code>{dashboard.event.slug}</code>
            </p>
            <p>Participants verify their email after opening the event.</p>
            <code>{eventQr.url}</code>
          </div>
          <Image
            className="event-qr"
            src={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(eventQr.svg)}`}
            alt="Event entry QR code"
            width={160}
            height={160}
            unoptimized
          />
        </section>
      )}
      <nav className="admin-links">
        <Link href={`/admin/events/${params.id}/participants`}>
          Participants
        </Link>
        <Link href={`/admin/events/${params.id}/tasks`}>Tasks</Link>
        <Link href={`/admin/events/${params.id}/submissions`}>Submissions</Link>
        <Link href={`/admin/events/${params.id}/leaderboard`}>Leaderboard</Link>
        <Link href={`/admin/events/${params.id}/rewards`}>Rewards</Link>
        <Link href={`/admin/events/${params.id}/reimbursements`}>
          Reimbursements
        </Link>
      </nav>
    </main>
  );
}
