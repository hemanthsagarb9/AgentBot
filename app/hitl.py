"""
Human-in-the-Loop (HITL) Management for Ping SSO Onboarding Agent

This module provides explicit HITL gates and approval workflows.
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field

from app.models import EnvName, EnvState, ClientThread, AuditLog


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class ApprovalType(str, Enum):
    ticket_creation = "ticket_creation"
    environment_progression = "environment_progression"
    production_deployment = "production_deployment"
    credential_issuance = "credential_issuance"


class ApprovalRequest(BaseModel):
    """Represents a human approval request."""
    id: str = Field(default_factory=lambda: f"approval-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    thread_id: str
    environment: EnvName
    approval_type: ApprovalType
    title: str
    description: str
    approvers: List[str]
    evidence: Dict[str, Any] = Field(default_factory=dict)
    status: ApprovalStatus = ApprovalStatus.pending
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


class HITLManager:
    """Manages human-in-the-loop approval workflows."""
    
    def __init__(self, thread_repo=None):
        self.thread_repo = thread_repo
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        self.approval_timeout_hours = 48  # SLA timeout
    
    async def create_approval_request(
        self,
        thread_id: str,
        environment: EnvName,
        approval_type: ApprovalType,
        title: str,
        description: str,
        approvers: List[str],
        evidence: Dict[str, Any] = None,
        timeout_hours: int = 48
    ) -> ApprovalRequest:
        """Create a new approval request."""
        
        approval = ApprovalRequest(
            thread_id=thread_id,
            environment=environment,
            approval_type=approval_type,
            title=title,
            description=description,
            approvers=approvers,
            evidence=evidence or {},
            expires_at=datetime.utcnow() + timedelta(hours=timeout_hours)
        )
        
        self.pending_approvals[approval.id] = approval
        
        # Log approval request
        if self.thread_repo:
            audit_log = AuditLog(
                thread_id=thread_id,
                actor="system",
                action="approval_requested",
                details={
                    "approval_id": approval.id,
                    "approval_type": approval_type.value,
                    "environment": environment.value,
                    "approvers": approvers,
                    "expires_at": approval.expires_at.isoformat()
                }
            )
            await self.thread_repo.add_audit_log(audit_log)
        
        return approval
    
    async def approve_request(
        self,
        approval_id: str,
        approver: str,
        comments: str = ""
    ) -> bool:
        """Approve a pending request."""
        
        if approval_id not in self.pending_approvals:
            return False
        
        approval = self.pending_approvals[approval_id]
        
        if approval.status != ApprovalStatus.pending:
            return False
        
        if approval.expires_at and datetime.utcnow() > approval.expires_at:
            approval.status = ApprovalStatus.expired
            return False
        
        # Update approval
        approval.status = ApprovalStatus.approved
        approval.approved_by = approver
        approval.approved_at = datetime.utcnow()
        
        # Log approval
        if self.thread_repo:
            audit_log = AuditLog(
                thread_id=approval.thread_id,
                actor=approver,
                action="approval_granted",
                details={
                    "approval_id": approval_id,
                    "approval_type": approval.approval_type.value,
                    "environment": approval.environment.value,
                    "comments": comments
                }
            )
            await self.thread_repo.add_audit_log(audit_log)
        
        return True
    
    async def reject_request(
        self,
        approval_id: str,
        approver: str,
        reason: str
    ) -> bool:
        """Reject a pending request."""
        
        if approval_id not in self.pending_approvals:
            return False
        
        approval = self.pending_approvals[approval_id]
        
        if approval.status != ApprovalStatus.pending:
            return False
        
        # Update approval
        approval.status = ApprovalStatus.rejected
        approval.approved_by = approver
        approval.approved_at = datetime.utcnow()
        approval.rejection_reason = reason
        
        # Log rejection
        if self.thread_repo:
            audit_log = AuditLog(
                thread_id=approval.thread_id,
                actor=approver,
                action="approval_rejected",
                details={
                    "approval_id": approval_id,
                    "approval_type": approval.approval_type.value,
                    "environment": approval.environment.value,
                    "reason": reason
                }
            )
            await self.thread_repo.add_audit_log(audit_log)
        
        return True
    
    async def get_pending_approvals(self, thread_id: str = None) -> List[ApprovalRequest]:
        """Get pending approvals, optionally filtered by thread."""
        
        approvals = list(self.pending_approvals.values())
        
        if thread_id:
            approvals = [a for a in approvals if a.thread_id == thread_id]
        
        # Filter out expired approvals
        now = datetime.utcnow()
        valid_approvals = []
        
        for approval in approvals:
            if approval.expires_at and now > approval.expires_at:
                approval.status = ApprovalStatus.expired
            valid_approvals.append(approval)
        
        return [a for a in valid_approvals if a.status == ApprovalStatus.pending]
    
    async def check_expired_approvals(self) -> List[ApprovalRequest]:
        """Check for expired approvals and update their status."""
        
        expired = []
        now = datetime.utcnow()
        
        for approval in self.pending_approvals.values():
            if (approval.status == ApprovalStatus.pending and 
                approval.expires_at and 
                now > approval.expires_at):
                
                approval.status = ApprovalStatus.expired
                expired.append(approval)
                
                # Log expiration
                if self.thread_repo:
                    audit_log = AuditLog(
                        thread_id=approval.thread_id,
                        actor="system",
                        action="approval_expired",
                        details={
                            "approval_id": approval.id,
                            "approval_type": approval.approval_type.value,
                            "environment": approval.environment.value,
                            "expired_at": now.isoformat()
                        }
                    )
                    await self.thread_repo.add_audit_log(audit_log)
        
        return expired
    
    def get_approval_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get approval summary for a thread."""
        
        thread_approvals = [a for a in self.pending_approvals.values() if a.thread_id == thread_id]
        
        return {
            "total_approvals": len(thread_approvals),
            "pending": len([a for a in thread_approvals if a.status == ApprovalStatus.pending]),
            "approved": len([a for a in thread_approvals if a.status == ApprovalStatus.approved]),
            "rejected": len([a for a in thread_approvals if a.status == ApprovalStatus.rejected]),
            "expired": len([a for a in thread_approvals if a.status == ApprovalStatus.expired]),
            "approvals": [
                {
                    "id": a.id,
                    "type": a.approval_type.value,
                    "environment": a.environment.value,
                    "title": a.title,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat(),
                    "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                    "approvers": a.approvers
                }
                for a in thread_approvals
            ]
        }


