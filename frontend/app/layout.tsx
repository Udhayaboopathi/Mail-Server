import "./globals.css";

import type { Metadata } from "next";
import { ReactNode } from "react";

import { QueryProvider } from "@/components/providers/QueryProvider";

export const metadata: Metadata = {
  title: "Email System",
  description: "Self-hosted email system",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
