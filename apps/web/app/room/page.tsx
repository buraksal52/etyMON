import Link from "next/link";
import type { Metadata } from "next";
import { RoomScanner } from "../../components/room-scanner";

export const metadata: Metadata = {
  title: "etyMON — The room is waiting for you",
  description:
    "Scan the event QR to enter the mission. Monad Hackathon — access opens when Port starts the event.",
};

export default function RoomPage() {
  return (
    <div className="room-page">
      <div className="room-stage">
        <header className="site-header">
          <Link
            className="brand"
            href="/identity"
            aria-label="etyMON — build your identity"
          >
            <svg
              className="room-logo"
              viewBox="0 0 40 40"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M3 40V3H38M37 13V37H14M16 13V26M16 19H25"
                stroke="currentColor"
                strokeWidth="6"
              />
            </svg>
            <span>etyMON</span>
          </Link>
        </header>
        <main className="room-main">
          <div className="room-copy">
            <h1 aria-label="The room is waiting for you.">
              <svg viewBox="0 0 700 368" aria-hidden="true" focusable="false">
                <text
                  x="0"
                  y="108"
                  textLength="650"
                  lengthAdjust="spacingAndGlyphs"
                >
                  THE ROOM
                </text>
                <text
                  x="0"
                  y="235"
                  textLength="695"
                  lengthAdjust="spacingAndGlyphs"
                >
                  IS WAITING
                </text>
                <text
                  x="0"
                  y="362"
                  textLength="578"
                  lengthAdjust="spacingAndGlyphs"
                >
                  FOR YOU.
                </text>
              </svg>
            </h1>
            <p>Scan the event QR to enter the mission.</p>
          </div>
          <div className="room-art">
            <RoomScanner />
          </div>
          <footer className="room-instructions">
            <p>Monad Hackathon · Access opens when Port starts the event.</p>
            <span>
              <b>01</b> SCAN　 /　 <b>02</b> VERIFY EMAIL　 /　 <b>03</b> ENTER
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
