import Link from "next/link";

const SECTIONS = [
  { slug: "", label: "Dashboard" },
  { slug: "participants", label: "Katılımcılar" },
  { slug: "tasks", label: "Görevler" },
  { slug: "submissions", label: "Gönderimler" },
  { slug: "leaderboard", label: "Leaderboard" },
  { slug: "rewards", label: "Ödüller" },
  { slug: "reimbursements", label: "Masraflar" },
];

export function AdminEventNav({
  eventId,
  current,
}: {
  eventId: string;
  current: string;
}) {
  return (
    <nav className="tab-nav" aria-label="Event yönetimi">
      {SECTIONS.map((section) => (
        <Link
          key={section.slug}
          href={`/admin/events/${eventId}${section.slug ? `/${section.slug}` : ""}`}
          aria-current={section.slug === current ? "page" : undefined}
        >
          {section.label}
        </Link>
      ))}
    </nav>
  );
}

export function AdminPageHeader({
  eventId,
  current,
  title,
  description,
  actions,
}: {
  eventId: string;
  current: string;
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <>
      <p className="breadcrumb">
        <Link href="/admin">← Tüm event&apos;ler</Link>
      </p>
      <header className="page-header">
        <div>
          <p className="eyebrow">Organizer paneli</p>
          <h1>{title}</h1>
          {description && <p className="muted">{description}</p>}
        </div>
        {actions && <div className="header-actions">{actions}</div>}
      </header>
      <AdminEventNav eventId={eventId} current={current} />
    </>
  );
}
