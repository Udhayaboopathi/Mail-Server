"use client";

import { useEffect, useState } from "react";

import { UserTable } from "@/components/admin/UserTable";
import { api } from "@/lib/api";
import type { User } from "@/types";

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    api.users
      .list()
      .then(setUsers)
      .catch(() => setUsers([]));
  }, []);

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-ember">Admin</p>
        <h1 className="text-3xl font-semibold text-ink">Users</h1>
      </div>
      <UserTable users={users} />
    </section>
  );
}
