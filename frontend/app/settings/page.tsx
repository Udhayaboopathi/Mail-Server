"use client";

import { useEffect, useState } from "react";

import { AutoresponderSettings } from "@/components/mail/AutoresponderSettings";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { apiFetch } from "@/lib/api";

type AliasItem = {
  id: string;
  source_address: string;
  destination_address: string;
  is_active: boolean;
};

type ContactItem = {
  id?: string | null;
  email: string;
  name?: string | null;
};

export default function SettingsPage() {
  const [aliases, setAliases] = useState<AliasItem[]>([]);
  const [contacts, setContacts] = useState<ContactItem[]>([]);
  const [aliasLocalPart, setAliasLocalPart] = useState("random");
  const [contactEmail, setContactEmail] = useState("");
  const [contactName, setContactName] = useState("");

  const load = async () => {
    const [aliasData, contactData] = await Promise.all([
      apiFetch<AliasItem[]>("/api/mail/aliases"),
      apiFetch<ContactItem[]>("/api/contacts"),
    ]);
    setAliases(aliasData);
    setContacts(contactData);
  };

  useEffect(() => {
    void load();
  }, []);

  const createAlias = async () => {
    await apiFetch("/api/mail/aliases", {
      method: "POST",
      body: JSON.stringify({ local_part: aliasLocalPart }),
    });
    setAliasLocalPart("random");
    await load();
  };

  const deleteAlias = async (id: string) => {
    await apiFetch(`/api/mail/aliases/${id}`, { method: "DELETE" });
    await load();
  };

  const addContact = async () => {
    await apiFetch("/api/contacts", {
      method: "POST",
      body: JSON.stringify({ email: contactEmail, name: contactName || null }),
    });
    setContactEmail("");
    setContactName("");
    await load();
  };

  const exportMailbox = async (kind: "mbox" | "zip") => {
    const profile =
      await apiFetch<{ id: string; user_id: string }[]>("/api/mailboxes");
    if (profile.length === 0) {
      return;
    }
    const mailboxId = profile[0].id;
    window.open(
      `${process.env.NEXT_PUBLIC_API_URL ?? ""}/api/mailboxes/${mailboxId}/export/${kind}`,
      "_blank",
    );
  };

  return (
    <section className="space-y-6">
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-ember">
          Account
        </p>
        <h1 className="text-3xl font-semibold text-ink">Settings</h1>
      </div>

      <AutoresponderSettings />

      <div className="rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel space-y-4">
        <h2 className="text-xl font-semibold text-ink">Aliases</h2>
        <div className="flex gap-3">
          <Input
            value={aliasLocalPart}
            onChange={(event) => setAliasLocalPart(event.target.value)}
            placeholder="random or alias"
          />
          <Button onClick={() => void createAlias()}>Create</Button>
        </div>
        <div className="space-y-2">
          {aliases.map((alias) => (
            <div
              key={alias.id}
              className="flex items-center justify-between rounded-2xl border border-black/10 px-3 py-2"
            >
              <span className="text-sm text-ink">
                {alias.source_address} → {alias.destination_address}
              </span>
              <Button
                className="bg-sand text-ink"
                onClick={() => void deleteAlias(alias.id)}
              >
                Deactivate
              </Button>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel space-y-4">
        <h2 className="text-xl font-semibold text-ink">Contacts</h2>
        <div className="grid gap-3 md:grid-cols-3">
          <Input
            value={contactEmail}
            onChange={(event) => setContactEmail(event.target.value)}
            placeholder="email@example.com"
          />
          <Input
            value={contactName}
            onChange={(event) => setContactName(event.target.value)}
            placeholder="Name (optional)"
          />
          <Button onClick={() => void addContact()}>Add Contact</Button>
        </div>
        <ul className="space-y-2">
          {contacts.map((contact, index) => (
            <li
              key={`${contact.email}-${index}`}
              className="rounded-2xl border border-black/10 px-3 py-2 text-sm text-ink"
            >
              {contact.name
                ? `${contact.name} <${contact.email}>`
                : contact.email}
            </li>
          ))}
        </ul>
      </div>

      <div className="rounded-3xl border border-black/10 bg-white/90 p-5 shadow-panel space-y-3">
        <h2 className="text-xl font-semibold text-ink">Export My Mailbox</h2>
        <div className="flex gap-3">
          <Button onClick={() => void exportMailbox("mbox")}>
            Export MBOX
          </Button>
          <Button
            className="bg-ember"
            onClick={() => void exportMailbox("zip")}
          >
            Export ZIP
          </Button>
        </div>
      </div>
    </section>
  );
}
