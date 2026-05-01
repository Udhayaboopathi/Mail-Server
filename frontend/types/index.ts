export type AuthTokens = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
};

export type User = {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  created_at?: string;
  updated_at?: string | null;
};

export type Domain = {
  id: string;
  name: string;
  is_active: boolean;
  dkim_selector: string;
  spf_record?: string | null;
  dmarc_record?: string | null;
  created_at?: string;
};

export type Mailbox = {
  id: string;
  user_id: string;
  domain_id: string;
  local_part: string;
  full_address: string;
  quota_mb: number;
  used_mb: number;
  maildir_path?: string | null;
  is_active: boolean;
  created_at?: string;
};

export type FolderSummary = {
  folders: string[];
};

export type MailSummary = {
  id: string;
  uid: number;
  sender: string;
  recipients: string[];
  subject: string;
  date?: string | null;
  flags: string[];
  size: number;
  has_attachments: boolean;
  preview?: string | null;
};

export type MailMessage = {
  id: string;
  uid: number;
  folder: string;
  headers: Record<string, string>;
  body_text?: string | null;
  body_html?: string | null;
  attachments: Attachment[];
  flags: string[];
  date?: string | null;
};

export type Attachment = {
  filename: string;
  content_base64: string;
  mime_type: string;
};

export type MailSendRequest = {
  to: string[];
  cc?: string[];
  bcc?: string[];
  subject: string;
  body_text: string;
  body_html?: string | null;
  attachments?: Attachment[];
};

export type DNSRecords = {
  MX: string;
  A: string;
  SPF: string;
  DKIM: string;
  DMARC: string;
};

export type Stats = {
  total_users: number;
  total_domains: number;
  total_mailboxes: number;
  audit_logs: number;
  mail_volume_today: number;
  storage_used_mb: number;
};