# HITL Gate Decorators
def requires_approval(approval_type: ApprovalType, approvers: List[str], timeout_hours: int = 48):
    """Decorator to require human approval before executing a function."""
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract context from arguments
            ctx = None
            for arg in args:
                if hasattr(arg, 'user') and hasattr(arg, 'config'):
                    ctx = arg
                    break
            
            if not ctx:
                raise ValueError("Context not found in function arguments")
            
            # Create approval request
            hitl_manager = HITLManager(ctx.thread_repo)
            
            approval = await hitl_manager.create_approval_request(
                thread_id=kwargs.get('thread_id', 'unknown'),
                environment=kwargs.get('env', EnvName.dev),
                approval_type=approval_type,
                title=f"Approval required for {func.__name__}",
                description=f"Human approval required before executing {func.__name__}",
                approvers=approvers,
                evidence=kwargs,
                timeout_hours=timeout_hours
            )
            
            # Wait for approval (in real implementation, this would be async polling)
            print(f"⏳ HITL Gate: Waiting for approval {approval.id}")
            print(f"   Approvers: {', '.join(approvers)}")
            print(f"   Expires: {approval.expires_at}")
            
            # For demo purposes, simulate approval after 2 seconds
            await asyncio.sleep(2)
            
            # Simulate approval
            await hitl_manager.approve_request(approval.id, approvers[0], "Auto-approved for demo")
            
            # Execute the original function
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator
