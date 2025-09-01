#!/usr/bin/env python3
"""
Enhanced Demo for Ping SSO Onboarding Agent with HITL (Human-in-the-Loop)

This script demonstrates the HITL approval workflows and gates.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Mock implementations for demo
class MockApprovalRequest:
    def __init__(self, approval_id: str, title: str, approvers: List[str], timeout_hours: int = 48):
        self.id = approval_id
        self.title = title
        self.approvers = approvers
        self.status = "pending"
        self.created_at = datetime.utcnow()
        self.expires_at = datetime.utcnow() + timedelta(hours=timeout_hours)
        self.approved_by = None
        self.approved_at = None

class MockHITLManager:
    """Mock HITL Manager for demo purposes."""
    
    def __init__(self):
        self.approvals: Dict[str, MockApprovalRequest] = {}
        self.approval_counter = 1000
    
    def create_approval(self, title: str, approvers: List[str], timeout_hours: int = 48) -> MockApprovalRequest:
        """Create a mock approval request."""
        self.approval_counter += 1
        approval_id = f"APP-{self.approval_counter}"
        
        approval = MockApprovalRequest(approval_id, title, approvers, timeout_hours)
        self.approvals[approval_id] = approval
        
        return approval
    
    def approve(self, approval_id: str, approver: str) -> bool:
        """Approve a request."""
        if approval_id in self.approvals:
            approval = self.approvals[approval_id]
            approval.status = "approved"
            approval.approved_by = approver
            approval.approved_at = datetime.utcnow()
            return True
        return False
    
    def reject(self, approval_id: str, approver: str, reason: str) -> bool:
        """Reject a request."""
        if approval_id in self.approvals:
            approval = self.approvals[approval_id]
            approval.status = "rejected"
            approval.approved_by = approver
            approval.approved_at = datetime.utcnow()
            return True
        return False
    
    def get_pending_approvals(self) -> List[MockApprovalRequest]:
        """Get pending approvals."""
        return [a for a in self.approvals.values() if a.status == "pending"]
    
    def get_approval_summary(self) -> Dict[str, Any]:
        """Get approval summary."""
        total = len(self.approvals)
        pending = len([a for a in self.approvals.values() if a.status == "pending"])
        approved = len([a for a in self.approvals.values() if a.status == "approved"])
        rejected = len([a for a in self.approvals.values() if a.status == "rejected"])
        
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }


class MockHITLAgent:
    """Mock agent with HITL capabilities."""
    
    def __init__(self):
        self.hitl_manager = MockHITLManager()
        self.threads: Dict[str, Dict[str, Any]] = {}
        self.ticket_counter = 1000
    
    def _generate_ticket_id(self, kind: str) -> str:
        """Generate mock ticket ID."""
        prefix = "SN" if kind == "NSSR" else "GW"
        self.ticket_counter += 1
        return f"{prefix}-{self.ticket_counter}"
    
    async def onboard_with_approval(self, client: str, user: str) -> Dict[str, Any]:
        """Onboard client with HITL approval gates."""
        print(f"🚀 Starting HITL onboarding for {client}...")
        
        # Create thread
        thread_id = f"thread-{client.lower()}-{len(self.threads) + 1}"
        
        # HITL Gate 1: Ticket Creation Approval
        print(f"\n🔒 HITL Gate 1: Ticket Creation Approval")
        approval1 = self.hitl_manager.create_approval(
            title=f"Create NSSR/GLAM tickets for {client}",
            approvers=["ping-admin@company.com", "security-team@company.com"],
            timeout_hours=24
        )
        
        print(f"   📋 Approval ID: {approval1.id}")
        print(f"   👥 Approvers: {', '.join(approval1.approvers)}")
        print(f"   ⏰ Expires: {approval1.expires_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Simulate approval process
        await asyncio.sleep(1)
        print(f"   ⏳ Waiting for approval...")
        await asyncio.sleep(1)
        
        # Simulate approval
        self.hitl_manager.approve(approval1.id, "ping-admin@company.com")
        print(f"   ✅ Approved by: ping-admin@company.com")
        
        # Create tickets after approval
        nssr_ticket = self._generate_ticket_id("NSSR")
        glam_ticket = self._generate_ticket_id("GLAM")
        
        print(f"\n🎫 Tickets created after approval:")
        print(f"   NSSR: {nssr_ticket}")
        print(f"   GLAM: {glam_ticket}")
        
        # Store thread
        self.threads[thread_id] = {
            "client": client,
            "owner": user,
            "created_at": datetime.utcnow().isoformat(),
            "environments": {
                "dev": {
                    "state": "FormsRaised",
                    "tickets": [nssr_ticket, glam_ticket],
                    "approvals": [approval1.id]
                },
                "staging": {"state": "NotStarted"},
                "prod": {"state": "NotStarted"}
            }
        }
        
        return {
            "thread_id": thread_id,
            "message": f"HITL onboarding started for {client}",
            "approvals": [approval1.id],
            "tickets": [nssr_ticket, glam_ticket]
        }
    
    async def advance_environment_with_approval(self, client: str, env: str, target_state: str) -> Dict[str, Any]:
        """Advance environment with HITL approval."""
        print(f"\n🔒 HITL Gate: Environment Progression Approval")
        print(f"   🎯 Moving {client} {env} to {target_state}")
        
        # Find thread
        thread = None
        thread_id = None
        for tid, t in self.threads.items():
            if t["client"].lower() == client.lower():
                thread = t
                thread_id = tid
                break
        
        if not thread:
            return {"error": f"Client {client} not found"}
        
        # Create approval request
        approval = self.hitl_manager.create_approval(
            title=f"Advance {client} {env} to {target_state}",
            approvers=["ping-admin@company.com", "devops-team@company.com"],
            timeout_hours=48
        )
        
        print(f"   📋 Approval ID: {approval.id}")
        print(f"   👥 Approvers: {', '.join(approval.approvers)}")
        print(f"   ⏰ Expires: {approval.expires_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Simulate approval process
        await asyncio.sleep(1)
        print(f"   ⏳ Waiting for approval...")
        await asyncio.sleep(1)
        
        # Simulate approval
        self.hitl_manager.approve(approval.id, "devops-team@company.com")
        print(f"   ✅ Approved by: devops-team@company.com")
        
        # Update environment state
        thread["environments"][env]["state"] = target_state
        if "approvals" not in thread["environments"][env]:
            thread["environments"][env]["approvals"] = []
        thread["environments"][env]["approvals"].append(approval.id)
        
        return {
            "thread_id": thread_id,
            "environment": env,
            "new_state": target_state,
            "approval_id": approval.id
        }
    
    async def deploy_to_production_with_approval(self, client: str) -> Dict[str, Any]:
        """Deploy to production with executive approval."""
        print(f"\n🔒 HITL Gate: PRODUCTION DEPLOYMENT APPROVAL")
        print(f"   🚀 PRODUCTION DEPLOYMENT for {client}")
        print(f"   ⚠️  This requires EXECUTIVE approval!")
        
        # Find thread
        thread = None
        thread_id = None
        for tid, t in self.threads.items():
            if t["client"].lower() == client.lower():
                thread = t
                thread_id = tid
                break
        
        if not thread:
            return {"error": f"Client {client} not found"}
        
        # Create executive approval request
        approval = self.hitl_manager.create_approval(
            title=f"PRODUCTION DEPLOYMENT: {client}",
            approvers=["ping-admin@company.com", "security-team@company.com", "cto@company.com"],
            timeout_hours=72
        )
        
        print(f"   📋 Approval ID: {approval.id}")
        print(f"   👥 Executive Approvers: {', '.join(approval.approvers)}")
        print(f"   ⏰ Expires: {approval.expires_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   🚨 This is a HIGH-RISK operation requiring C-level approval!")
        
        # Simulate executive approval process (longer)
        await asyncio.sleep(2)
        print(f"   ⏳ Waiting for executive approval...")
        await asyncio.sleep(2)
        
        # Simulate executive approval
        self.hitl_manager.approve(approval.id, "cto@company.com")
        print(f"   ✅ Approved by: cto@company.com (Executive)")
        
        # Update to production ready
        thread["environments"]["prod"]["state"] = "Complete"
        thread["environments"]["prod"]["approvals"] = [approval.id]
        
        return {
            "thread_id": thread_id,
            "deployment": "approved",
            "approval_id": approval.id,
            "approved_by": "cto@company.com"
        }
    
    async def create_emergency_approval(self, client: str, emergency_type: str, justification: str) -> Dict[str, Any]:
        """Create emergency approval with reduced timeout."""
        print(f"\n🚨 EMERGENCY APPROVAL REQUEST")
        print(f"   ⚠️  Type: {emergency_type}")
        print(f"   📝 Justification: {justification}")
        
        # Create emergency approval with reduced timeout
        approval = self.hitl_manager.create_approval(
            title=f"EMERGENCY: {emergency_type}",
            approvers=["ping-admin@company.com", "on-call-engineer@company.com"],
            timeout_hours=4  # Reduced timeout for emergencies
        )
        
        print(f"   📋 Emergency Approval ID: {approval.id}")
        print(f"   👥 Emergency Approvers: {', '.join(approval.approvers)}")
        print(f"   ⏰ URGENT - Expires in 4 hours: {approval.expires_at.strftime('%Y-%m-%d %H:%M')}")
        
        # Simulate urgent approval process
        await asyncio.sleep(1)
        print(f"   ⏳ Urgent approval process...")
        await asyncio.sleep(1)
        
        # Simulate emergency approval
        self.hitl_manager.approve(approval.id, "on-call-engineer@company.com")
        print(f"   ✅ Emergency approved by: on-call-engineer@company.com")
        
        return {
            "emergency_approval_id": approval.id,
            "approved_by": "on-call-engineer@company.com",
            "timeout_hours": 4
        }
    
    def get_approval_dashboard(self) -> Dict[str, Any]:
        """Get approval dashboard."""
        summary = self.hitl_manager.get_approval_summary()
        pending = self.hitl_manager.get_pending_approvals()
        
        return {
            "summary": summary,
            "pending_approvals": [
                {
                    "id": approval.id,
                    "title": approval.title,
                    "approvers": approval.approvers,
                    "status": approval.status,
                    "created_at": approval.created_at.strftime('%Y-%m-%d %H:%M'),
                    "expires_at": approval.expires_at.strftime('%Y-%m-%d %H:%M')
                }
                for approval in pending
            ]
        }


async def main():
    """Run the HITL demo."""
    print("=" * 70)
    print("🎯 PING SSO ONBOARDING AGENT - HITL (HUMAN-IN-THE-LOOP) DEMO")
    print("=" * 70)
    print()
    
    agent = MockHITLAgent()
    
    # Demo 1: Onboard with HITL gates
    print("DEMO 1: HITL Onboarding Workflow")
    print("-" * 40)
    result = await agent.onboard_with_approval("Galaxy", "john.doe")
    print(f"✅ Result: {result['message']}")
    print()
    
    # Demo 2: Environment progression with approval
    print("DEMO 2: Environment Progression with HITL")
    print("-" * 40)
    result = await agent.advance_environment_with_approval("Galaxy", "dev", "Validated")
    print(f"✅ Environment advanced: {result['environment']} → {result['new_state']}")
    print()
    
    # Demo 3: Production deployment with executive approval
    print("DEMO 3: Production Deployment with Executive Approval")
    print("-" * 40)
    result = await agent.deploy_to_production_with_approval("Galaxy")
    print(f"✅ Production deployment: {result['deployment']}")
    print(f"   Approved by: {result['approved_by']}")
    print()
    
    # Demo 4: Emergency approval
    print("DEMO 4: Emergency Approval Process")
    print("-" * 40)
    result = await agent.create_emergency_approval(
        "Galaxy", 
        "Security Incident Response", 
        "Critical security vulnerability requires immediate access provisioning"
    )
    print(f"✅ Emergency approval: {result['emergency_approval_id']}")
    print(f"   Approved by: {result['approved_by']}")
    print(f"   Timeout: {result['timeout_hours']} hours")
    print()
    
    # Demo 5: Approval dashboard
    print("DEMO 5: Approval Dashboard")
    print("-" * 40)
    dashboard = agent.get_approval_dashboard()
    print(f"📊 Approval Summary:")
    print(f"   Total: {dashboard['summary']['total']}")
    print(f"   Pending: {dashboard['summary']['pending']}")
    print(f"   Approved: {dashboard['summary']['approved']}")
    print(f"   Rejected: {dashboard['summary']['rejected']}")
    print()
    
    print("=" * 70)
    print("✅ HITL Demo completed!")
    print()
    print("Key HITL Features Demonstrated:")
    print("1. 🔒 Approval Gates: Ticket creation, environment progression")
    print("2. 👥 Multi-level Approvers: Admin, DevOps, Executive")
    print("3. ⏰ Timeout Management: 24h, 48h, 72h timeouts")
    print("4. 🚨 Emergency Approvals: 4-hour reduced timeout")
    print("5. 📊 Approval Dashboard: Status tracking and monitoring")
    print("6. 🔐 Executive Approval: C-level approval for production")
    print()
    print("🚀 To run the full HITL-enabled agent:")
    print("   1. Import app.hitl and app.hitl_tools")
    print("   2. Use @requires_approval decorators on critical functions")
    print("   3. Configure approvers and timeouts per approval type")
    print("   4. Integrate with notification systems (Slack, email)")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
