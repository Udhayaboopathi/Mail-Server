"use client";

import { ReactNode, useState } from "react";

import { ComposeModal } from "@/components/mail/ComposeModal";
import { MobileSidebar } from "@/components/layout/MobileSidebar";
import { Sidebar } from "@/components/layout/Sidebar";
import { Topbar } from "@/components/layout/Topbar";

export default function MailLayout({ children }: { children: ReactNode }) {
  const [composeOpen, setComposeOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onCompose={() => setComposeOpen(true)} />
        <div className="border-b border-black/10 bg-white/60 px-4 py-3 lg:hidden">
          <MobileSidebar />
        </div>
        <main className="flex-1 p-4 lg:p-8">{children}</main>
      </div>
      <ComposeModal open={composeOpen} onClose={() => setComposeOpen(false)} />
    </div>
  );
}
