"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import { IdentityBuilder } from "../../../../components/identity-builder";

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
  const [eventName, setEventName] = useState("EVENT");
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    let active = true;
    apiRequest<{ name: string }>(`/events/${params.slug}`)
      .then((event) => {
        if (active) setEventName(event.name);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [params.slug]);

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
        setVerified(true);
        setError("");
        if (result.state === "ACTIVE")
          router.push(`/e/${params.slug}/task?eventId=${eventId}`);
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
    <>
      <div className="event-wait-status" role="status">
        {error ||
          `${status} — Waiting for Port to start the competition. Create your identity while you wait.`}
      </div>
      <IdentityBuilder
        slug={params.slug}
        eventId={eventId}
        eventName={eventName}
        checkedIn={verified}
      />
    </>
  );
}
