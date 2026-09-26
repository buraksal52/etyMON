// Angular terminal lettering, drawn as strokes so the display is font-independent.
const glyphs: Record<string, string> = {
  C: "M34 4H8L4 8V52L8 56H34",
  O: "M8 4H30L34 8V52L30 56H8L4 52V8Z",
  N: "M4 56V4L34 56V4",
  G: "M34 4H8L4 8V52L8 56H34V32H20",
  R: "M4 56V4H30L34 8V26L30 30H4M20 30L34 56",
  A: "M4 56V8L8 4H30L34 8V56M4 30H34",
  T: "M2 4H36M19 4V56",
  S: "M34 4H8L4 8V26L8 30H30L34 34V52L30 56H4",
  H: "M4 4V56M34 4V56M4 30H34",
  K: "M4 4V56M34 4L5 30L34 56",
  E: "M34 4H4V56H34M4 30H29",
  "!": "M19 4V40M19 51V56",
};

export function EntrySuccess() {
  return (
    <main className="entry-success" aria-labelledby="entry-success-title">
      <h1 id="entry-success-title" aria-label="Congrats hacker!">
        {["CONGRATS", "HACKER!"].map((line) => (
          <svg
            key={line}
            viewBox={`0 0 ${line.length * 50} 64`}
            aria-hidden="true"
          >
            {Array.from(line).map((letter, index) => (
              <path
                key={index}
                d={glyphs[letter]}
                transform={`translate(${index * 50 + 6} 2)`}
              />
            ))}
          </svg>
        ))}
      </h1>
      <p role="status">You’re in. Make your identity.</p>
      <div className="entry-success-progress" aria-hidden="true">
        <span />
      </div>
    </main>
  );
}
