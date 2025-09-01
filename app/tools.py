from typing import List, Optional, Dict, Any
from datetime import datetime
import boto3
import httpx
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import hashlib
import secrets

from pydantic_ai import tool
from pydantic_ai import RunContext

from app.models import (
    EnvName, TicketRef, SecretRef, ScreenshotRef, Evidence, 
    RedirectUris, PeopleSet, EnvState, ClientThread, AuditLog,
    AppConfig
)
from app.state_machine import StateMachine


class CtxState:
    """Context state for tool execution."""
    def __init__(self, user: str, config: AppConfig, thread_repo=None):
        self.user = user
        self.config = config
        self.thread_repo = thread_repo


@tool
async def create_nssr_ticket(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName, 
    redirect_uris: RedirectUris
) -> TicketRef:
    """Create an NSSR/OAuth ticket for the given environment and client."""
    
    # Generate ticket ID (in real implementation, this would call ServiceNow/Jira)
    ticket_id = f"SN-{secrets.token_hex(4).upper()}"
    
    # Create ticket via external system
    if ctx.config.servicenow_url:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{ctx.config.servicenow_url}/api/now/table/incident",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {ctx.config.servicenow_username}:{ctx.config.servicenow_password}"
                },
                json={
                    "short_description": f"NSSR/OAuth Request for {client} - {env}",
                    "description": f"Request for client credentials for {client} in {env} environment",
                    "category": "request",
                    "subcategory": "oauth",
                    "caller_id": ctx.user,
                    "custom_fields": {
                        "client_name": client,
                        "environment": env.value,
                        "redirect_uris": redirect_uris.model_dump()
                    }
                }
            )
            if response.status_code == 201:
                ticket_data = response.json()
                ticket_id = ticket_data["result"]["number"]
    
    return TicketRef(
        system="ServiceNow",
        id=ticket_id,
        url=f"{ctx.config.servicenow_url}/nav_to.do?uri=incident.do?sys_id={ticket_id}",
        kind="NSSR",
        status="open"
    )


@tool
async def create_glam_gwam_ticket(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName, 
    lanids: List[str]
) -> TicketRef:
    """Create GLAM/GWAM request to add users for the environment."""
    
    # Generate ticket ID
    ticket_id = f"GW-{secrets.token_hex(4).upper()}"
    
    # Create ticket via external system
    if ctx.config.servicenow_url:
        async with httpx.AsyncClient() as http_client:
            response = await http_client.post(
                f"{ctx.config.servicenow_url}/api/now/table/incident",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Basic {ctx.config.servicenow_username}:{ctx.config.servicenow_password}"
                },
                json={
                    "short_description": f"GLAM/GWAM Request for {client} - {env}",
                    "description": f"Request to add users {lanids} for {client} in {env} environment",
                    "category": "request",
                    "subcategory": "access",
                    "caller_id": ctx.user,
                    "custom_fields": {
                        "client_name": client,
                        "environment": env.value,
                        "lanids": lanids
                    }
                }
            )
            if response.status_code == 201:
                ticket_data = response.json()
                ticket_id = ticket_data["result"]["number"]
    
    return TicketRef(
        system="ServiceNow",
        id=ticket_id,
        url=f"{ctx.config.servicenow_url}/nav_to.do?uri=incident.do?sys_id={ticket_id}",
        kind="GLAM",
        status="open"
    )


@tool
async def store_client_secret(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName, 
    secret: str
) -> SecretRef:
    """Store client secret in AWS Secrets Manager and return masked reference."""
    
    secret_name = f"{ctx.config.secrets_manager_prefix}/{client}/{env}/client_secret"
    mask = f"****{secret[-4:]}" if len(secret) >= 4 else "****"
    
    # Store in AWS Secrets Manager
    try:
        secrets_client = boto3.client('secretsmanager', region_name=ctx.config.aws_region)
        secrets_client.create_secret(
            Name=secret_name,
            SecretString=secret,
            Description=f"Client secret for {client} in {env} environment"
        )
    except Exception as e:
        # In development, just log the secret (don't do this in production!)
        print(f"Would store secret {secret_name}: {mask}")
    
    return SecretRef(
        name=secret_name,
        mask=mask
    )


