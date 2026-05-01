import type { User } from "@/types";

export function UserTable({ users }: { users: User[] }) {
  return (
    <div className="overflow-hidden rounded-3xl border border-black/10 bg-white/90 shadow-panel">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-paper text-ink/60">
          <tr>
            <th className="px-4 py-3">Email</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id} className="border-t border-black/5">
              <td className="px-4 py-3 font-medium text-ink">{user.email}</td>
              <td className="px-4 py-3 text-ink/70">
                {user.is_admin ? "Admin" : "User"}
              </td>
              <td className="px-4 py-3 text-ink/70">
                {user.is_active ? "Active" : "Disabled"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
