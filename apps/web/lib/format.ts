export type EventState = "DRAFT" | "WAITING" | "ACTIVE" | "ENDED";

export const EVENT_STATE_LABELS: Record<EventState, string> = {
  DRAFT: "Taslak",
  WAITING: "Katılım bekleniyor",
  ACTIVE: "Event aktif",
  ENDED: "Event sona erdi",
};

export const PROOF_TYPE_LABELS: Record<string, string> = {
  IMAGE: "Fotoğraf",
  TEXT: "Metin",
  URL: "URL",
  IMAGE_AND_URL: "Fotoğraf ve URL",
  TEXT_OR_URL: "Metin veya URL",
};

export const REVIEW_STATUS_LABELS: Record<string, string> = {
  PENDING: "İnceleme bekliyor",
  SUBMITTED: "İnceleme bekliyor",
  APPROVED: "Onaylandı",
  REJECTED: "Reddedildi",
  PAID: "Ödendi",
  ASSIGNED: "Atandı",
  EXPIRED: "Süresi doldu",
};

export function eventStateLabel(state: string): string {
  return EVENT_STATE_LABELS[state as EventState] ?? state;
}

export function proofTypeLabel(type: string): string {
  return PROOF_TYPE_LABELS[type] ?? type;
}

export function reviewStatusLabel(status: string): string {
  return REVIEW_STATUS_LABELS[status] ?? status;
}

/** API timestamps are UTC; naive strings are treated as UTC. */
function parseApiDate(value: string): Date {
  const hasZone = /[zZ]|[+-]\d\d:?\d\d$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

/** `datetime-local` input value -> ISO string (or null when empty). */
export function localInputToIso(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

/** API timestamp -> `datetime-local` input value. */
export function isoToLocalInput(value: string | null | undefined): string {
  if (!value) return "";
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function slugify(value: string): string {
  return value
    .toLocaleLowerCase("tr-TR")
    .replace(/ı/g, "i")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function isImageKey(value: string | null | undefined): boolean {
  return !!value && /\.(jpe?g|png|webp)(\?|$)/i.test(value);
}
