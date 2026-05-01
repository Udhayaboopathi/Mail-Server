import { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  accept?: string;
};

export function Input({
  className,
  ...props
}: InputProps) {
  return (
    <input
      className={cn(
        "w-full rounded-2xl border border-black/10 bg-white/80 px-4 py-3 outline-none ring-0 placeholder:text-black/40 focus:border-ember",
        className,
      )}
      {...props}
    />
  );
}
