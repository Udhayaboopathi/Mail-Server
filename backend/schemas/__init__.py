from schemas.alias import AliasRead
from schemas.alias import AliasCreateRequest, AliasRead, AliasUpdateRequest
from schemas.admin import AdminLogsResponse, AdminStatsResponse
from schemas.auth import TokenPair, LoginRequest, RefreshRequest, LogoutRequest
from schemas.auth_extended import (
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    TotpSetupResponse,
    TotpCodeRequest,
    TotpDisableRequest,
    TotpVerifyResponse,
    LoginActivityItem,
)
from schemas.audit import AuditLogRead
from schemas.common import ActionResponse
from schemas.domain import DomainCreate, DomainRead, DNSRecordsResponse
from schemas.mail import AttachmentInput, MailMessageRead, MailSendRequest, MailSummary, FolderListResponse, SearchResponse
from schemas.mail import AttachmentInput, MailFlagsRequest, MailMessageRead, MailMoveRequest, MailSendRequest, MailSummary, FolderListResponse, SearchResponse
from schemas.folder import FolderCreateRequest, FolderListResponse, FolderRenameRequest
from schemas.mailbox import MailboxCreate, MailboxRead, MailboxUpdate
from schemas.pgp import PgpGenerateRequest, PgpKeyResponse, PgpPublicKeyResponse
from schemas.threads import ThreadSummary, ThreadMessage, ThreadLabel
from schemas.labels import LabelCreateRequest, LabelUpdateRequest, LabelResponse
from schemas.rules import RuleCreateRequest, RuleUpdateRequest, RuleResponse, RuleTestResult
from schemas.templates import TemplateCreateRequest, TemplateUpdateRequest, TemplateResponse
from schemas.ai import (
    AiSummarizeRequest,
    AiSummarizeResponse,
    AiSmartReplyRequest,
    AiSmartReplyResponse,
    AiPriorityInboxResponse,
    AiSuggestLabelsRequest,
    AiSuggestLabelsResponse,
)
from schemas.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse
from schemas.tasks import TaskCreateRequest, TaskUpdateRequest, TaskResponse
from schemas.notes import NoteCreateRequest, NoteUpdateRequest, NoteResponse
from schemas.shared_mailboxes import SharedMailboxCreateRequest, SharedMailboxMemberRequest, SharedMailboxResponse
from schemas.delegation import DelegationGrantRequest, DelegationRecord
from schemas.api_keys import ApiKeyCreateRequest, ApiKeyResponse, ApiKeyCreatedResponse
from schemas.send_api import SendApiRequest, SendApiResponse
from schemas.campaigns import CampaignCreateRequest, CampaignUpdateRequest, CampaignListItem, CampaignRecipientList
from schemas.webhooks import WebhookCreateRequest, WebhookUpdateRequest, WebhookResponse
from schemas.spam_reports import SpamReportRequest, SpamReportResponse
from schemas.ediscovery import EdiscoveryExportCreate, EdiscoveryExportListItem
from schemas.whitelabel import WhitelabelResponse, WhitelabelUpdateRequest
from schemas.user import UserCreate, UserRead, UserUpdate

__all__ = [
    "TokenPair",
    "LoginRequest",
    "RefreshRequest",
    "LogoutRequest",
    "ActionResponse",
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "DomainCreate",
    "DomainRead",
    "DNSRecordsResponse",
    "MailboxCreate",
    "MailboxRead",
    "MailboxUpdate",
    "AliasRead",
    "AliasCreateRequest",
    "AliasUpdateRequest",
    "MailSummary",
    "MailMessageRead",
    "MailSendRequest",
    "AttachmentInput",
    "MailFlagsRequest",
    "MailMoveRequest",
    "FolderListResponse",
    "FolderCreateRequest",
    "FolderRenameRequest",
    "SearchResponse",
    "AuditLogRead",
    "AdminStatsResponse",
    "AdminLogsResponse",
    "PasswordResetRequest",
    "PasswordResetConfirmRequest",
    "TotpSetupResponse",
    "TotpCodeRequest",
    "TotpDisableRequest",
    "TotpVerifyResponse",
    "LoginActivityItem",
    "PgpGenerateRequest",
    "PgpKeyResponse",
    "PgpPublicKeyResponse",
    "ThreadSummary",
    "ThreadMessage",
    "ThreadLabel",
    "LabelCreateRequest",
    "LabelUpdateRequest",
    "LabelResponse",
    "RuleCreateRequest",
    "RuleUpdateRequest",
    "RuleResponse",
    "RuleTestResult",
    "TemplateCreateRequest",
    "TemplateUpdateRequest",
    "TemplateResponse",
    "AiSummarizeRequest",
    "AiSummarizeResponse",
    "AiSmartReplyRequest",
    "AiSmartReplyResponse",
    "AiPriorityInboxResponse",
    "AiSuggestLabelsRequest",
    "AiSuggestLabelsResponse",
    "CalendarEventCreate",
    "CalendarEventUpdate",
    "CalendarEventResponse",
    "TaskCreateRequest",
    "TaskUpdateRequest",
    "TaskResponse",
    "NoteCreateRequest",
    "NoteUpdateRequest",
    "NoteResponse",
    "SharedMailboxCreateRequest",
    "SharedMailboxMemberRequest",
    "SharedMailboxResponse",
    "DelegationGrantRequest",
    "DelegationRecord",
    "ApiKeyCreateRequest",
    "ApiKeyResponse",
    "ApiKeyCreatedResponse",
    "SendApiRequest",
    "SendApiResponse",
    "CampaignCreateRequest",
    "CampaignUpdateRequest",
    "CampaignListItem",
    "CampaignRecipientList",
    "WebhookCreateRequest",
    "WebhookUpdateRequest",
    "WebhookResponse",
    "SpamReportRequest",
    "SpamReportResponse",
    "EdiscoveryExportCreate",
    "EdiscoveryExportListItem",
    "WhitelabelResponse",
    "WhitelabelUpdateRequest",
]
