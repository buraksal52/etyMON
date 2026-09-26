import Link from "next/link";

const ITEMS = [
  { path: "task", label: "Görev" },
  { path: "progress", label: "İlerleme" },
  { path: "leaderboard", label: "Sıralama" },
  { path: "reimbursement", label: "Masraf" },
];

export function ParticipantNav({
  slug,
  eventId,
  current,
}: {
  slug: string;
  eventId: string | null;
  current: string;
}) {
  if (!eventId) return null;
  return (
    <nav className="bottom-nav" aria-label="Katılımcı menüsü">
      {ITEMS.map((item) => (
        <Link
          key={item.path}
          href={`/e/${slug}/${item.path}?eventId=${encodeURIComponent(eventId)}`}
          aria-current={item.path === current ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

export function MissingSession({ slug }: { slug: string }) {
  return (
    <section className="card card-narrow">
      <p className="eyebrow">Oturum bulunamadı</p>
      <h1>Event oturumu yok</h1>
      <p className="muted">
        Bu sayfayı görmek için önce event&apos;e e-posta ile katılmalısın.
      </p>
      <Link className="button button-primary" href={`/e/${slug}`}>
        Event&apos;e katıl
      </Link>
    </section>
  );
}
