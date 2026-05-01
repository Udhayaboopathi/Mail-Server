export function Avatar({ name }: { name: string }) {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
    .slice(0, 2);

  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-ink text-sm font-semibold text-paper dark:bg-gray-800 dark:text-gray-100">
      {initials || "?"}
    </div>
  );
}
