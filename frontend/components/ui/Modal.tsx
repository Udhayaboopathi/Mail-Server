"use client";

import { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Modal({
  open,
  onClose,
  children,
  className,
}: {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  if (!open) {
    return null;
  }
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/50 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className={cn(
          "max-h-[90vh] w-full max-w-4xl overflow-auto rounded-3xl bg-white p-6 shadow-panel",
          className,
        )}
        onClick={(event: { stopPropagation: () => void }) =>
          event.stopPropagation()
        }
      >
        {children}
      </div>
    </div>
  );
}
