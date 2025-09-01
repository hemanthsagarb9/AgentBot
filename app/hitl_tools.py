"""
Enhanced tools with explicit HITL gates for Ping SSO Onboarding Agent.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from pydantic_ai import tool
from pydantic_ai import RunContext

from app.models import (
    EnvName, TicketRef, SecretRef, ScreenshotRef, Evidence, 
    RedirectUris, EnvState, ClientThread, AuditLog
)
from app.tools import CtxState
from app.state_machine import StateMachine
from app.hitl import HITLManager, ApprovalType, requires_approval


@tool
@requires_approval(
    approval_type=ApprovalType.ticket_creation,
    approvers=["ping-admin@company.com", "security-team@company.com"],
    timeout_hours=24
)
async def create_nssr_ticket_with_approval(
    ctx: RunContext[CtxState], 
    client: str, 
    env: EnvName, 
    redirect_uris: RedirectUris
) -> TicketRef:
    """Create an NSSR/OAuth ticket with human approval gate."""
    
    print(f"🎫 Creating NSSR ticket for {client} in {env} environment")
    print(f"📍 Redirect URIs: {redirect_uris.web_callback}")
    
    # Generate ticket ID (in real implementation, this would call ServiceNow/Jira)
    import secrets
    ticket_id = f"SN-{secrets.token_hex(4).upper()}"
    
    return TicketRef(
        system="ServiceNow",
        id=ticket_id,
        url=f"https://servicenow.company.com/incident.do?sys_id={ticket_id}",
        kind="NSSR",
        status="open"
    )


@tool
@requires_approval(
    approval_type=ApprovalType.environment_progression,
    approvers=["ping-admin@company.com", "devops-team@company.com"],
    timeout_hours=48
)
async def advance_environment_with_approval(
    ctx: RunContext[CtxState],
    thread_id: str,
    env: EnvName,
    target_state: EnvState,
    evidence: Evidence,
    reason: str = ""
) -> bool:
    """Advance environment state with human approval gate."""
    
    print(f"🚀 Advancing {env} environment to {target_state}")
    print(f"📋 Evidence: {len(evidence.tickets)} tickets, {len(evidence.screenshots)} screenshots")
    
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
        env_obj.state, target_state, env, evidence, thread
    )
    
    if not is_valid:
        raise ValueError(f"Invalid state transition: {errors}")
    
    # Update environment
    env_obj.state = target_state
    env_obj.evidence = evidence
    env_obj.last_updated = datetime.utcnow()
    
    # Update thread
    thread.last_update = datetime.utcnow()
    
    # Persist changes
    await ctx.thread_repo.update_thread(thread)
    
    # Add audit log
    audit_log = AuditLog(
        thread_id=thread_id,
        actor=ctx.user,
        action="state_transition_approved",
        details={
            "environment": env.value,
            "from_state": env_obj.state.value,
            "to_state": target_state.value,
            "reason": reason,
            "approval_required": True
        }
    )
    await ctx.thread_repo.add_audit_log(audit_log)
    
    print(f"✅ Environment {env} advanced to {target_state}")
    return True


@tool
@requires_approval(
    approval_type=ApprovalType.production_deployment,
    approvers=["ping-admin@company.com", "security-team@company.com", "cto@company.com"],
    timeout_hours=72
)
async def deploy_to_production_with_approval(
    ctx: RunContext[CtxState],
    thread_id: str,
    client: str
) -> Dict[str, Any]:
    """Deploy to production with executive approval gate."""
    
    print(f"🚀 PRODUCTION DEPLOYMENT for {client}")
    print(f"⚠️  This requires executive approval!")
    
    if not ctx.thread_repo:
        raise ValueError("Thread repository not available")
    
    # Get thread
    thread = await ctx.thread_repo.get_thread(thread_id)
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")
    
    # Validate all environments are complete
    for env_name, env in thread.environments.items():
        if env_name != EnvName.prod and env.state != EnvState.complete:
            raise ValueError(f"Environment {env_name} must be complete before production deployment")
    
    # Create production deployment record
    deployment_record = {
        "client": client,
        "thread_id": thread_id,
        "deployed_at": datetime.utcnow().isoformat(),
        "deployed_by": ctx.user,
        "environments": {
            env_name.value: {
                "state": env.state.value,
                "evidence_count": len(env.evidence.tickets) + len(env.evidence.screenshots)
            }
            for env_name, env in thread.environments.items()
        }
    }
    
    # Add audit log
    audit_log = AuditLog(
        thread_id=thread_id,
        actor=ctx.user,
        action="production_deployment_approved",
        details=deployment_record
    )
    await ctx.thread_repo.add_audit_log(audit_log)
    
    print(f"✅ Production deployment approved for {client}")
    return deployment_record


@tool
async def get_approval_status(
    ctx: RunContext[CtxState],
    thread_id: str
) -> Dict[str, Any]:
    """Get current approval status for a thread."""
    
    hitl_manager = HITLManager(ctx.thread_repo)
    
    # Get pending approvals
    pending_approvals = await hitl_manager.get_pending_approvals(thread_id)
    
    # Get approval summary
    summary = hitl_manager.get_approval_summary(thread_id)
    
    return {
        "thread_id": thread_id,
        "summary": summary,
        "pending_approvals": [
            {
                "id": approval.id,
                "type": approval.approval_type.value,
                "environment": approval.environment.value,
                "title": approval.title,
                "description": approval.description,
                "approvers": approval.approvers,
                "created_at": approval.created_at.isoformat(),
                "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
                "status": approval.status.value
            }
            for approval in pending_approvals
        ]
    }


@tool
async def escalate_approval(
    ctx: RunContext[CtxState],
    approval_id: str,
    escalation_reason: str
) -> bool:
    """Escalate an approval request."""
    
    print(f"🚨 Escalating approval {approval_id}")
    print(f"📝 Reason: {escalation_reason}")
    
    # In real implementation, this would:
    # 1. Send urgent notifications to managers
    # 2. Create high-priority tickets
    # 3. Update approval timeout
    # 4. Log escalation
    
    # For demo, just log the escalation
    print(f"✅ Approval {approval_id} escalated successfully")
    return True


@tool
async def create_emergency_approval(
    ctx: RunContext[CtxState],
    thread_id: str,
    environment: EnvName,
    emergency_type: str,
    justification: str,
    emergency_approvers: List[str]
) -> str:
    """Create an emergency approval with reduced timeout."""
    
    print(f"🚨 EMERGENCY APPROVAL for {thread_id}")
    print(f"⚠️  Type: {emergency_type}")
    print(f"📝 Justification: {justification}")
    print(f"👥 Emergency Approvers: {', '.join(emergency_approvers)}")
    
    hitl_manager = HITLManager(ctx.thread_repo)
    
    approval = await hitl_manager.create_approval_request(
        thread_id=thread_id,
        environment=environment,
        approval_type=ApprovalType.environment_progression,
        title=f"EMERGENCY: {emergency_type}",
        description=f"Emergency approval required: {justification}",
        approvers=emergency_approvers,
        evidence={
            "emergency_type": emergency_type,
            "justification": justification,
            "requested_by": ctx.user,
            "emergency": True
        },
        timeout_hours=4  # Reduced timeout for emergencies
    )
    
    print(f"✅ Emergency approval {approval.id} created with 4-hour timeout")
    return approval.id
