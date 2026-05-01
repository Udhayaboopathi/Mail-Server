import { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  accept?: string;
};

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "w-full rounded-2xl border border-black/10 bg-white/80 px-4 py-3 text-ink outline-none ring-0 placeholder:text-black/40 focus:border-ember dark:border-gray-700 dark:bg-gray-900/80 dark:text-gray-100 dark:placeholder:text-gray-400",
        className,
      )}
      {...props}
    />
  );
}
