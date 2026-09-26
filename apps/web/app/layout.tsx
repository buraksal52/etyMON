import type { Metadata } from "next";
import { PageBackground } from "../components/page-background";

import "./globals.css";

export const metadata: Metadata = {
  title: "etyMON — Build your identity",
  description:
    "Show up. Build. Belong. Create your etyMON event identity and enter the mission.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <PageBackground>{children}</PageBackground>
      </body>
    </html>
  );
}
