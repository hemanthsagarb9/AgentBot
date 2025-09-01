import os
import re
from typing import Dict, Any, Optional
from datetime import datetime
import hashlib

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from langfuse import Langfuse
from contextlib import contextmanager

from app.models import (
    CommandResult, CommandRequest, EnvName, EnvState, 
    Evidence, TicketRef, SecretRef, ScreenshotRef, 
    RedirectUris, AppConfig, ClientThread
)
from app.tools import CtxState
from app.state_machine import StateMachine


class PingSSOAgent:
    """Ping SSO Onboarding Agent with PydanticAI and Langfuse integration."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.thread_repo = None
        
        # Initialize Langfuse
        if config.langfuse_secret_key:
            self.langfuse = Langfuse(
                secret_key=config.langfuse_secret_key,
                public_key=config.langfuse_public_key,
                host=config.langfuse_host,
            )
        else:
            self.langfuse = None
        
        # Initialize PydanticAI agent
        self.agent = Agent(
            model=OpenAIModel("gpt-4"),  # Configure via env
            system_prompt=self._get_system_prompt(),
            result_type=CommandResult,
        )
    
    def _get_system_prompt(self) -> str:
        """Get system prompt, optionally from Langfuse."""
        base_prompt = """You are the Ping SSO Onboarding Agent. Your role is to automate the Ping SSO onboarding workflow with a typed, evidence-backed state machine.

Key Responsibilities:
1. Follow the state machine strictly - never skip HITL gates
2. Always record evidence for state transitions
3. Coordinate human approvals with proper gating
4. Maintain situational awareness for each client

State Machine Order:
NotStarted → FormsRaised → CredsIssued → AccessProvisioned → Validated → SignoffSent → Approved → Complete

Special States: Blocked, ChangesRequested, Abandoned

Available Commands:
- "Onboard {Client}" - Create thread, raise Dev NSSR + GLAM/GWAM, draft redirect URI email
- "Status of {Client}" - Return per-env state, evidence links, blockers, next actions  
- "Move {Client} to {Environment}" - Verify guards, send sign-off, raise next env tickets
- "Prepare Prod for {Client}" - Validate staging evidence, send sign-off, raise Prod NSSR

Evidence Requirements:
- FormsRaised: At least one ticket (NSSR/OAuth)
- CredsIssued: Client secret stored and masked
- AccessProvisioned: GLAM/GWAM tickets (Dev/Staging only)
- Validated: 4 screenshots (login, consent, landing, token)
- SignoffSent: Email with screenshots + redirect URIs
- Approved: Approval email received

