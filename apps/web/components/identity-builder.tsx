"use client";

import { useRef, useState, type PointerEvent } from "react";
import Link from "next/link";

const characters = [
  "Cipher",
  "Nova",
  "Ghost",
  "Echo",
  "Neo",
  "Scout",
  "Pixel",
  "Vex",
];
const frames = ["ACCESS", "WINDOWS", "BIOS", "HUD"];
// Stable decorative sequences keep the preview and downloaded card identical.
const edgeHashes = [
  "7K0X9A2F4M8Q1B6Z3R5V 0N8C2L9W4D1J6P3S7T5H",
  "3R8W0B6Y2N9D4K1V7F5A 9J2M6X0Q4C8Z1L5P3T7S",
  "6P1Z8C3T0H5V9A2N7K4X 2F7Q0M5B9W3D8R1J4L6Y",
  "9D4L1Q7F0X6M3A8T2W5N 5V0K8R2C6Z9B4P1H7J3S",
];

function FramePreview({ index }: { index: number }) {
  const portrait = (
    <g fill="currentColor" stroke="none">
      <path d="M43 40h14v4h4v14h-4v5H43v-5h-4V44h4Z" />
      <path d="M38 68h24l7 7v10H31V75Z" />
    </g>
  );

  return (
    <svg
      className="frame-drawing"
      viewBox="0 0 180 112"
      fill="none"
      stroke="currentColor"
      strokeWidth="1"
      aria-hidden="true"
    >
      {index === 0 && (
        <>
          <path d="M5 20V5h116l9 9h45v93H5V27" />
          <path d="M13 14h39M13 18h23M140 21h27M140 25h27" />
          <path d="M22 32h56v61H22Z" opacity=".45" />
          {portrait}
          <path d="M91 43h62M91 49h38M91 65h54M91 71h27" />
          <path d="M93 84v12m4-12v12m6-12v12m3-12v12m7-12v12m5-12v12m3-12v12m8-12v12m3-12v12m5-12v12m7-12v12m3-12v12m6-12v12" />
          <path d="M9 103h12" strokeWidth="3" />
        </>
      )}
      {index === 1 && (
        <>
          <path d="M8 75V7h123v13M8 19h123M15 13h3m4 0h3m4 0h3" opacity=".4" />
          <path d="M20 87V23h126v12M20 35h115" opacity=".65" />
          <path
            d="M33 39h139v65H33ZM33 51h139M40 45h42M151 45h5m5 0h5"
            strokeWidth="3"
          />
          <g transform="translate(16 26) scale(.7)">{portrait}</g>
          <path d="M82 65h73M82 71h49M82 85h25v10H82ZM114 85h41v10h-41Z" />
          <path d="m151 96 5 14 3-6 6-2Z" fill="var(--ink)" />
        </>
      )}
      {index === 2 && (
        <>
          <path d="M5 5h170v102H5Z" />
          <path d="M6 6h168v17H6Z" fill="currentColor" stroke="none" />
          <text x="12" y="17" fill="var(--ink)" stroke="none" fontSize="9">
            etyMON / BIOS
          </text>
          <path d="M13 34h51m5 0h22M13 40h29m5 0h60M13 46h44" opacity=".65" />
          <path d="m14 59 4 3-4 3M25 62h57M25 70h39M25 78h49" />
          <path d="M112 36h48v45h-48ZM119 43h34v31h-34Z" />
          <path d="M120 32v4m8-4v4m8-4v4m8-4v4m8-4v4M120 81v5m8-5v5m8-5v5m8-5v5m8-5v5" />
          <path d="M13 94h154" opacity=".3" />
          <path d="M13 94h105" strokeWidth="4" />
          <text
            x="14"
            y="104"
            fill="currentColor"
            stroke="none"
            fontSize="6"
            letterSpacing="2"
          >
            7K0X9A2F4M8Q1B6Z3R5V
          </text>
          <path d="M80 76h6v4h-6Z" fill="currentColor" />
        </>
      )}
      {index === 3 && (
        <>
          <path
            d="M32 5h116a27 27 0 0 1 27 27v48a27 27 0 0 1-27 27H32A27 27 0 0 1 5 80V32A27 27 0 0 1 32 5Z"
            strokeWidth="2"
          />
          <path
            d="M12 40v32m156-32v32M42 12h31m34 0h31M42 100h31m34 0h31"
            opacity=".4"
          />
          <circle cx="90" cy="56" r="33" strokeDasharray="48 5 3 5" />
          <path d="M90 17v12m0 54v12M51 56h12m54 0h12" />
          <g transform="translate(55 14) scale(.7)">{portrait}</g>
          <path d="M15 18h5v5h-5Z" fill="currentColor" />
          <path
            d="M143 86h4v10h-4Zm7-6h4v16h-4Zm7-7h4v23h-4Z"
            fill="currentColor"
            stroke="none"
          />
          <path d="M17 89h21m-21 5h13" />
        </>
      )}
    </svg>
  );
}

