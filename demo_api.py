#!/usr/bin/env python3
"""
API Demo for Ping SSO Onboarding Agent

This script demonstrates the full API functionality with HTTP requests.
"""

import asyncio
import httpx
import json
from datetime import datetime


class PingSSOAPIDemo:
    """Demo client for the Ping SSO Onboarding Agent API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def health_check(self):
        """Check if the API is running."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                print("✅ API is healthy and running")
                return True
            else:
                print(f"❌ API health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Cannot connect to API: {e}")
            print("💡 Make sure to start the server first:")
            print("   uvicorn app.main:app --reload")
            return False
    
    async def onboard_client(self, client_name: str, user_id: str = "demo_user"):
        """Onboard a new client."""
        print(f"\n🚀 Onboarding {client_name}...")
        
        response = await self.client.post(
            f"{self.base_url}/agent/command",
            json={
                "text": f"Onboard {client_name}",
                "user_id": user_id
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Onboarding successful!")
            print(f"   Thread ID: {result['thread_id']}")
            print(f"   Message: {result['message']}")
            return result['thread_id']
        else:
            print(f"❌ Onboarding failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None
    
    async def get_status(self, client_name: str):
        """Get status of a client."""
        print(f"\n📊 Getting status for {client_name}...")
        
        response = await self.client.post(
            f"{self.base_url}/agent/command",
            json={
                "text": f"Status of {client_name}",
                "user_id": "demo_user"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Status retrieved:")
            print(f"   {result['message']}")
            return result
        else:
            print(f"❌ Status check failed: {response.status_code}")
            return None
    
    async def get_thread_details(self, thread_id: str):
        """Get detailed thread information."""
        print(f"\n🔍 Getting detailed thread information...")
        
        response = await self.client.get(f"{self.base_url}/threads/{thread_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Thread details retrieved:")
            print(f"   Display Name: {result['thread']['display_name']}")
            print(f"   Owner: {result['thread']['owner']}")
            print(f"   Overall Progress: {result['overall_progress']:.1%}")
            print(f"   Current Environment: {result['current_environment']}")
            
            print(f"\n   Environment States:")
            for env_name, env_data in result['environments'].items():
                print(f"     {env_name.upper()}: {env_data['state']}")
                if env_data['evidence']['tickets'] > 0:
                    print(f"       Tickets: {env_data['evidence']['tickets']}")
                if env_data['evidence']['screenshots'] > 0:
                    print(f"       Screenshots: {env_data['evidence']['screenshots']}")
                if env_data['evidence']['has_secret']:
                    print(f"       Credentials: Issued")
            
            return result
        else:
            print(f"❌ Thread details failed: {response.status_code}")
            return None
    
    async def list_all_threads(self):
        """List all threads."""
        print(f"\n📋 Listing all threads...")
        
        response = await self.client.get(f"{self.base_url}/threads")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result['count']} threads:")
            
            for thread in result['threads']:
                print(f"   {thread['display_name']} ({thread['thread_id'][:8]}...)")
                print(f"     Owner: {thread['owner']}")
                print(f"     Progress: {thread['overall_progress']:.1%}")
                print(f"     Current Env: {thread['current_environment'] or 'None'}")
                print()
            
            return result
        else:
            print(f"❌ List threads failed: {response.status_code}")
            return None
    
    async def simulate_ticket_update(self, ticket_id: str, status: str = "resolved"):
        """Simulate a ticket status update."""
        print(f"\n🎫 Simulating ticket update: {ticket_id} → {status}")
        
        response = await self.client.post(
            f"{self.base_url}/webhooks/ticketing",
            json={
                "ticket_id": ticket_id,
                "system": "ServiceNow",
                "status": status,
                "details": {
                    "resolution": "Ticket completed successfully",
                    "updated_by": "system"
                }
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Ticket update processed:")
            print(f"   Message: {result['message']}")
            print(f"   Updated Threads: {result['updated_threads']}")
            return result
        else:
            print(f"❌ Ticket update failed: {response.status_code}")
            return None
    
    async def simulate_email_approval(self, thread_id: str, message_id: str = None):
        """Simulate an email approval."""
        if not message_id:
            message_id = f"<approval-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}@company.com>"
        
        print(f"\n📧 Simulating email approval: {message_id}")
        
        response = await self.client.post(
            f"{self.base_url}/webhooks/email",
            json={
                "message_id": message_id,
                "thread_id": thread_id,
                "subject": "Approved: Ping SSO Dev Sign-off for Galaxy",
                "sender": "ping-admin@company.com",
                "content": "Approved for progression to next environment"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Email approval processed:")
            print(f"   Message: {result['message']}")
            return result
        else:
            print(f"❌ Email approval failed: {response.status_code}")
            return None
    
    async def get_audit_logs(self, thread_id: str):
        """Get audit logs for a thread."""
        print(f"\n📜 Getting audit logs for thread {thread_id[:8]}...")
        
        response = await self.client.get(f"{self.base_url}/threads/{thread_id}/audit")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Found {result['count']} audit log entries:")
            
            for log in result['logs'][:5]:  # Show first 5 entries
                print(f"   {log['created_at'][:19]} | {log['actor']} | {log['action']}")
                if log['details']:
                    print(f"     Details: {json.dumps(log['details'], indent=6)}")
            
            return result
        else:
            print(f"❌ Audit logs failed: {response.status_code}")
            return None


async def run_api_demo():
    """Run the complete API demo."""
    print("=" * 70)
    print("🎯 PING SSO ONBOARDING AGENT - API DEMO")
    print("=" * 70)
    
    async with PingSSOAPIDemo() as demo:
        # Check API health
        if not await demo.health_check():
            return
        
        # Demo 1: Onboard Galaxy
        print("\n" + "=" * 50)
        print("DEMO 1: Onboard Galaxy")
        print("=" * 50)
        thread_id = await demo.onboard_client("Galaxy")
        
        if not thread_id:
            print("❌ Demo failed - could not onboard client")
            return
        
        # Demo 2: Check status
        print("\n" + "=" * 50)
        print("DEMO 2: Check Status")
        print("=" * 50)
        await demo.get_status("Galaxy")
        
        # Demo 3: Get detailed thread info
        print("\n" + "=" * 50)
        print("DEMO 3: Detailed Thread Information")
        print("=" * 50)
        await demo.get_thread_details(thread_id)
        
        # Demo 4: List all threads
        print("\n" + "=" * 50)
        print("DEMO 4: List All Threads")
        print("=" * 50)
        await demo.list_all_threads()
        
        # Demo 5: Simulate ticket update
        print("\n" + "=" * 50)
        print("DEMO 5: Simulate Ticket Update")
        print("=" * 50)
        await demo.simulate_ticket_update("SN-1001", "resolved")
        
        # Demo 6: Simulate email approval
        print("\n" + "=" * 50)
        print("DEMO 6: Simulate Email Approval")
        print("=" * 50)
        await demo.simulate_email_approval(thread_id)
        
        # Demo 7: Get audit logs
        print("\n" + "=" * 50)
        print("DEMO 7: Audit Logs")
        print("=" * 50)
        await demo.get_audit_logs(thread_id)
        
        # Demo 8: Onboard another client
        print("\n" + "=" * 50)
        print("DEMO 8: Onboard BusinessBanking")
        print("=" * 50)
        await demo.onboard_client("BusinessBanking")
        
        # Final status check
        print("\n" + "=" * 50)
        print("DEMO 9: Final Status Check")
        print("=" * 50)
        await demo.get_status("Galaxy")
        await demo.get_status("BusinessBanking")
        
        print("\n" + "=" * 70)
        print("✅ API Demo completed successfully!")
        print("\n🚀 To run the full server:")
        print("   1. Setup: ./scripts/setup.sh")
        print("   2. Start: uvicorn app.main:app --reload")
        print("   3. API docs: http://localhost:8000/docs")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_api_demo())
