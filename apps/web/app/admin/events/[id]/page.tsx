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

type MetricGroup = {
  title: string;
  metrics: { key: string; label: string; highlight?: boolean }[];
};

const METRIC_GROUPS: MetricGroup[] = [
  {
    title: "Participants",
    metrics: [
      { key: "registeredParticipants", label: "Registered" },
      { key: "joinedParticipants", label: "Joined" },
      { key: "waitingParticipants", label: "In waiting room" },
      { key: "activeParticipants", label: "Playing now" },
    ],
  },
  {
    title: "Tasks & reviews",
    metrics: [
      { key: "activeTasks", label: "Active tasks" },
      { key: "totalAssignments", label: "Assigned" },
      { key: "totalSubmissions", label: "Submitted" },
      {
        key: "pendingProofReviews",
        label: "Waiting for review",
        highlight: true,
      },
      { key: "approvedSubmissions", label: "Approved" },
      { key: "rejectedSubmissions", label: "Rejected" },
      { key: "reimbursementRequests", label: "Reimbursements" },
    ],
  },
];

const STATE_LABEL: Record<string, string> = {
  DRAFT: "Draft",
  WAITING: "Waiting room open",
  ACTIVE: "Live",
  ENDED: "Ended",
};

function formatRemaining(seconds: number): string {
  if (seconds <= 0) return "Deadline passed";
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h left`;
  if (hours > 0) return `${hours}h ${minutes}m left`;
  return `${Math.max(1, minutes)}m left`;
}

export default function AdminEventDashboardPage() {
  const params = useParams<{ id: string }>();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [eventQr, setEventQr] = useState<EventQr | null>(null);
  const [error, setError] = useState("");

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

  const { metrics } = dashboard;
  const state = dashboard.event.state;

  return (
    <main className="screen admin-screen event-dashboard">
      <section className="admin-header">
        <div>
          <p className="eyebrow">Organizer dashboard</p>
          <h1>{dashboard.event.name}</h1>
          <p className="dashboard-status">
            <span className={`state-pill state-${state.toLowerCase()}`}>
              {STATE_LABEL[state] ?? state}
            </span>
            {state !== "ENDED" && (
              <span>{formatRemaining(metrics.timeRemainingSeconds ?? 0)}</span>
            )}
          </p>
        </div>
        <div className="admin-actions">
          {state === "DRAFT" && (
            <button type="button" onClick={() => void changeState("publish")}>
              Open waiting room
            </button>
          )}
          {state === "WAITING" && (
            <button type="button" onClick={() => void changeState("start")}>
              Start event
            </button>
          )}
          {state === "ACTIVE" && (
            <button type="button" onClick={() => void changeState("end")}>
              End event
            </button>
          )}
        </div>
      </section>
      <nav className="admin-links" aria-label="Event management">
        <Link href={`/admin/events/${params.id}/participants`}>
          Participants
        </Link>
        <Link href={`/admin/events/${params.id}/tasks`}>Tasks</Link>
        <Link href={`/admin/events/${params.id}/submissions`}>
          Submissions
          {metrics.pendingProofReviews > 0 &&
            ` (${metrics.pendingProofReviews})`}
        </Link>
        <Link href={`/admin/events/${params.id}/leaderboard`}>Leaderboard</Link>
        <Link href={`/admin/events/${params.id}/rewards`}>Rewards</Link>
        <Link href={`/admin/events/${params.id}/reimbursements`}>
          Reimbursements
        </Link>
      </nav>
      {error && <p className="error">{error}</p>}
      {METRIC_GROUPS.map((group) => (
        <section className="metric-group" key={group.title}>
          <h2>{group.title}</h2>
          <div className="metrics-grid">
            {group.metrics.map((metric) => (
              <article
                className={`card metric-card${
                  metric.highlight && (metrics[metric.key] ?? 0) > 0
                    ? " metric-card-alert"
                    : ""
                }`}
                key={metric.key}
              >
                <strong>{metrics[metric.key] ?? 0}</strong>
                <span>{metric.label}</span>
              </article>
            ))}
          </div>
        </section>
      ))}
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
    </main>
  );
}
