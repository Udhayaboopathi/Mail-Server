"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/Button";

export function MobileSidebar() {
  const [open, setOpen] = useState(false);
  const folders = ["Inbox", "Sent", "Drafts", "Trash", "Spam"];

  return (
    <div className="lg:hidden">
      <Button className="bg-sand text-ink" onClick={() => setOpen(true)}>
        Menu
      </Button>
      {open ? (
        <div
          className="fixed inset-0 z-50 bg-ink/50 p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="h-full w-72 rounded-3xl bg-white p-5"
            onClick={(event) => event.stopPropagation()}
          >
            <p className="mb-4 text-xs font-semibold uppercase tracking-[0.3em] text-ember">
              Folders
            </p>
            <div className="space-y-2">
              {folders.map((folder) => (
                <Link
                  key={folder}
                  href={`/mail/${folder.toLowerCase()}`}
                  className="block rounded-2xl px-4 py-3 text-sm font-medium text-ink hover:bg-paper"
                  onClick={() => setOpen(false)}
                >
                  {folder}
                </Link>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