@tool
async def send_signoff_email(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName, 
    screenshots: List[ScreenshotRef], 
    redirect_uris: RedirectUris,
    approvers: List[str]
) -> str:
    """Compose and send sign-off email with screenshots and redirect URIs."""
    
    # Generate message ID
    message_id = f"<{secrets.token_hex(8)}@pingsso.agent>"
    
    # Compose email
    subject = f"Ping SSO {env.value.title()} Sign-off for {client}"
    
    body = f"""
Hi Ping Team,

{env.value.title()} validation for {client} is complete. Please find attached the required 4 screenshots and the requested redirect URIs for the next environment.

Redirect URIs:
- Web Callback: {redirect_uris.web_callback}
"""
    
    if redirect_uris.post_logout:
        body += f"- Post Logout: {redirect_uris.post_logout}\n"
    
    if redirect_uris.api_callback:
        body += f"- API Callback: {redirect_uris.api_callback}\n"
    
    body += f"""
Screenshots (required 4):
"""
    
    for screenshot in screenshots:
        body += f"- {screenshot.label}: {screenshot.url}\n"
    
    body += f"""
Please review and approve to proceed to the next environment.

Thanks,
{ctx.user}
"""
    
    # Send email
    if ctx.config.smtp_host:
        try:
            msg = MIMEMultipart()
            msg['From'] = ctx.config.smtp_username
            msg['To'] = ", ".join(approvers)
            msg['Subject'] = subject
            msg['Message-ID'] = message_id
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(ctx.config.smtp_host, ctx.config.smtp_port)
            server.starttls()
            server.login(ctx.config.smtp_username, ctx.config.smtp_password)
            server.send_message(msg)
            server.quit()
            
        except Exception as e:
            print(f"Failed to send email: {e}")
            # In development, just log
            print(f"Would send email to {approvers}: {subject}")
    
    return message_id


@tool
async def update_env_state(
    ctx: RunContext[CtxState], 
    thread_id: str, 
    env: EnvName, 
    new_state: EnvState, 
    evidence: Evidence,
    reason: str = ""
) -> bool:
    """Update environment state and evidence atomically."""
    
    if not ctx.thread_repo:
        raise ValueError("Thread repository not available")
    
    # Get current thread
    thread = await ctx.thread_repo.get_thread(thread_id)
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")
    
    # Get current environment
    env_obj = thread.environments.get(env)
    if not env_obj:
        raise ValueError(f"Environment {env} not found in thread {thread_id}")
    
    # Validate transition
    is_valid, errors = StateMachine.validate_transition(
        env_obj.state, new_state, env, evidence, thread
    )
    
    if not is_valid:
        raise ValueError(f"Invalid state transition: {errors}")
    
    # Update environment
    env_obj.state = new_state
    env_obj.evidence = evidence
    env_obj.last_updated = datetime.utcnow()
    
    # Update thread
    thread.last_update = datetime.utcnow()
    
    # Update blockers and next actions
    thread.blockers = []
    thread.next_actions = []
    
    for env_name, env_data in thread.environments.items():
        blockers = StateMachine.get_blockers(env_data, thread)
        actions = StateMachine.get_next_actions(env_data, thread)
        
        thread.blockers.extend(blockers)
        thread.next_actions.extend(actions)
    
    # Persist changes
    await ctx.thread_repo.update_thread(thread)
    
    # Add audit log
    audit_log = AuditLog(
        thread_id=thread_id,
        actor=ctx.user,
        action="state_transition",
        details={
            "environment": env.value,
            "from_state": env_obj.state.value,
            "to_state": new_state.value,
            "reason": reason,
            "evidence_count": len(evidence.tickets) + len(evidence.screenshots) + len(evidence.emails)
        }
    )
    await ctx.thread_repo.add_audit_log(audit_log)
    
    return True


