from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl, Field
import uuid


class EnvName(str, Enum):
    dev = 'dev'
    staging = 'staging'
    prod = 'prod'


class EnvState(str, Enum):
    not_started = 'NotStarted'
    forms_raised = 'FormsRaised'
    creds_issued = 'CredsIssued'
    access_provisioned = 'AccessProvisioned'
    validated = 'Validated'
    signoff_sent = 'SignoffSent'
    approved = 'Approved'
    complete = 'Complete'
    blocked = 'Blocked'
    changes_requested = 'ChangesRequested'
    abandoned = 'Abandoned'


class TicketRef(BaseModel):
    system: str  # e.g. 'ServiceNow', 'Jira'
    id: str
    url: Optional[HttpUrl] = None
    kind: str  # 'NSSR', 'OAuth', 'GLAM', 'GWAM'
    status: str = "open"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SecretRef(BaseModel):
    name: str  # secret manager key
    mask: str  # last 4 chars for UI
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScreenshotRef(BaseModel):
    key: str  # s3 key
    label: str  # login, consent, landing, token
    url: Optional[HttpUrl] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class Evidence(BaseModel):
    tickets: List[TicketRef] = []
    secret: Optional[SecretRef] = None
    screenshots: List[ScreenshotRef] = []
    emails: List[str] = []  # message-ids or links
    notes: List[str] = []  # additional context


class RedirectUris(BaseModel):
    web_callback: HttpUrl
    post_logout: Optional[HttpUrl] = None
    api_callback: Optional[HttpUrl] = None


class PeopleSet(BaseModel):
    lanids: List[str] = []  # Dev/Staging only
    approvers: List[str] = []
    contacts: Dict[str, str] = {}  # name->email


class Environment(BaseModel):
    name: EnvName
    state: EnvState = EnvState.not_started
    evidence: Evidence = Evidence()
    redirect_uris: Optional[RedirectUris] = None
    people: PeopleSet = PeopleSet()
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class ClientThread(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    display_name: str  # e.g. 'Galaxy'
    environments: Dict[EnvName, Environment] = Field(default_factory=dict)
    owner: str  # requester
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_update: datetime = Field(default_factory=datetime.utcnow)
    blockers: List[str] = []
    next_actions: List[str] = []
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize environments if not provided
        if not self.environments:
            self.environments = {
                EnvName.dev: Environment(name=EnvName.dev),
                EnvName.staging: Environment(name=EnvName.staging),
                EnvName.prod: Environment(name=EnvName.prod)
            }


class CommandResult(BaseModel):
    message: str
    thread_id: str
    success: bool = True
    details: Dict[str, Any] = Field(default_factory=dict)


class CommandRequest(BaseModel):
    text: str
    user_id: str
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))


class ThreadStatus(BaseModel):
    thread: ClientThread
    summary: str
    current_environment: Optional[EnvName] = None
    overall_progress: float = 0.0  # 0.0 to 1.0


class StateTransition(BaseModel):
    from_state: EnvState
    to_state: EnvState
    environment: EnvName
    evidence: Evidence
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(BaseModel):
    id: Optional[int] = None
    thread_id: str
    actor: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Webhook models
class TicketUpdate(BaseModel):
    ticket_id: str
    system: str
    status: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)


class EmailUpdate(BaseModel):
    message_id: str
    thread_id: str
    subject: str
    sender: str
    received_at: datetime = Field(default_factory=datetime.utcnow)
    content: Optional[str] = None


# Configuration models
class AppConfig(BaseModel):
    database_url: str
    aws_region: str = "us-east-1"
    langfuse_secret_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_host: str = "https://cloud.langfuse.com"
    servicenow_url: Optional[str] = None
    servicenow_username: Optional[str] = None
    servicenow_password: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    s3_bucket: str = "pingsso-artifacts"
    secrets_manager_prefix: str = "pingsso"
