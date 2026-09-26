"use client";

import { useState } from "react";

type ConfirmButtonProps = {
  label: string;
  confirmLabel?: string;
  question: string;
  onConfirm: () => void | Promise<void>;
  disabled?: boolean;
  busy?: boolean;
  variant?: "primary" | "secondary" | "danger";
  small?: boolean;
};

/** Two-step button: asks for confirmation inline before running an action. */
export function ConfirmButton({
  label,
  confirmLabel = "Evet, onayla",
  question,
  onConfirm,
  disabled = false,
  busy = false,
  variant = "primary",
  small = false,
}: ConfirmButtonProps) {
  const [asking, setAsking] = useState(false);
  const size = small ? " button-small" : "";

  if (asking) {
    return (
      <div className="confirm-inline" role="group" aria-label={question}>
        <span>{question}</span>
        <button
          type="button"
          className={`button button-${variant}${size}`}
          disabled={busy}
          onClick={async () => {
            await onConfirm();
            setAsking(false);
          }}
        >
          {busy ? "İşleniyor…" : confirmLabel}
        </button>
        <button
          type="button"
          className={`button button-secondary${size}`}
          disabled={busy}
          onClick={() => setAsking(false)}
        >
          Vazgeç
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      className={`button button-${variant}${size}`}
      disabled={disabled || busy}
      onClick={() => setAsking(true)}
    >
      {label}
    </button>
  );
}
