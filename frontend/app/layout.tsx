import "./globals.css";

import type { Metadata } from "next";
import { ReactNode } from "react";

import { AppProviders } from "@/components/providers/AppProviders";

export const metadata: Metadata = {
  title: "Email System",
  description: "Self-hosted email system",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#6366f1" />
      </head>
      <body>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
