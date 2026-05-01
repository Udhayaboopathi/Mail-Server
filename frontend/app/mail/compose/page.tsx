"use client";

import { useState } from "react";

import { ComposeModal } from "@/components/mail/ComposeModal";

export default function ComposePage() {
  const [open, setOpen] = useState(true);
  return <ComposeModal open={open} onClose={() => setOpen(false)} />;
}
