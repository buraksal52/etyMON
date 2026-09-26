"use client";

import { useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";

import { describeError, isUnauthorized } from "./errors";

/** Returns a handler that redirects to login on 401 and otherwise yields a Turkish message. */
export function useAdminError() {
  const router = useRouter();
  const pathname = usePathname();
  return useCallback(
    (error: unknown, fallback: string): string => {
      if (isUnauthorized(error)) {
        router.push(`/admin/login?next=${encodeURIComponent(pathname)}`);
      }
      return describeError(error, fallback);
    },
    [router, pathname],
  );
}
