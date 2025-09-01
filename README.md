# Ping SSO Onboarding Agent

A Natural-Language Agent that automates the Ping SSO onboarding workflow with typed, evidence-backed state management.

## Overview

The Ping SSO Onboarding Agent streamlines the process of onboarding new clients to Ping SSO across multiple environments (Dev → Staging → Prod). It handles ticket creation, access provisioning, evidence collection, and approval workflows through a deterministic state machine.

## Features

- **Natural Language Commands**: "Onboard Galaxy", "Status of BusinessBanking", "Move Galaxy to Staging"
- **State Machine**: Typed environment states with evidence-backed transitions
- **HITL Gates**: Human-in-the-loop approvals for critical steps
- **Evidence Tracking**: Screenshots, tickets, secrets, and email artifacts
- **Observability**: Langfuse integration for LLM observability and tracing
- **Security**: PII redaction, masked secrets, RBAC

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   PydanticAI    │    │   PostgreSQL    │
│   /agent/command│◄──►│   Agent + Tools │◄──►│   Threads/State │
│   /threads/{id} │    │   State Machine │    │   Evidence      │
│   /webhooks/*   │    │                 │    │   Audit Log     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   External      │    │   AWS Services  │    │   Observability │
│   ServiceNow    │    │   Secrets Mgr   │    │   Langfuse      │
│   Jira          │    │   S3            │    │   OpenTelemetry │
│   SMTP/Graph    │    │   CloudWatch    │    │   Structured    │
│   LDAP/Graph    │    │                 │    │   Logs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## State Machine

```
NotStarted → FormsRaised → CredsIssued → AccessProvisioned → Validated → SignoffSent → Approved → Complete
     ↓           ↓            ↓              ↓              ↓            ↓           ↓
  Blocked    Blocked      Blocked        Blocked        Blocked     Blocked    Blocked
     ↓           ↓            ↓              ↓              ↓            ↓           ↓
ChangesRequested ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ← ←
     ↓
  Abandoned
```

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Setup**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Database Setup**:
   ```bash
   alembic upgrade head
   ```

4. **Run the Application**:
   ```bash
   uvicorn app.main:app --reload
   ```

5. **Test Commands**:
   ```bash
   # Onboard a new client
   curl -X POST "http://localhost:8000/agent/command" \
        -H "Content-Type: application/json" \
        -d '{"text": "Onboard Galaxy"}'
   
   # Check status
   curl -X POST "http://localhost:8000/agent/command" \
        -H "Content-Type: application/json" \
        -d '{"text": "Status of Galaxy"}'
   ```

## API Endpoints

- `POST /agent/command` - Natural language commands
- `GET /threads/{thread_id}` - Thread status and evidence
- `POST /webhooks/ticketing` - Ticket status updates
- `POST /webhooks/email` - Email replies

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/pingsso

# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1

# Langfuse
LANGFUSE_SECRET_KEY=your_key
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_HOST=https://cloud.langfuse.com

# External Services
SERVICENOW_URL=https://your-instance.service-now.com
SERVICENOW_USERNAME=your_user
SERVICENOW_PASSWORD=your_pass

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
```

## Development

### Running Tests
```bash
pytest
```

### Database Migrations
```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Code Formatting
```bash
black .
isort .
```

## Security

- All secrets are stored in AWS Secrets Manager
- PII is redacted in logs and traces
- RBAC controls access to threads and operations
- Signed URLs for sensitive artifacts

## Monitoring

- **Langfuse**: LLM observability, prompt management, experiments
- **OpenTelemetry**: Distributed tracing and metrics
- **CloudWatch**: Application logs and alarms
- **Custom Dashboards**: State transition errors, SLA violations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

Internal use only - GenAI Platform Team
