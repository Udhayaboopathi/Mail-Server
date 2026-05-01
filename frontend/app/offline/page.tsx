export default function OfflinePage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-6 py-12 text-ink dark:bg-gray-950 dark:text-gray-100">
      <div className="max-w-md rounded-3xl border border-black/10 bg-white/90 p-8 text-center shadow-panel dark:border-gray-700 dark:bg-gray-900">
        <h1 className="text-2xl font-semibold">You are offline</h1>
        <p className="mt-3 text-sm text-ink/70 dark:text-gray-400">
          We cannot reach the server right now. Check your connection and try
          again.
        </p>
      </div>
    </div>
  );
}
