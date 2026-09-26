"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export function PageBackground({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className={pathname === "/" ? undefined : "animated-page-background"}>
      {children}
    </div>
  );
}
