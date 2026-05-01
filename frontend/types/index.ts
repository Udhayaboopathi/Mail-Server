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

export type TotpSetupResponse = {
  secret: string;
  qr_uri: string;
  backup_codes: string[];
};

export type TotpVerifyResponse = AuthTokens;

export type LoginActivityItem = {
  id: string;
  ip_address: string;
  user_agent?: string | null;
  device_type?: string | null;
  location?: string | null;
  success: boolean;
  failure_reason?: string | null;
  created_at: string;
};

export type PgpKeyResponse = {
  fingerprint: string;
  public_key: string;
};

export type ThreadLabel = {
  name: string;
  color: string;
};

export type ThreadSummary = {
  thread_id: string;
  subject: string;
  participants: string[];
  last_message_at?: string | null;
  message_count: number;
  has_unread: boolean;
  latest_preview: string;
  labels: ThreadLabel[];
  last_sender?: string | null;
};

export type ThreadMessage = {
  uid?: number | null;
  folder: string;
  from?: string | null;
  to?: string | null;
  subject?: string | null;
  date?: string | null;
  flags?: string[] | null;
  preview?: string | null;
};

export type Label = {
  id: string;
  name: string;
  color: string;
  created_at: string;
};

export type RuleCondition = {
  field: string;
  op: string;
  value?: string | null;
};

export type RuleAction = {
  type: string;
  value?: string | null;
};

export type Rule = {
  id: string;
  mailbox_id: string;
  name: string;
  is_active: boolean;
  priority: number;
  match_type: string;
  conditions: RuleCondition[];
  actions: RuleAction[];
  created_at: string;
};

export type Template = {
  id: string;
  mailbox_id: string;
  name: string;
  subject: string;
  body_text?: string | null;
  body_html?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type AiSummaryResponse = {
  summary: string;
};

export type AiSmartReplyResponse = {
  suggestions: string[];
};

export type AiPriorityEmail = {
  uid: number | string;
  from?: string | null;
  subject?: string | null;
  preview?: string | null;
  date?: string | null;
  priority_score?: number | null;
};

export type AiPriorityInboxResponse = {
  emails: AiPriorityEmail[];
};

export type CalendarEvent = {
  id: string;
  mailbox_id: string;
  uid: string;
  title: string;
  description?: string | null;
  location?: string | null;
  start_at: string;
  end_at: string;
  all_day: boolean;
  rrule?: string | null;
  attendees?: { email?: string; name?: string }[];
  linked_email_uid?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type TaskItem = {
  id: string;
  mailbox_id: string;
  title: string;
  description?: string | null;
  due_at?: string | null;
  is_completed: boolean;
  completed_at?: string | null;
  priority: string;
  linked_email_uid?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type NoteItem = {
  id: string;
  mailbox_id: string;
  title?: string | null;
  body: string;
  linked_email_uid?: string | null;
  created_at: string;
  updated_at?: string | null;
};

export type SharedMailbox = {
  id: string;
  mailbox_id: string;
  domain_id: string;
  display_name: string;
  created_at: string;
};

export type DelegationRecord = {
  id: string;
  owner_mailbox_id: string;
  delegate_user_id: string;
  permission: string;
  created_at: string;
};

export type ApiKey = {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  rate_limit_per_hour: number;
  last_used_at?: string | null;
  expires_at?: string | null;
  is_active: boolean;
  created_at: string;
};

export type ApiKeyCreated = {
  id: string;
  key: string;
  prefix: string;
};

export type CampaignRecipient = {
  email: string;
  name?: string | null;
  vars?: Record<string, string> | null;
};

export type Campaign = {
  id: string;
  mailbox_id: string;
  name: string;
  subject: string;
  body_html: string;
  body_text?: string | null;
  from_name?: string | null;
  recipients: CampaignRecipient[];
  status: string;
  scheduled_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  total_recipients?: number | null;
  sent_count?: number | null;
  failed_count?: number | null;
  open_count?: number | null;
  click_count?: number | null;
  unsubscribe_count?: number | null;
  created_at: string;
};

export type CampaignAnalytics = {
  sent: number;
  opens: number;
  unique_opens: number;
  clicks: number;
  unique_clicks: number;
  unsubscribes: number;
  open_rate: number;
  click_rate: number;
};

export type Webhook = {
  id: string;
  mailbox_id: string;
  url: string;
  secret: string;
  events: string[];
  is_active: boolean;
  last_triggered_at?: string | null;
  failure_count: number;
  created_at: string;
};

export type EdiscoveryExport = {
  id: string;
  domain_id: string;
  requested_by?: string | null;
  query: Record<string, unknown>;
  status: string;
  file_path?: string | null;
  total_messages: number;
  created_at: string;
  completed_at?: string | null;
};

export type Whitelabel = {
  logo_url?: string | null;
  primary_color?: string | null;
  company_name?: string | null;
};
