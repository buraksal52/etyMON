import type { ReactNode } from "react";

export function Spinner({ label = "Yükleniyor…" }: { label?: string }) {
  return (
    <div className="loading-block" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorNotice({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  if (!message) return null;
  return (
    <div className="notice notice-error" role="alert">
      <p>{message}</p>
      {onRetry && (
        <button
          type="button"
          className="button button-secondary button-small"
          onClick={onRetry}
        >
          Tekrar dene
        </button>
      )}
    </div>
  );
}

export function SuccessNotice({ message }: { message: string }) {
  if (!message) return null;
  return (
    <div className="notice notice-success" role="status">
      <p>{message}</p>
    </div>
  );
}

export function WarningNotice({ children }: { children: ReactNode }) {
  return (
    <div className="notice notice-warning" role="status">
      {children}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <h2>{title}</h2>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}
