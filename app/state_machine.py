from typing import List, Optional, Tuple
from app.models import EnvState, EnvName, Evidence, Environment, ClientThread


class StateMachineError(Exception):
    """Raised when state transition is invalid or blocked."""
    pass


class StateMachine:
    """Deterministic state machine for Ping SSO onboarding environments."""
    
    # Valid state progression order
    STATE_ORDER = [
        EnvState.not_started,
        EnvState.forms_raised,
        EnvState.creds_issued,
        EnvState.access_provisioned,
        EnvState.validated,
        EnvState.signoff_sent,
        EnvState.approved,
        EnvState.complete,
    ]
    
    # Special states that can be entered from any state
    SPECIAL_STATES = {
        EnvState.blocked,
        EnvState.changes_requested,
        EnvState.abandoned
    }
    
    @classmethod
    def can_transition(cls, current: EnvState, target: EnvState) -> bool:
        """Check if transition from current to target state is valid."""
        # Special states can be entered from any state
        if target in cls.SPECIAL_STATES:
            return True
            
        # Changes requested can only go back to previous states
        if current == EnvState.changes_requested:
            return target in cls.STATE_ORDER[:cls.STATE_ORDER.index(current)]
            
        # Normal progression: must be next in sequence
        try:
            current_idx = cls.STATE_ORDER.index(current)
            target_idx = cls.STATE_ORDER.index(target)
            return target_idx == current_idx + 1
        except ValueError:
            return False
    
    @classmethod
    def validate_transition(
        cls, 
        current: EnvState, 
        target: EnvState, 
        env: EnvName, 
        evidence: Evidence,
        thread: Optional[ClientThread] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate state transition with evidence and business rules.
        Returns (is_valid, list_of_errors).
        """
        errors = []
        
        # Basic transition validation
        if not cls.can_transition(current, target):
            errors.append(f"Invalid transition: {current} → {target}")
            return False, errors
        
        # Evidence validation based on target state
        if target == EnvState.forms_raised:
            if not evidence.tickets:
                errors.append("FormsRaised requires at least one ticket")
                
        elif target == EnvState.creds_issued:
            if not evidence.secret:
                errors.append("CredsIssued requires client secret evidence")
                
        elif target == EnvState.access_provisioned:
            # GLAM/GWAM only required for Dev and Staging
            if env in [EnvName.dev, EnvName.staging]:
                glam_tickets = [t for t in evidence.tickets if t.kind in ['GLAM', 'GWAM']]
                if not glam_tickets:
                    errors.append(f"{env} requires GLAM/GWAM tickets for access provisioning")
                    
        elif target == EnvState.validated:
            # Must have 4 screenshots: login, consent, landing, token
            required_labels = ['login', 'consent', 'landing', 'token']
            screenshot_labels = [s.label for s in evidence.screenshots]
            missing_labels = [label for label in required_labels if label not in screenshot_labels]
            if missing_labels:
                errors.append(f"Validation requires screenshots: {missing_labels}")
                
        elif target == EnvState.signoff_sent:
            if not evidence.emails:
                errors.append("SignoffSent requires email evidence")
                
        elif target == EnvState.approved:
            # Must have approval email
            if not evidence.emails:
                errors.append("Approved requires approval email evidence")
                
        elif target == EnvState.complete:
            # For Prod, no additional requirements
            # For Dev/Staging, must have approval from previous environment
            if env in [EnvName.staging, EnvName.prod] and thread:
                prev_env = EnvName.dev if env == EnvName.staging else EnvName.staging
                prev_env_state = thread.environments[prev_env].state
                if prev_env_state != EnvState.complete:
                    errors.append(f"Environment {env} requires {prev_env} to be complete")
        
        return len(errors) == 0, errors
    
    @classmethod
    def get_next_actions(cls, env: Environment, thread: ClientThread) -> List[str]:
        """Get list of next actions based on current state."""
        actions = []
        
        if env.state == EnvState.not_started:
            actions.extend([
                "Create NSSR/OAuth ticket",
                "Create GLAM/GWAM tickets (if Dev/Staging)",
                "Generate redirect URIs"
            ])
            
        elif env.state == EnvState.forms_raised:
            actions.append("Wait for credentials to be issued")
            
        elif env.state == EnvState.creds_issued:
            if env.name in [EnvName.dev, EnvName.staging]:
                actions.append("Create GLAM/GWAM tickets")
            actions.append("Test application sign-in")
            
        elif env.state == EnvState.access_provisioned:
            actions.extend([
                "Capture login screenshot",
                "Capture consent screenshot", 
                "Capture landing page screenshot",
                "Capture token/session screenshot"
            ])
            
        elif env.state == EnvState.validated:
            actions.append("Send sign-off email with screenshots and redirect URIs")
            
        elif env.state == EnvState.signoff_sent:
            actions.append("Wait for approval email")
            
        elif env.state == EnvState.approved:
            if env.name == EnvName.prod:
                actions.append("Production ready - onboarding complete")
            else:
                actions.append("Proceed to next environment")
                
        elif env.state == EnvState.blocked:
            actions.append("Resolve blocker and retry")
            
        elif env.state == EnvState.changes_requested:
            actions.append("Address requested changes")
            
        return actions
    
    @classmethod
    def get_blockers(cls, env: Environment, thread: ClientThread) -> List[str]:
        """Get list of current blockers for the environment."""
        blockers = []
        
        if env.state == EnvState.blocked:
            blockers.append("Environment is blocked - manual intervention required")
            
        elif env.state == EnvState.changes_requested:
            blockers.append("Changes requested - address feedback before proceeding")
            
        elif env.state == EnvState.forms_raised:
            # Check if tickets are taking too long
            for ticket in env.evidence.tickets:
                if ticket.status == "open":
                    blockers.append(f"Ticket {ticket.id} ({ticket.kind}) is still open")
                    
        elif env.state == EnvState.signoff_sent:
            # Check if sign-off is taking too long
            if not env.evidence.emails:
                blockers.append("Waiting for sign-off approval")
                
        return blockers
    
    @classmethod
    def calculate_progress(cls, thread: ClientThread) -> float:
        """Calculate overall progress across all environments (0.0 to 1.0)."""
        total_states = len(cls.STATE_ORDER)
        completed_states = 0
        
        for env in thread.environments.values():
            if env.state == EnvState.complete:
                completed_states += total_states
            elif env.state in cls.STATE_ORDER:
                completed_states += cls.STATE_ORDER.index(env.state) + 1
                
        max_possible = total_states * len(thread.environments)
        return min(completed_states / max_possible, 1.0) if max_possible > 0 else 0.0
    
    @classmethod
    def get_current_environment(cls, thread: ClientThread) -> Optional[EnvName]:
        """Get the environment currently being worked on."""
        for env_name in [EnvName.dev, EnvName.staging, EnvName.prod]:
            env = thread.environments[env_name]
            if env.state not in [EnvState.complete, EnvState.abandoned]:
                return env_name
        return None
