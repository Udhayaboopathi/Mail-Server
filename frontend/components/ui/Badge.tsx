import { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Badge({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-sand px-2.5 py-1 text-xs font-medium text-ink dark:bg-gray-800 dark:text-gray-100",
        className,
      )}
    >
      {children}
    </span>
  );
}
