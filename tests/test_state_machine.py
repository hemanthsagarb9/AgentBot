import pytest
from app.models import (
    EnvName, EnvState, Evidence, Environment, ClientThread,
    TicketRef, SecretRef, ScreenshotRef
)
from app.state_machine import StateMachine, StateMachineError


class TestStateMachine:
    """Test state machine logic."""
    
    def test_can_transition_normal_flow(self):
        """Test normal state transitions."""
        # Test valid transitions
        assert StateMachine.can_transition(EnvState.not_started, EnvState.forms_raised)
        assert StateMachine.can_transition(EnvState.forms_raised, EnvState.creds_issued)
        assert StateMachine.can_transition(EnvState.creds_issued, EnvState.access_provisioned)
        assert StateMachine.can_transition(EnvState.access_provisioned, EnvState.validated)
        assert StateMachine.can_transition(EnvState.validated, EnvState.signoff_sent)
        assert StateMachine.can_transition(EnvState.signoff_sent, EnvState.approved)
        assert StateMachine.can_transition(EnvState.approved, EnvState.complete)
    
    def test_can_transition_invalid_flow(self):
        """Test invalid state transitions."""
        # Test invalid transitions (skipping states)
        assert not StateMachine.can_transition(EnvState.not_started, EnvState.creds_issued)
        assert not StateMachine.can_transition(EnvState.forms_raised, EnvState.validated)
        assert not StateMachine.can_transition(EnvState.validated, EnvState.complete)
    
    def test_can_transition_special_states(self):
        """Test transitions to special states."""
        # Special states can be entered from any state
        assert StateMachine.can_transition(EnvState.not_started, EnvState.blocked)
        assert StateMachine.can_transition(EnvState.forms_raised, EnvState.blocked)
        assert StateMachine.can_transition(EnvState.validated, EnvState.changes_requested)
        assert StateMachine.can_transition(EnvState.signoff_sent, EnvState.abandoned)
    
    def test_validate_transition_forms_raised(self):
        """Test validation for FormsRaised state."""
        # Valid transition with ticket
        ticket = TicketRef(system="ServiceNow", id="SN-12345", kind="NSSR")
        evidence = Evidence(tickets=[ticket])
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.not_started,
            EnvState.forms_raised,
            EnvName.dev,
            evidence
        )
        
        assert is_valid
        assert len(errors) == 0
        
        # Invalid transition without ticket
        empty_evidence = Evidence()
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.not_started,
            EnvState.forms_raised,
            EnvName.dev,
            empty_evidence
        )
        
        assert not is_valid
        assert "FormsRaised requires at least one ticket" in errors
    
    def test_validate_transition_creds_issued(self):
        """Test validation for CredsIssued state."""
        # Valid transition with secret
        secret = SecretRef(name="test/secret", mask="****1234")
        evidence = Evidence(secret=secret)
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.forms_raised,
            EnvState.creds_issued,
            EnvName.dev,
            evidence
        )
        
        assert is_valid
        assert len(errors) == 0
        
        # Invalid transition without secret
        empty_evidence = Evidence()
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.forms_raised,
            EnvState.creds_issued,
            EnvName.dev,
            empty_evidence
        )
        
        assert not is_valid
        assert "CredsIssued requires client secret evidence" in errors
    
    def test_validate_transition_access_provisioned(self):
        """Test validation for AccessProvisioned state."""
        # Dev/Staging require GLAM tickets
        glam_ticket = TicketRef(system="ServiceNow", id="GW-12345", kind="GLAM")
        evidence = Evidence(tickets=[glam_ticket])
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.creds_issued,
            EnvState.access_provisioned,
            EnvName.dev,
            evidence
        )
        
        assert is_valid
        assert len(errors) == 0
        
        # Prod doesn't require GLAM tickets
        empty_evidence = Evidence()
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.creds_issued,
            EnvState.access_provisioned,
            EnvName.prod,
            empty_evidence
        )
        
        assert is_valid
        assert len(errors) == 0
        
        # Dev without GLAM should fail
        is_valid, errors = StateMachine.validate_transition(
            EnvState.creds_issued,
            EnvState.access_provisioned,
            EnvName.dev,
            empty_evidence
        )
        
        assert not is_valid
        assert "dev requires GLAM/GWAM tickets" in errors[0]
    
    def test_validate_transition_validated(self):
        """Test validation for Validated state."""
        # Valid transition with all 4 screenshots
        screenshots = [
            ScreenshotRef(key="test/login", label="login"),
            ScreenshotRef(key="test/consent", label="consent"),
            ScreenshotRef(key="test/landing", label="landing"),
            ScreenshotRef(key="test/token", label="token"),
        ]
        evidence = Evidence(screenshots=screenshots)
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.access_provisioned,
            EnvState.validated,
            EnvName.dev,
            evidence
        )
        
        assert is_valid
        assert len(errors) == 0
        
        # Invalid transition with missing screenshots
        partial_screenshots = [
            ScreenshotRef(key="test/login", label="login"),
            ScreenshotRef(key="test/consent", label="consent"),
        ]
        partial_evidence = Evidence(screenshots=partial_screenshots)
        
        is_valid, errors = StateMachine.validate_transition(
            EnvState.access_provisioned,
            EnvState.validated,
            EnvName.dev,
            partial_evidence
        )
        
        assert not is_valid
        assert "Validation requires screenshots" in errors[0]
        assert "landing" in errors[0]
        assert "token" in errors[0]
    
    def test_get_next_actions(self):
        """Test getting next actions for each state."""
        thread = ClientThread(
            display_name="TestClient",
            owner="test_user",
            created_by="test_user"
        )
        
        env = thread.environments[EnvName.dev]
        
        # Test NotStarted state
        env.state = EnvState.not_started
        actions = StateMachine.get_next_actions(env, thread)
        
        assert "Create NSSR/OAuth ticket" in actions
        assert "Create GLAM/GWAM tickets" in actions
        assert "Generate redirect URIs" in actions
        
        # Test Validated state
        env.state = EnvState.validated
        actions = StateMachine.get_next_actions(env, thread)
        
        assert "Send sign-off email" in actions[0]
        
        # Test Complete state for Prod
        prod_env = thread.environments[EnvName.prod]
        prod_env.state = EnvState.approved
        actions = StateMachine.get_next_actions(prod_env, thread)
        
        assert "Production ready" in actions[0]
    
    def test_get_blockers(self):
        """Test getting blockers for environments."""
        thread = ClientThread(
            display_name="TestClient",
            owner="test_user",
            created_by="test_user"
        )
        
        env = thread.environments[EnvName.dev]
        
        # Test Blocked state
        env.state = EnvState.blocked
        blockers = StateMachine.get_blockers(env, thread)
        
        assert "Environment is blocked" in blockers[0]
        
        # Test ChangesRequested state
        env.state = EnvState.changes_requested
        blockers = StateMachine.get_blockers(env, thread)
        
        assert "Changes requested" in blockers[0]
        
        # Test FormsRaised with open tickets
        env.state = EnvState.forms_raised
        ticket = TicketRef(system="ServiceNow", id="SN-12345", kind="NSSR", status="open")
        env.evidence.tickets = [ticket]
        blockers = StateMachine.get_blockers(env, thread)
        
        assert "SN-12345" in blockers[0]
        assert "still open" in blockers[0]
    
    def test_calculate_progress(self):
        """Test progress calculation."""
        thread = ClientThread(
            display_name="TestClient",
            owner="test_user",
            created_by="test_user"
        )
        
        # All environments at NotStarted = 0% progress
        progress = StateMachine.calculate_progress(thread)
        assert progress == 0.0
        
        # Dev complete, others not started
        thread.environments[EnvName.dev].state = EnvState.complete
        progress = StateMachine.calculate_progress(thread)
        assert 0.3 < progress < 0.4  # Roughly 1/3
        
        # All environments complete = 100% progress
        thread.environments[EnvName.staging].state = EnvState.complete
        thread.environments[EnvName.prod].state = EnvState.complete
        progress = StateMachine.calculate_progress(thread)
        assert progress == 1.0
    
    def test_get_current_environment(self):
        """Test getting current environment."""
        thread = ClientThread(
            display_name="TestClient",
            owner="test_user",
            created_by="test_user"
        )
        
        # All environments at NotStarted, should return Dev
        current = StateMachine.get_current_environment(thread)
        assert current == EnvName.dev
        
        # Dev complete, should return Staging
        thread.environments[EnvName.dev].state = EnvState.complete
        current = StateMachine.get_current_environment(thread)
        assert current == EnvName.staging
        
        # Dev and Staging complete, should return Prod
        thread.environments[EnvName.staging].state = EnvState.complete
        current = StateMachine.get_current_environment(thread)
        assert current == EnvName.prod
        
        # All complete, should return None
        thread.environments[EnvName.prod].state = EnvState.complete
        current = StateMachine.get_current_environment(thread)
        assert current is None
