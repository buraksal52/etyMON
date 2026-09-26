"use client";

import { useState } from "react";

export function CopyButton({ value, label }: { value: string; label: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setState("copied");
    } catch {
      setState("failed");
    }
    window.setTimeout(() => setState("idle"), 2000);
  }

  return (
    <button
      type="button"
      className="button button-secondary button-small"
      onClick={() => void copy()}
    >
      {state === "copied"
        ? "Kopyalandı ✓"
        : state === "failed"
          ? "Kopyalanamadı"
          : label}
    </button>
  );
}
