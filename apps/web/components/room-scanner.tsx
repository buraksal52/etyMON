"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import type QrScanner from "qr-scanner";

export function RoomScanner() {
  const router = useRouter();
  const video = useRef<HTMLVideoElement>(null);
  const scanner = useRef<QrScanner | null>(null);
  const generation = useRef(0);
  const [state, setState] = useState<"idle" | "starting" | "scanning">("idle");
  const [error, setError] = useState("");
  const [code, setCode] = useState("");
  const isCodeValid = code === "admin123";

  function enterCode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!isCodeValid) return;
    stop();
    router.push("/e/monad-hackathon");
  }

  useEffect(
    () => () => {
      generation.current += 1;
      scanner.current?.destroy();
    },
    [],
  );

  function stop() {
    generation.current += 1;
    scanner.current?.destroy();
    scanner.current = null;
    setState("idle");
  }

  async function start() {
    const attempt = ++generation.current;
    setError("");
    setState("starting");
    try {
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
        throw new Error("Camera access requires HTTPS or localhost.");
      }
      const { default: Scanner } = await import("qr-scanner");
      if (attempt !== generation.current || !video.current) return;
      const instance = new Scanner(
        video.current,
        (result) => {
          try {
            const url = new URL(result.data, window.location.origin);
            if (
              url.origin !== window.location.origin ||
              !/^\/e\/[a-zA-Z0-9_-]+\/?$/.test(url.pathname)
            ) {
              setError("Please scan an etyMON event QR code.");
              return;
            }
            stop();
            router.push(url.pathname);
          } catch {
            setError("Please scan a valid event QR code.");
          }
        },
        {
          preferredCamera: "environment",
          maxScansPerSecond: 10,
          returnDetailedScanResult: true,
        },
      );
      scanner.current = instance;
      await instance.start();
      if (attempt !== generation.current) {
        instance.destroy();
        return;
      }
      setState("scanning");
    } catch (cause) {
      if (attempt !== generation.current) return;
      scanner.current?.destroy();
      scanner.current = null;
      setState("idle");
      setError(
        cause instanceof Error && cause.message.includes("HTTPS")
          ? cause.message
          : "Camera unavailable. Allow camera access, then try again.",
      );
    }
  }

  return (
    <section className="room-scanner" aria-label="Event QR scanner">
      <div className="room-scanner-bar">
        <span>0x00000</span>
        <button type="button" onClick={stop} aria-label="Stop camera">
          ×
        </button>
      </div>
      <div className="room-scan-body">
        <div className="room-scan-viewport">
          <video
            ref={video}
            muted
            playsInline
            aria-label="Live QR camera preview"
            className={state === "scanning" ? "is-active" : ""}
          />
          <i />
          <i />
          <i />
          <i />
          {state !== "scanning" && (
            <button
              className="room-scan-start"
              type="button"
              onClick={start}
              disabled={state === "starting"}
            >
              {state === "starting" ? "OPENING CAMERA…" : "START SCANNING"}
            </button>
          )}
        </div>
        <p className="room-scan-caption" aria-live="polite">
          {state === "scanning"
            ? "ALIGN THE QR INSIDE THE FRAME"
            : "SCAN THE QR AT THE VENUE"}
        </p>
        {error && (
          <p className="room-scan-error" role="alert">
            {error}
          </p>
        )}
      </div>
      <form className="room-event-code" onSubmit={enterCode}>
        <label htmlFor="event-code">CAN’T SCAN? ENTER EVENT CODE</label>
        <div className="room-code-controls">
          <input
            id="event-code"
            name="eventCode"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="Event code"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            maxLength={120}
            required
            aria-invalid={code.length > 0 && !isCodeValid}
            aria-describedby="event-code-status"
          />
          <button type="submit" disabled={!isCodeValid}>
            Next →
          </button>
        </div>
        <p id="event-code-status" role="status">
          {isCodeValid
            ? "Code verified. You can continue."
            : code
              ? "Invalid event code. Try again."
              : "Enter your event code to continue."}
        </p>
      </form>
    </section>
  );
}
