#!/usr/bin/env python3
"""
Demo script for Ping SSO Onboarding Agent

This script demonstrates the key functionality of the agent without requiring
external dependencies like ServiceNow, AWS, or a full database setup.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any

# Mock implementations for demo
class MockTicketRef:
    def __init__(self, system: str, id: str, kind: str):
        self.system = system
        self.id = id
        self.kind = kind
        self.status = "open"
        self.url = f"https://mock-{system.lower()}.com/ticket/{id}"

class MockSecretRef:
    def __init__(self, name: str, secret: str):
        self.name = name
        self.mask = f"****{secret[-4:]}" if len(secret) >= 4 else "****"

class MockRedirectUris:
    def __init__(self, client: str, env: str):
        base = f"https://{env}.{client.lower()}.ourdomain.com"
        self.web_callback = f"{base}/api/auth/callback/ping"
        self.post_logout = f"{base}/auth/logout/callback"

class MockAgent:
    """Mock implementation of the Ping SSO Onboarding Agent for demo purposes."""
    
    def __init__(self):
        self.threads: Dict[str, Dict[str, Any]] = {}
        self.ticket_counter = 1000
    
    def _generate_ticket_id(self, kind: str) -> str:
        """Generate mock ticket ID."""
        prefix = "SN" if kind == "NSSR" else "GW"
        self.ticket_counter += 1
        return f"{prefix}-{self.ticket_counter}"
    
    async def onboard_client(self, client: str, user: str) -> Dict[str, Any]:
        """Onboard a new client."""
        print(f"🚀 Starting onboarding for {client}...")
        
        # Create thread
        thread_id = f"thread-{client.lower()}-{len(self.threads) + 1}"
        
        # Generate redirect URIs
        redirect_uris = MockRedirectUris(client, "dev")
        print(f"📍 Generated redirect URIs:")
        print(f"   Web Callback: {redirect_uris.web_callback}")
        print(f"   Post Logout: {redirect_uris.post_logout}")
        
        # Create tickets
        nssr_ticket = MockTicketRef("ServiceNow", self._generate_ticket_id("NSSR"), "NSSR")
        glam_ticket = MockTicketRef("ServiceNow", self._generate_ticket_id("GLAM"), "GLAM")
        
        print(f"🎫 Created tickets:")
        print(f"   NSSR: {nssr_ticket.id} ({nssr_ticket.url})")
        print(f"   GLAM: {glam_ticket.id} ({glam_ticket.url})")
        
        # Store thread
        self.threads[thread_id] = {
            "client": client,
            "owner": user,
            "created_at": datetime.utcnow().isoformat(),
            "environments": {
                "dev": {
                    "state": "FormsRaised",
                    "tickets": [nssr_ticket, glam_ticket],
                    "redirect_uris": redirect_uris
                },
                "staging": {"state": "NotStarted"},
                "prod": {"state": "NotStarted"}
            }
        }
        
        print(f"✅ Onboarding thread created: {thread_id}")
        print(f"📊 Current state: Dev → FormsRaised")
        print(f"⏳ Next: Waiting for credentials to be issued")
        
        return {
            "thread_id": thread_id,
            "message": f"Successfully started onboarding for {client}",
            "nssr_ticket": nssr_ticket.id,
            "glam_ticket": glam_ticket.id
        }
    
    async def get_status(self, client: str) -> Dict[str, Any]:
        """Get status of client onboarding."""
        # Find thread by client name
        thread = None
        thread_id = None
        for tid, t in self.threads.items():
            if t["client"].lower() == client.lower():
                thread = t
                thread_id = tid
                break
        
        if not thread:
            return {"error": f"Client {client} not found"}
        
        print(f"📊 Status for {client} (Thread: {thread_id})")
        print(f"👤 Owner: {thread['owner']}")
        print(f"📅 Created: {thread['created_at']}")
        print()
        
        for env_name, env_data in thread["environments"].items():
            state = env_data["state"]
            print(f"🌍 {env_name.upper()}: {state}")
            
            if "tickets" in env_data:
                for ticket in env_data["tickets"]:
                    print(f"   🎫 {ticket.kind}: {ticket.id} ({ticket.status})")
            
            if "redirect_uris" in env_data:
                uris = env_data["redirect_uris"]
                print(f"   📍 Callback: {uris.web_callback}")
            
            print()
        
        return {
            "thread_id": thread_id,
            "client": client,
            "status": "active",
            "environments": thread["environments"]
        }
    
    async def simulate_credential_issuance(self, client: str, secret: str):
        """Simulate receiving credentials from ServiceNow."""
        # Find thread
        thread = None
        thread_id = None
        for tid, t in self.threads.items():
            if t["client"].lower() == client.lower():
                thread = t
                thread_id = tid
                break
        
        if not thread:
            print(f"❌ Client {client} not found")
            return
        
        print(f"🔐 Credentials issued for {client}")
        
        # Store secret (masked)
        secret_ref = MockSecretRef(f"pingsso/{client.lower()}/dev/client_secret", secret)
        print(f"🔒 Secret stored: {secret_ref.name} → {secret_ref.mask}")
        
        # Update state
        thread["environments"]["dev"]["state"] = "CredsIssued"
        thread["environments"]["dev"]["secret"] = secret_ref
        
        print(f"📊 State updated: Dev → CredsIssued")
        print(f"⏳ Next: Test application sign-in and capture screenshots")
    
    async def simulate_validation_complete(self, client: str):
        """Simulate completing validation with screenshots."""
        # Find thread
        thread = None
        for tid, t in self.threads.items():
            if t["client"].lower() == client.lower():
                thread = t
                break
        
        if not thread:
            print(f"❌ Client {client} not found")
            return
        
        print(f"📸 Validation screenshots captured for {client}")
        
        screenshots = [
            {"label": "login", "key": f"screenshots/{client.lower()}/dev/login.png"},
            {"label": "consent", "key": f"screenshots/{client.lower()}/dev/consent.png"},
            {"label": "landing", "key": f"screenshots/{client.lower()}/dev/landing.png"},
            {"label": "token", "key": f"screenshots/{client.lower()}/dev/token.png"},
        ]
        
        for screenshot in screenshots:
            print(f"   📷 {screenshot['label']}: {screenshot['key']}")
        
        # Update state
        thread["environments"]["dev"]["state"] = "Validated"
        thread["environments"]["dev"]["screenshots"] = screenshots
        
        print(f"📊 State updated: Dev → Validated")
        print(f"⏳ Next: Send sign-off email to proceed to Staging")


async def main():
    """Run the demo."""
    print("=" * 60)
    print("🎯 PING SSO ONBOARDING AGENT - DEMO")
    print("=" * 60)
    print()
    
    agent = MockAgent()
    
    # Demo 1: Onboard Galaxy
    print("DEMO 1: Onboarding Galaxy")
    print("-" * 30)
    result = await agent.onboard_client("Galaxy", "john.doe")
    print()
    
    # Demo 2: Check status
    print("DEMO 2: Check Status")
    print("-" * 30)
    await agent.get_status("Galaxy")
    
    # Demo 3: Simulate credential issuance
    print("DEMO 3: Simulate Credential Issuance")
    print("-" * 30)
    await agent.simulate_credential_issuance("Galaxy", "super-secret-client-key-12345")
    print()
    
    # Demo 4: Check status again
    print("DEMO 4: Updated Status")
    print("-" * 30)
    await agent.get_status("Galaxy")
    
    # Demo 5: Simulate validation complete
    print("DEMO 5: Simulate Validation Complete")
    print("-" * 30)
    await agent.simulate_validation_complete("Galaxy")
    print()
    
    # Demo 6: Final status
    print("DEMO 6: Final Status")
    print("-" * 30)
    await agent.get_status("Galaxy")
    
    print("=" * 60)
    print("✅ Demo completed!")
    print()
    print("This demonstrates the core workflow:")
    print("1. Create thread and raise Dev tickets (NSSR + GLAM)")
    print("2. Wait for credentials to be issued")
    print("3. Test application and capture validation screenshots")
    print("4. Send sign-off email to proceed to next environment")
    print()
    print("🚀 To run the full agent:")
    print("   1. Setup environment: ./scripts/setup.sh")
    print("   2. Start services: docker-compose up -d")
    print("   3. Run agent: uvicorn app.main:app --reload")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