@tool
async def generate_redirect_uris(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName
) -> RedirectUris:
    """Generate redirect URIs for the client and environment."""
    
    base_url = f"https://{env.value}.{client.lower()}.ourdomain.com"
    
    return RedirectUris(
        web_callback=f"{base_url}/api/auth/callback/ping",
        post_logout=f"{base_url}/auth/logout/callback",
        api_callback=f"{base_url}/api/auth/callback/ping"
    )


@tool
async def upload_screenshot(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName, 
    label: str, 
    file_content: bytes
) -> ScreenshotRef:
    """Upload screenshot to S3 and return reference."""
    
    # Generate S3 key
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"screenshots/{client}/{env}/{label}_{timestamp}.png"
    
    # Upload to S3
    try:
        s3_client = boto3.client('s3', region_name=ctx.config.aws_region)
        s3_client.put_object(
            Bucket=ctx.config.s3_bucket,
            Key=key,
            Body=file_content,
            ContentType='image/png'
        )
        
        # Generate signed URL
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': ctx.config.s3_bucket, 'Key': key},
            ExpiresIn=3600  # 1 hour
        )
        
    except Exception as e:
        print(f"Failed to upload to S3: {e}")
        # In development, just return a mock URL
        url = f"https://mock-s3.amazonaws.com/{ctx.config.s3_bucket}/{key}"
    
    return ScreenshotRef(
        key=key,
        label=label,
        url=url
    )


@tool
async def get_thread_status(
    ctx: RunContext[CtxState], 
    thread_id: str
) -> Dict[str, Any]:
    """Get comprehensive status of a client thread."""
    
    if not ctx.thread_repo:
        raise ValueError("Thread repository not available")
    
    thread = await ctx.thread_repo.get_thread(thread_id)
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")
    
    # Calculate progress
    progress = StateMachine.calculate_progress(thread)
    current_env = StateMachine.get_current_environment(thread)
    
    # Build status summary
    status_summary = {
        "thread_id": thread.thread_id,
        "display_name": thread.display_name,
        "owner": thread.owner,
        "created_at": thread.created_at.isoformat(),
        "last_update": thread.last_update.isoformat(),
        "overall_progress": progress,
        "current_environment": current_env.value if current_env else None,
        "blockers": thread.blockers,
        "next_actions": thread.next_actions,
        "environments": {}
    }
    
    for env_name, env in thread.environments.items():
        status_summary["environments"][env_name.value] = {
            "state": env.state.value,
            "last_updated": env.last_updated.isoformat(),
            "evidence": {
                "tickets": len(env.evidence.tickets),
                "screenshots": len(env.evidence.screenshots),
                "emails": len(env.evidence.emails),
                "has_secret": env.evidence.secret is not None
            },
            "redirect_uris": env.redirect_uris.model_dump() if env.redirect_uris else None,
            "people": {
                "lanids": env.people.lanids,
                "approvers": env.people.approvers,
                "contacts": env.people.contacts
            }
        }
    
    return status_summary


@tool
async def create_client_thread(
    ctx: RunContext[CtxState], 
    display_name: str, 
    owner: str,
    lanids: List[str] = None
) -> str:
    """Create a new client thread for onboarding."""
    
    if not ctx.thread_repo:
        raise ValueError("Thread repository not available")
    
    from app.models import ClientThread
    
    thread = ClientThread(
        display_name=display_name,
        owner=owner,
        created_by=ctx.user
    )
    
    # Add LANIDs to Dev environment
    if lanids:
        thread.environments[EnvName.dev].people.lanids = lanids
    
    # Persist thread
    await ctx.thread_repo.create_thread(thread)
    
    # Add audit log
    audit_log = AuditLog(
        thread_id=thread.thread_id,
        actor=ctx.user,
        action="thread_created",
        details={
            "display_name": display_name,
            "owner": owner,
            "lanids": lanids or []
        }
    )
    await ctx.thread_repo.add_audit_log(audit_log)
    
    return thread.thread_id