Always validate state transitions and evidence before proceeding. If unsure, ask for clarification."""
        
        # Try to get from Langfuse if available
        if self.langfuse:
            try:
                prompt = self.langfuse.get_prompt(
                    "ping-onboarding/system", 
                    label=os.getenv("PROMPT_LABEL", "prod")
                )
                return prompt.compile(variables={
                    "policy": "Follow state machine; record evidence; HITL gates."
                })
            except Exception as e:
                print(f"Failed to fetch prompt from Langfuse: {e}")
        
        return base_prompt
    
    def set_thread_repo(self, thread_repo):
        """Set the thread repository for the agent."""
        self.thread_repo = thread_repo
    
    @contextmanager
    def traced_command(self, user_id: str, thread_id: str, name: str, metadata: dict):
        """Context manager for Langfuse tracing."""
        if not self.langfuse:
            yield None
            return
        
        trace = self.langfuse.trace(
            name=name,
            user_id=user_id,
            metadata={"thread_id": thread_id, **metadata},
        )
        try:
            yield trace
            trace.update(output={"status": "ok"})
        except Exception as e:
            trace.update(output={"status": "error", "error": str(e)})
            trace.end()
            raise
        trace.end()
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII from text for logging."""
        # Hash LANIDs
        text = re.sub(r'\b[A-Z]{2,3}-\d+\b', lambda m: f"LANID-{hashlib.md5(m.group().encode()).hexdigest()[:8]}", text)
        
        # Hash email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                     lambda m: f"EMAIL-{hashlib.md5(m.group().encode()).hexdigest()[:8]}", text)
        
        # Mask ticket IDs
        text = re.sub(r'\b(SN|GW|JIRA)-\d+\b', lambda m: f"{m.group().split('-')[0]}-****", text)
        
        return text
    
    def _parse_command_intent(self, text: str) -> Dict[str, Any]:
        """Parse natural language command into structured intent."""
        text_lower = text.lower().strip()
        
        # Onboard command
        onboard_match = re.match(r'onboard\s+(\w+)', text_lower)
        if onboard_match:
            return {
                "intent": "onboard",
                "client": onboard_match.group(1),
                "params": {}
            }
        
        # Status command
        status_match = re.match(r'status\s+(?:of\s+)?(\w+)', text_lower)
        if status_match:
            return {
                "intent": "status",
                "client": status_match.group(1),
                "params": {}
            }
        
        # Move command
        move_match = re.match(r'move\s+(\w+)\s+to\s+(dev|staging|prod)', text_lower)
        if move_match:
            return {
                "intent": "move",
                "client": move_match.group(1),
                "params": {"target_env": move_match.group(2)}
            }
        
        # Prepare Prod command
        prepare_match = re.match(r'prepare\s+prod\s+(?:for\s+)?(\w+)', text_lower)
        if prepare_match:
            return {
                "intent": "prepare_prod",
                "client": prepare_match.group(1),
                "params": {}
            }
        
        # Unknown command
        return {
            "intent": "unknown",
            "client": None,
            "params": {}
        }
    
    async def execute_command(self, request: CommandRequest) -> CommandResult:
        """Execute a natural language command."""
        
        # Parse intent
        intent = self._parse_command_intent(request.text)
        
        # Create context
        ctx = CtxState(
            user=request.user_id,
            config=self.config,
            thread_repo=self.thread_repo
        )
        
        # Trace command execution
        with self.traced_command(
            request.user_id, 
            intent.get("client", "unknown"), 
            intent["intent"], 
            {"request_id": request.request_id}
        ) as trace:
            
            if trace:
                trace.update(input={"command": self._redact_pii(request.text)})
            
            try:
                if intent["intent"] == "onboard":
                    result = await self._handle_onboard(ctx, intent["client"])
                elif intent["intent"] == "status":
                    result = await self._handle_status(ctx, intent["client"])
                elif intent["intent"] == "move":
                    result = await self._handle_move(ctx, intent["client"], intent["params"]["target_env"])
                elif intent["intent"] == "prepare_prod":
                    result = await self._handle_prepare_prod(ctx, intent["client"])
                else:
                    result = CommandResult(
                        message=f"Unknown command: {request.text}. Available commands: onboard, status, move, prepare prod",
                        thread_id="",
                        success=False
                    )
                
                if trace:
                    trace.update(output={"result": self._redact_pii(result.message)})
                
                return result
                
            except Exception as e:
                error_msg = f"Error executing command: {str(e)}"
                if trace:
                    trace.update(output={"status": "error", "error": error_msg})
                
                return CommandResult(
                    message=error_msg,
                    thread_id="",
                    success=False
                )
    
    async def _handle_onboard(self, ctx: CtxState, client: str) -> CommandResult:
        """Handle onboard command."""
        from app.tools import create_client_thread, create_nssr_ticket, create_glam_gwam_ticket, generate_redirect_uris, update_env_state
        from app.models import EnvName, EnvState, Evidence, TicketRef
        
        # Create thread
        thread_id = await create_client_thread(ctx, client, ctx.user)
        
        # Generate redirect URIs for Dev
        redirect_uris = await generate_redirect_uris(ctx, client, EnvName.dev)
        
        # Create NSSR ticket
        nssr_ticket = await create_nssr_ticket(ctx, client, EnvName.dev, redirect_uris)
        
        # Create GLAM/GWAM tickets (Dev only)
        glam_ticket = await create_glam_gwam_ticket(ctx, client, EnvName.dev, [])
        
        # Update state to FormsRaised
        evidence = Evidence(tickets=[nssr_ticket, glam_ticket])
        await update_env_state(ctx, thread_id, EnvName.dev, EnvState.forms_raised, evidence)
        
        return CommandResult(
            message=f"Created onboarding thread for {client}. Dev NSSR ticket {nssr_ticket.id} and GLAM ticket {glam_ticket.id} created. Waiting for credentials.",
            thread_id=thread_id,
            details={
                "nssr_ticket": nssr_ticket.id,
                "glam_ticket": glam_ticket.id,
                "redirect_uris": redirect_uris.model_dump()
            }
        )
    
    async def _handle_status(self, ctx: CtxState, client: str) -> CommandResult:
        """Handle status command."""
        from app.tools import get_thread_status
        
        # Find thread by client name
        threads = await self.thread_repo.list_threads()
        thread = None
        for t in threads:
            if t.display_name.lower() == client.lower():
                thread = t
                break
        
        if not thread:
            return CommandResult(
                message=f"Client {client} not found. Available clients: {[t.display_name for t in threads]}",
                thread_id="",
                success=False
            )
        
        # Get status
        status = await get_thread_status(ctx, thread.thread_id)
        
        # Format status message
        message = f"Status for {client}:\n"
        message += f"Overall Progress: {status['overall_progress']:.1%}\n"
        message += f"Current Environment: {status['current_environment'] or 'None'}\n\n"
        
        for env_name, env_data in status["environments"].items():
            message += f"{env_name.title()}: {env_data['state']}\n"
            if env_data['evidence']['tickets'] > 0:
                message += f"  Tickets: {env_data['evidence']['tickets']}\n"
            if env_data['evidence']['screenshots'] > 0:
                message += f"  Screenshots: {env_data['evidence']['screenshots']}\n"
            if env_data['evidence']['has_secret']:
                message += f"  Credentials: Issued\n"
            message += "\n"
        
        if status['blockers']:
            message += f"Blockers: {', '.join(status['blockers'])}\n"
        
        if status['next_actions']:
            message += f"Next Actions: {', '.join(status['next_actions'][:3])}\n"
        
        return CommandResult(
            message=message,
            thread_id=thread.thread_id,
            details=status
        )
    
    async def _handle_move(self, ctx: CtxState, client: str, target_env: str) -> CommandResult:
        """Handle move command."""
        from app.tools import get_thread_status, update_env_state, send_signoff_email
        from app.models import EnvName, EnvState, Evidence
        
        # Find thread
        threads = await self.thread_repo.list_threads()
        thread = None
        for t in threads:
            if t.display_name.lower() == client.lower():
                thread = t
                break
        
        if not thread:
            return CommandResult(
                message=f"Client {client} not found",
                thread_id="",
                success=False
            )
        
        target_env_enum = EnvName(target_env)
        
        # Get current status
        status = await get_thread_status(ctx, thread.thread_id)
        
        # Validate move is possible
        current_env = status['current_environment']
        if not current_env:
            return CommandResult(
                message=f"No active environment for {client}",
                thread_id=thread.thread_id,
                success=False
            )
        
        # For now, just update the message
        message = f"Move {client} to {target_env} - this would require:\n"
        message += f"1. Validating {current_env} evidence\n"
        message += f"2. Sending {current_env} sign-off email\n"
        message += f"3. Creating {target_env} tickets\n"
        message += f"4. Updating state to {target_env}\n"
        
        return CommandResult(
            message=message,
            thread_id=thread.thread_id,
            details={"target_env": target_env, "current_env": current_env}
        )
    
    async def _handle_prepare_prod(self, ctx: CtxState, client: str) -> CommandResult:
        """Handle prepare prod command."""
        from app.tools import get_thread_status
        
        # Find thread
        threads = await self.thread_repo.list_threads()
        thread = None
        for t in threads:
            if t.display_name.lower() == client.lower():
                thread = t
                break
        
        if not thread:
            return CommandResult(
                message=f"Client {client} not found",
                thread_id="",
                success=False
            )
        
        # Get status
        status = await get_thread_status(ctx, thread.thread_id)
        
        message = f"Prepare Prod for {client} - this would require:\n"
        message += "1. Validating Staging evidence\n"
        message += "2. Sending Staging sign-off\n"
        message += "3. Creating Prod NSSR ticket\n"
        message += "4. No GLAM/GWAM needed for Prod\n"
        
        return CommandResult(
            message=message,
            thread_id=thread.thread_id,
            details={"action": "prepare_prod"}
        )