function Avatar({ index }: { index: number }) {
  const extra = index >= 6;
  const column = extra ? index - 6 : index % 3;
  const row = extra ? 0 : Math.floor(index / 3);

  return (
    <span
      className="avatar-portrait"
      role="img"
      aria-label={characters[index]}
      style={{
        backgroundImage: `url(/assets/${extra ? "avatars-extra" : "avatars"}.png)`,
        backgroundSize: extra ? "200% 100%" : "300% 200%",
        backgroundPosition: `${column * (extra ? 100 : 50)}% ${row * 100}%`,
      }}
    />
  );
}

export function Brand() {
  return (
    <Link href="/" className="brand" aria-label="etyMON home">
      <span className="brand-mark">
        <i />
      </span>
      <span>etyMON</span>
    </Link>
  );
}

export function IdentityBuilder({
  eventName = "MONAD HACKATHON",
  slug,
  eventId,
  checkedIn = false,
}: {
  eventName?: string;
  slug?: string;
  eventId?: string | null;
  checkedIn?: boolean;
}) {
  const [name, setName] = useState("");
  const [avatar, setAvatar] = useState<number | null>(null);
  const [frame, setFrame] = useState(0);
  const [signature, setSignature] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const shareUrl = `https://x.com/intent/post?text=${encodeURIComponent(`My identity is ready. See you at ${eventName}! #etyMON`)}`;
  const canvas = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const card = useRef<HTMLDivElement>(null);
  const [leaderboardOpen, setLeaderboardOpen] = useState(false);
  function point(e: PointerEvent<HTMLCanvasElement>) {
    const bounds = e.currentTarget.getBoundingClientRect();
    return [
      ((e.clientX - bounds.left) * 1000) / bounds.width,
      ((e.clientY - bounds.top) * 170) / bounds.height,
    ];
  }
  function start(e: PointerEvent<HTMLCanvasElement>) {
    drawing.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    const ctx = e.currentTarget.getContext("2d")!;
    const [x, y] = point(e);
    ctx.strokeStyle = "#58f52b";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.lineTo(x + 0.1, y);
    ctx.stroke();
  }
  function draw(e: PointerEvent<HTMLCanvasElement>) {
    if (!drawing.current) return;
    const [x, y] = point(e);
    const ctx = e.currentTarget.getContext("2d")!;
    ctx.lineTo(x, y);
    ctx.stroke();
  }
  function finish() {
    drawing.current = false;
    setSignature(canvas.current?.toDataURL() ?? "");
  }
  async function download() {
    if (!name.trim() || avatar === null) {
      setMessage("Enter your name and choose a character to create your ID.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const { toPng } = await import("html-to-image");
      const data = await toPng(card.current!, {
        pixelRatio: 2,
        backgroundColor: "#030803",
      });
      const a = document.createElement("a");
      a.download = `etyMON-${name.trim().replace(/[^a-z0-9_-]/gi, "-")}.png`;
      a.href = data;
      a.click();
      setMessage("Your card is downloaded.");
    } catch {
      setMessage("Could not export your card. Please try again.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="identity-page">
      <header className="site-header">
        <Brand />
        <nav>
          <a href="#how-it-works">HOW IT WORKS</a>
          {slug && eventId ? (
            <Link
              href={`/e/${slug}/leaderboard?eventId=${encodeURIComponent(eventId)}`}
            >
              LEADERBOARD
            </Link>
          ) : (
            <button onClick={() => setLeaderboardOpen(true)}>
              LEADERBOARD
            </button>
          )}
        </nav>
      </header>
      <main className="identity-main">
        <div className="identity-editor">
          <p className="section-kicker">
            <span /> IDENTITY / 01
          </p>
          <h1>
            BUILD
            <br />
            <em>YOUR ID.</em>
          </h1>
          <label htmlFor="username" className="control-label">
            USERNAME
          </label>
          <input
            id="username"
            className="name-input"
            placeholder="Enter your name"
            maxLength={24}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <p className="field-hint">Your name appears on the card.</p>
          <fieldset>
            <legend>CHOOSE A CHARACTER</legend>
            <div className="characters">
              {characters.map((character, i) => (
                <button
                  key={character}
                  className={`character ${avatar === i ? "selected" : ""}`}
                  aria-label={`Choose ${character}`}
                  aria-pressed={avatar === i}
                  onClick={() => setAvatar(i)}
                >
                  <Avatar index={i} />
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>CHOOSE A FRAME</legend>
            <div className="frames">
              {frames.map((item, i) => (
                <button
                  key={item}
                  className={`frame-option ${frame === i ? "selected" : ""}`}
                  aria-pressed={frame === i}
                  onClick={() => setFrame(i)}
                >
                  <FramePreview index={i} />
                  <span>
                    0{i + 1} {item}
                  </span>
                </button>
              ))}
            </div>
          </fieldset>
          <div className="signature-heading">
            <label htmlFor="signature" className="control-label">
              SIGNATURE
            </label>
            <button
              onClick={() => {
                canvas.current?.getContext("2d")?.clearRect(0, 0, 1000, 170);
                setSignature("");
              }}
            >
              Clear
            </button>
          </div>
          <canvas
            id="signature"
            ref={canvas}
            width={1000}
            height={170}
            className="signature-pad"
            aria-label="Draw your signature using a mouse, finger or pen"
            onPointerDown={start}
            onPointerMove={draw}
            onPointerUp={finish}
            onPointerCancel={finish}
          />
          <p className="field-hint signature-hint">
            Draw with your finger, mouse or trackpad.
          </p>
        </div>
        <aside
          className="preview-column"
          aria-label="Live identity card preview"
        >
          <div ref={card} className={`identity-card theme-${frame}`}>
            {frame === 2 && (
              <div className="card-hash-border" aria-hidden="true">
                {edgeHashes.map((hash, index) => (
                  <span
                    key={hash}
                    className={`card-hash-edge hash-edge-${index}`}
                  >
                    {`${hash} ${hash} ${hash}`}
                  </span>
                ))}
              </div>
            )}
            <div className="terminal-header">
              <span>{eventName}</span>
            </div>
            <div className="terminal-body">
              <h2>HACKER</h2>
              <div className="portrait-panel">
                <div className="portrait-titlebar" aria-hidden="true">
                  <span>CHARACTER.SYS</span>
                  <span>− + ×</span>
                </div>
                <div className="portrait-window">
                  {avatar === null ? (
                    <div className="avatar-placeholder">
                      <b>?</b>
                      <span>SELECT AVATAR</span>
                    </div>
                  ) : (
                    <Avatar index={avatar} />
                  )}
                </div>
                <div className="portrait-strip" aria-hidden="true">
                  <span>
                    PLAYER /{" "}
                    {avatar === null
                      ? "--"
                      : String(avatar + 1).padStart(2, "0")}
                  </span>
                  <i />
                </div>
              </div>
              <dl className="identity-details">
                <dt>USER:</dt>
                <dd>{name.trim() || "YOUR NAME"}</dd>
                <dt>STATUS:</dt>
                <dd className="green">
                  {checkedIn ? "CHECKED IN" : "ID READY"}
                </dd>
                <dt>EVENT:</dt>
                <dd>{eventName}</dd>
              </dl>
              <div className="card-signature">
                <span>SIGNATURE /</span>
                {signature && (
                  <span
                    className="signature-image"
                    style={{ backgroundImage: `url(${signature})` }}
                  />
                )}
              </div>
              <footer>
                <span>etyMON</span>
                <span>0xA4D91E</span>
              </footer>
            </div>
          </div>
          <div className="preview-actions">
            <a
              className="share-button"
              href={shareUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              SHARE ON X<span aria-hidden="true">↗</span>
            </a>
            <button
              type="button"
              className="save-image-button"
              disabled={busy}
              onClick={() => void download()}
            >
              {busy ? "SAVING IMAGE…" : "SAVE IMAGE"}
              <span aria-hidden="true">↓</span>
            </button>
            <Link
              href={
                slug && eventId
                  ? `/e/${slug}/task?eventId=${encodeURIComponent(eventId)}`
                  : "/room"
              }
              className="next-button"
            >
              NEXT <span aria-hidden="true">→</span>
            </Link>
          </div>
          <div className="export-note">
            <p className="field-hint">
              Share on X opens a new post. To include your card, save the image
              and attach it on X.
            </p>
          </div>
          <p role="status" className="export-status">
            {message}
          </p>
        </aside>
        <section id="how-it-works" className="how-section">
          <h2>HOW IT WORKS</h2>
          <ol>
            <li>Scan the event QR and verify your email.</li>
            <li>Choose a name and a character for your card.</li>
            <li>When the host starts the event, your missions unlock.</li>
          </ol>
          <Link href="/room">
            THE ROOM IS WAITING FOR YOU <span>↗</span>
          </Link>
        </section>
      </main>
      <footer className="site-footer">
        <span>etyMON / BUILT FOR THE ROOM.</span>
        <span>SHOW UP. BUILD. BELONG.</span>
      </footer>
      {leaderboardOpen && (
        <div
          className="modal-backdrop"
          onKeyDown={(event) => {
            if (event.key === "Escape") setLeaderboardOpen(false);
            if (event.key === "Tab") {
              const items =
                event.currentTarget.querySelectorAll<HTMLElement>("button, a");
              const first = items[0];
              const last = items[items.length - 1];
              if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
              }
              if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
              }
            }
          }}
          onClick={() => setLeaderboardOpen(false)}
        >
          <section
            className="leaderboard-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="leaderboard-title"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              autoFocus
              className="dialog-close"
              aria-label="Close leaderboard"
              onClick={() => setLeaderboardOpen(false)}
            >
              ×
            </button>
            <p className="section-kicker">THE COMPETITION / 02</p>
            <h2 id="leaderboard-title">LEADERBOARD</h2>
            <p>
              Scan the QR at your event and check in to view your event’s live
              leaderboard.
            </p>
            <Link href="/room">VIEW THE ROOM ↗</Link>
          </section>
        </div>
      )}
    </div>
  );
}
