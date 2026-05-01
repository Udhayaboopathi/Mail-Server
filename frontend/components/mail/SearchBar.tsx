"use client";

import { Input } from "@/components/ui/Input";

export function SearchBar({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <Input
      placeholder="Search messages, people, subjects"
      value={value}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
