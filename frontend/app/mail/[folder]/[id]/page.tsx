"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { EmailReader } from "@/components/mail/EmailReader";
import { api } from "@/lib/api";
import type { MailMessage } from "@/types";

const fallbackMessage: MailMessage = {
  id: "placeholder",
  uid: 0,
  folder: "inbox",
  headers: {
    from: "mail@yourdomain.com",
    to: "you@yourdomain.com",
    subject: "Welcome",
    date: new Date().toISOString(),
  },
  body_text: "Your inbox is ready.",
  body_html: "<p>Your inbox is ready.</p>",
  attachments: [],
  flags: [],
};

export default function MessagePage() {
  const params = useParams<{ folder: string; id: string }>();
  const folder = Array.isArray(params.folder)
    ? params.folder[0]
    : params.folder;
  const id = Number(Array.isArray(params.id) ? params.id[0] : params.id);
  const [message, setMessage] = useState<MailMessage | null>(null);

  useEffect(() => {
    let mounted = true;
    api.mail
      .get(folder, id)
      .then((data) => {
        if (mounted) {
          setMessage(data);
        }
      })
      .catch(() => setMessage(fallbackMessage));
    return () => {
      mounted = false;
    };
  }, [folder, id]);

  return <EmailReader message={message ?? fallbackMessage} />;
}
