import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings, get_app_config
from app.models import (
    CommandRequest, CommandResult, ThreadStatus, TicketUpdate, 
    EmailUpdate, ClientThread
)
from app.database import create_database_session, init_database, ThreadRepository
from app.agent import PingSSOAgent
from app.state_machine import StateMachine


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global instances
agent: PingSSOAgent = None
thread_repo: ThreadRepository = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    global agent, thread_repo
    
    # Startup
    logger.info("Starting Ping SSO Onboarding Agent...")
    
    # Initialize configuration
    config = get_app_config()
    
    # Initialize database
    init_database(config)
    session_factory = create_database_session(config)
    thread_repo = ThreadRepository(session_factory)
    
    # Initialize agent
    agent = PingSSOAgent(config)
    agent.set_thread_repo(thread_repo)
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title="Ping SSO Onboarding Agent",
    description="Natural-Language Agent for automating Ping SSO onboarding workflow",
    version="0.9.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ping SSO Onboarding Agent",
        "version": "0.9.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}


@app.post("/agent/command", response_model=CommandResult)
async def execute_command(request: CommandRequest):
    """Execute a natural language command."""
    try:
        logger.info(f"Executing command: {request.text} for user: {request.user_id}")
        
        result = await agent.execute_command(request)
        
        logger.info(f"Command result: {result.success} - {result.message}")
        return result
        
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}", response_model=Dict[str, Any])
async def get_thread_status(thread_id: str):
    """Get comprehensive status of a client thread."""
    try:
        thread = await thread_repo.get_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread {thread_id} not found")
        
        # Calculate progress and current environment
        progress = StateMachine.calculate_progress(thread)
        current_env = StateMachine.get_current_environment(thread)
        
        # Build comprehensive status
        status = {
            "thread": thread.model_dump(),
            "summary": f"{thread.display_name} - {progress:.1%} complete",
            "current_environment": current_env.value if current_env else None,
            "overall_progress": progress,
            "environments": {}
        }
        
        # Add environment details
        for env_name, env in thread.environments.items():
            blockers = StateMachine.get_blockers(env, thread)
            next_actions = StateMachine.get_next_actions(env, thread)
            
            status["environments"][env_name.value] = {
                "state": env.state.value,
                "last_updated": env.last_updated.isoformat(),
                "evidence": {
                    "tickets": [ticket.model_dump() for ticket in env.evidence.tickets],
                    "secret": env.evidence.secret.model_dump() if env.evidence.secret else None,
                    "screenshots": [screenshot.model_dump() for screenshot in env.evidence.screenshots],
                    "emails": env.evidence.emails,
                    "notes": env.evidence.notes
                },
                "redirect_uris": env.redirect_uris.model_dump() if env.redirect_uris else None,
                "people": env.people.model_dump(),
                "blockers": blockers,
                "next_actions": next_actions
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting thread status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads", response_model=Dict[str, Any])
async def list_threads(owner: str = None):
    """List all client threads, optionally filtered by owner."""
    try:
        threads = await thread_repo.list_threads(owner=owner)
        
        thread_summaries = []
        for thread in threads:
            progress = StateMachine.calculate_progress(thread)
            current_env = StateMachine.get_current_environment(thread)
            
            thread_summaries.append({
                "thread_id": thread.thread_id,
                "display_name": thread.display_name,
                "owner": thread.owner,
                "created_at": thread.created_at.isoformat(),
                "last_update": thread.last_update.isoformat(),
                "overall_progress": progress,
                "current_environment": current_env.value if current_env else None,
                "blockers": thread.blockers,
                "next_actions": thread.next_actions[:3]  # Limit to top 3
            })
        
        return {
            "threads": thread_summaries,
            "count": len(thread_summaries),
            "filtered_by_owner": owner
        }
        
    except Exception as e:
        logger.error(f"Error listing threads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/ticketing")
async def handle_ticket_update(update: TicketUpdate, background_tasks: BackgroundTasks):
    """Handle ticket status updates from external systems."""
    try:
        logger.info(f"Received ticket update: {update.ticket_id} - {update.status}")
        
        # Find threads with this ticket
        threads = await thread_repo.list_threads()
        updated_threads = []
        
        for thread in threads:
            for env_name, env in thread.environments.items():
                for ticket in env.evidence.tickets:
                    if ticket.id == update.ticket_id:
                        # Update ticket status
                        ticket.status = update.status
                        
                        # If ticket is completed, potentially advance state
                        if update.status.lower() in ['resolved', 'closed', 'completed']:
                            logger.info(f"Ticket {update.ticket_id} completed, checking state advancement")
                            # Add background task to check state advancement
                            background_tasks.add_task(
                                check_state_advancement, 
                                thread.thread_id, 
                                env_name
                            )
                        
                        updated_threads.append(thread.thread_id)
                        await thread_repo.update_thread(thread)
        
        return {
            "message": f"Processed ticket update for {update.ticket_id}",
            "updated_threads": updated_threads
        }
        
    except Exception as e:
        logger.error(f"Error handling ticket update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhooks/email")
async def handle_email_update(update: EmailUpdate, background_tasks: BackgroundTasks):
    """Handle email updates (sign-off replies, etc.)."""
    try:
        logger.info(f"Received email update: {update.message_id} for thread {update.thread_id}")
        
        thread = await thread_repo.get_thread(update.thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail=f"Thread {update.thread_id} not found")
        
        # Determine if this is an approval email
        is_approval = any(word in update.subject.lower() for word in ['approved', 'approve', 'sign-off'])
        
        if is_approval:
            # Find environment waiting for approval
            for env_name, env in thread.environments.items():
                if env.state.value == "SignoffSent":
                    # Add approval email to evidence
                    env.evidence.emails.append(update.message_id)
                    
                    # Add background task to advance to Approved state
                    background_tasks.add_task(
                        advance_to_approved,
                        thread.thread_id,
                        env_name,
                        update.message_id
                    )
                    break
        
        return {"message": f"Processed email update for {update.message_id}"}
        
    except Exception as e:
        logger.error(f"Error handling email update: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{thread_id}/audit")
async def get_audit_logs(thread_id: str, limit: int = 100):
    """Get audit logs for a thread."""
    try:
        logs = await thread_repo.get_audit_logs(thread_id, limit)
        return {
            "thread_id": thread_id,
            "logs": [log.model_dump() for log in logs],
            "count": len(logs)
        }
    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Background tasks
async def check_state_advancement(thread_id: str, env_name: str):
    """Background task to check if state can be advanced after ticket completion."""
    try:
        thread = await thread_repo.get_thread(thread_id)
        if not thread:
            return
        
        env = thread.environments.get(env_name)
        if not env:
            return
        
        # Check if we can advance from FormsRaised to CredsIssued
        if env.state.value == "FormsRaised":
            # In real implementation, check if credentials are actually issued
            # For now, just log that we would check
            logger.info(f"Would check if credentials are issued for {thread_id} {env_name}")
            
    except Exception as e:
        logger.error(f"Error in background task check_state_advancement: {str(e)}")


async def advance_to_approved(thread_id: str, env_name: str, approval_email_id: str):
    """Background task to advance environment to Approved state."""
    try:
        from app.tools import update_env_state
        from app.models import EnvName, EnvState, Evidence
        
        thread = await thread_repo.get_thread(thread_id)
        if not thread:
            return
        
        env = thread.environments.get(EnvName(env_name))
        if not env or env.state.value != "SignoffSent":
            return
        
        # Create context for state update
        from app.tools import CtxState
        ctx = CtxState(
            user="system",
            config=get_app_config(),
            thread_repo=thread_repo
        )
        
        # Update to Approved state
        evidence = env.evidence
        evidence.emails.append(approval_email_id)
        
        await update_env_state(
            ctx, 
            thread_id, 
            EnvName(env_name), 
            EnvState.approved, 
            evidence,
            f"Approval received via email {approval_email_id}"
        )
        
        logger.info(f"Advanced {thread_id} {env_name} to Approved state")
        
    except Exception as e:
        logger.error(f"Error in background task advance_to_approved: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
