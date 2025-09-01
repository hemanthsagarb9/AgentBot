#!/usr/bin/env python3
"""
Interactive Demo for Ping SSO Onboarding Agent

This script provides an interactive menu to demonstrate different aspects of the agent.
"""

import asyncio
import sys
from typing import Dict, Any


class InteractiveDemo:
    """Interactive demo with menu options."""
    
    def __init__(self):
        self.demo_functions = {
            "1": ("Core Workflow Demo", self.run_core_demo),
            "2": ("HITL Approval Demo", self.run_hitl_demo),
            "3": ("API Demo (requires server)", self.run_api_demo),
            "4": ("State Machine Demo", self.run_state_machine_demo),
            "5": ("Security & Compliance Demo", self.run_security_demo),
            "6": ("All Demos", self.run_all_demos),
            "0": ("Exit", self.exit_demo)
        }
    
    def show_menu(self):
        """Display the main menu."""
        print("\n" + "=" * 60)
        print("🎯 PING SSO ONBOARDING AGENT - INTERACTIVE DEMO")
        print("=" * 60)
        print()
        print("Choose a demo to run:")
        print()
        
        for key, (name, _) in self.demo_functions.items():
            if key == "0":
                print(f"  {key}. {name}")
            else:
                print(f"  {key}. {name}")
        
        print()
    
    async def run_core_demo(self):
        """Run the core workflow demo."""
        print("\n🚀 Running Core Workflow Demo...")
        print("-" * 40)
        
        # Import and run the core demo
        import subprocess
        result = subprocess.run([sys.executable, "demo.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
    
    async def run_hitl_demo(self):
        """Run the HITL demo."""
        print("\n🔒 Running HITL (Human-in-the-Loop) Demo...")
        print("-" * 40)
        
        # Import and run the HITL demo
        import subprocess
        result = subprocess.run([sys.executable, "demo_hitl.py"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Warnings:", result.stderr)
    
    async def run_api_demo(self):
        """Run the API demo."""
        print("\n🌐 Running API Demo...")
        print("-" * 40)
        print("⚠️  This requires the server to be running!")
        print("   Start server with: uvicorn app.main:app --reload")
        print()
        
        response = input("Is the server running? (y/n): ").lower().strip()
        if response == 'y':
            import subprocess
            result = subprocess.run([sys.executable, "demo_api.py"], capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
        else:
            print("Skipping API demo. Start the server and try again.")
    
    async def run_state_machine_demo(self):
        """Run the state machine demo."""
        print("\n🔄 Running State Machine Demo...")
        print("-" * 40)
        
        # Import state machine components
        try:
            from app.models import EnvName, EnvState, Evidence, TicketRef, SecretRef, ScreenshotRef
            from app.state_machine import StateMachine
            
            print("📊 State Machine Flow:")
            print("NotStarted → FormsRaised → CredsIssued → AccessProvisioned → Validated → SignoffSent → Approved → Complete")
            print()
            
            # Demo state transitions
            print("🔍 Testing State Transitions:")
            
            # Test valid transition
            is_valid = StateMachine.can_transition(EnvState.not_started, EnvState.forms_raised)
            print(f"   NotStarted → FormsRaised: {'✅ Valid' if is_valid else '❌ Invalid'}")
            
            # Test invalid transition
            is_valid = StateMachine.can_transition(EnvState.not_started, EnvState.validated)
            print(f"   NotStarted → Validated: {'✅ Valid' if is_valid else '❌ Invalid'}")
            
            # Test special states
            is_valid = StateMachine.can_transition(EnvState.forms_raised, EnvState.blocked)
            print(f"   FormsRaised → Blocked: {'✅ Valid' if is_valid else '❌ Invalid'}")
            
            print()
            print("🔍 Testing Evidence Validation:")
            
            # Test with evidence
            ticket = TicketRef(system="ServiceNow", id="SN-12345", kind="NSSR")
            evidence = Evidence(tickets=[ticket])
            
            is_valid, errors = StateMachine.validate_transition(
                EnvState.not_started, EnvState.forms_raised, EnvName.dev, evidence
            )
            print(f"   FormsRaised with ticket: {'✅ Valid' if is_valid else '❌ Invalid'}")
            if errors:
                print(f"     Errors: {errors}")
            
            # Test without evidence
            empty_evidence = Evidence()
            is_valid, errors = StateMachine.validate_transition(
                EnvState.not_started, EnvState.forms_raised, EnvName.dev, empty_evidence
            )
            print(f"   FormsRaised without ticket: {'✅ Valid' if is_valid else '❌ Invalid'}")
            if errors:
                print(f"     Errors: {errors}")
            
            print()
            print("✅ State Machine Demo completed!")
            
        except ImportError as e:
            print(f"❌ Could not import state machine components: {e}")
            print("   Make sure you're in the project directory and dependencies are installed.")
    
    async def run_security_demo(self):
        """Run the security and compliance demo."""
        print("\n🔐 Running Security & Compliance Demo...")
        print("-" * 40)
        
        # Demo PII redaction
        print("🛡️  PII Redaction Demo:")
        test_text = "User ABC-123 with email john.doe@company.com created ticket SN-98765"
        print(f"   Original: {test_text}")
        
        # Simple redaction demo
        redacted = test_text
        redacted = redacted.replace("ABC-123", "LANID-****")
        redacted = redacted.replace("john.doe@company.com", "EMAIL-****")
        redacted = redacted.replace("SN-98765", "SN-****")
        
        print(f"   Redacted: {redacted}")
        print()
        
        # Demo secret masking
        print("🔒 Secret Masking Demo:")
        secret = "super-secret-client-key-12345"
        masked = f"****{secret[-4:]}" if len(secret) >= 4 else "****"
        print(f"   Original: {secret}")
        print(f"   Masked:   {masked}")
        print()
        
        # Demo audit logging
        print("📜 Audit Logging Demo:")
        audit_entry = {
            "timestamp": "2024-01-01T12:00:00Z",
            "actor": "john.doe",
            "action": "state_transition",
            "details": {
                "environment": "dev",
                "from_state": "NotStarted",
                "to_state": "FormsRaised",
                "evidence_count": 2
            }
        }
        print(f"   Audit Entry: {audit_entry}")
        print()
        
        print("✅ Security & Compliance Demo completed!")
    
    async def run_all_demos(self):
        """Run all demos in sequence."""
        print("\n🎯 Running All Demos...")
        print("=" * 60)
        
        demos = [
            ("Core Workflow", self.run_core_demo),
            ("HITL Approvals", self.run_hitl_demo),
            ("State Machine", self.run_state_machine_demo),
            ("Security & Compliance", self.run_security_demo)
        ]
        
        for name, demo_func in demos:
            print(f"\n{'='*20} {name} {'='*20}")
            await demo_func()
            print(f"\n✅ {name} completed!")
            
            # Pause between demos
            if demo_func != demos[-1][1]:  # Not the last demo
                input("\nPress Enter to continue to next demo...")
        
        print("\n🎉 All demos completed!")
    
    async def exit_demo(self):
        """Exit the demo."""
        print("\n👋 Thanks for trying the Ping SSO Onboarding Agent!")
        print("🚀 To get started:")
        print("   1. Setup: ./scripts/setup.sh")
        print("   2. Start server: uvicorn app.main:app --reload")
        print("   3. API docs: http://localhost:8000/docs")
        print("   4. Run tests: ./scripts/run_tests.sh")
        return True
    
    async def run(self):
        """Run the interactive demo."""
        while True:
            self.show_menu()
            
            try:
                choice = input("Enter your choice (0-6): ").strip()
                
                if choice in self.demo_functions:
                    name, func = self.demo_functions[choice]
                    print(f"\n🎯 Running: {name}")
                    
                    should_exit = await func()
                    if should_exit:
                        break
                    
                    input("\nPress Enter to return to menu...")
                else:
                    print("❌ Invalid choice. Please enter 0-6.")
                    
            except KeyboardInterrupt:
                print("\n\n👋 Demo interrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("Press Enter to continue...")


async def main():
    """Main entry point."""
    demo = InteractiveDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())

