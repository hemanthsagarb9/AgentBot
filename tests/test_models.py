import pytest
from datetime import datetime
from pydantic import ValidationError

from app.models import (
    EnvName, EnvState, TicketRef, SecretRef, ScreenshotRef, 
    Evidence, RedirectUris, PeopleSet, Environment, 
    ClientThread, CommandResult, CommandRequest
)


class TestModels:
    """Test Pydantic models."""
    
    def test_env_name_enum(self):
        """Test EnvName enum."""
        assert EnvName.dev == "dev"
        assert EnvName.staging == "staging"
        assert EnvName.prod == "prod"
    
    def test_env_state_enum(self):
        """Test EnvState enum."""
        assert EnvState.not_started == "NotStarted"
        assert EnvState.complete == "Complete"
        assert EnvState.blocked == "Blocked"
    
    def test_ticket_ref(self):
        """Test TicketRef model."""
        ticket = TicketRef(
            system="ServiceNow",
            id="SN-12345",
            url="https://test.service-now.com/incident.do?sys_id=12345",
            kind="NSSR"
        )
        
        assert ticket.system == "ServiceNow"
        assert ticket.id == "SN-12345"
        assert ticket.kind == "NSSR"
        assert ticket.status == "open"  # default
        assert isinstance(ticket.created_at, datetime)
    
    def test_secret_ref(self):
        """Test SecretRef model."""
        secret = SecretRef(
            name="pingsso/testclient/dev/client_secret",
            mask="****abc123"
        )
        
        assert secret.name == "pingsso/testclient/dev/client_secret"
        assert secret.mask == "****abc123"
        assert isinstance(secret.created_at, datetime)
    
    def test_screenshot_ref(self):
        """Test ScreenshotRef model."""
        screenshot = ScreenshotRef(
            key="screenshots/testclient/dev/login_20240101_120000.png",
            label="login",
            url="https://s3.amazonaws.com/bucket/key"
        )
        
        assert screenshot.key == "screenshots/testclient/dev/login_20240101_120000.png"
        assert screenshot.label == "login"
        assert screenshot.url == "https://s3.amazonaws.com/bucket/key"
        assert isinstance(screenshot.uploaded_at, datetime)
    
    def test_evidence(self):
        """Test Evidence model."""
        ticket = TicketRef(system="ServiceNow", id="SN-12345", kind="NSSR")
        secret = SecretRef(name="test/secret", mask="****1234")
        screenshot = ScreenshotRef(key="test/key", label="login")
        
        evidence = Evidence(
            tickets=[ticket],
            secret=secret,
            screenshots=[screenshot],
            emails=["<msg123@test.com>"],
            notes=["Test note"]
        )
        
        assert len(evidence.tickets) == 1
        assert evidence.secret.name == "test/secret"
        assert len(evidence.screenshots) == 1
        assert len(evidence.emails) == 1
        assert len(evidence.notes) == 1
    
    def test_redirect_uris(self):
        """Test RedirectUris model."""
        uris = RedirectUris(
            web_callback="https://dev.testclient.ourdomain.com/api/auth/callback/ping",
            post_logout="https://dev.testclient.ourdomain.com/auth/logout/callback"
        )
        
        assert str(uris.web_callback) == "https://dev.testclient.ourdomain.com/api/auth/callback/ping"
        assert str(uris.post_logout) == "https://dev.testclient.ourdomain.com/auth/logout/callback"
        assert uris.api_callback is None
    
    def test_people_set(self):
        """Test PeopleSet model."""
        people = PeopleSet(
            lanids=["ABC123", "DEF456"],
            approvers=["john.doe", "jane.smith"],
            contacts={"tech_lead": "john.doe@company.com"}
        )
        
        assert len(people.lanids) == 2
        assert len(people.approvers) == 2
        assert people.contacts["tech_lead"] == "john.doe@company.com"
    
    def test_environment(self):
        """Test Environment model."""
        env = Environment(
            name=EnvName.dev,
            state=EnvState.not_started
        )
        
        assert env.name == EnvName.dev
        assert env.state == EnvState.not_started
        assert isinstance(env.evidence, Evidence)
        assert isinstance(env.people, PeopleSet)
        assert isinstance(env.last_updated, datetime)
    
    def test_client_thread(self):
        """Test ClientThread model."""
        thread = ClientThread(
            display_name="TestClient",
            owner="test_user",
            created_by="test_user"
        )
        
        assert thread.display_name == "TestClient"
        assert thread.owner == "test_user"
        assert thread.created_by == "test_user"
        assert isinstance(thread.thread_id, str)
        assert len(thread.thread_id) > 0
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.last_update, datetime)
        
        # Check environments are initialized
        assert len(thread.environments) == 3
        assert EnvName.dev in thread.environments
        assert EnvName.staging in thread.environments
        assert EnvName.prod in thread.environments
        
        # Check all environments start in not_started state
        for env in thread.environments.values():
            assert env.state == EnvState.not_started
    
    def test_command_request(self):
        """Test CommandRequest model."""
        request = CommandRequest(
            text="Onboard TestClient",
            user_id="test_user"
        )
        
        assert request.text == "Onboard TestClient"
        assert request.user_id == "test_user"
        assert isinstance(request.request_id, str)
    
    def test_command_result(self):
        """Test CommandResult model."""
        result = CommandResult(
            message="Successfully onboarded TestClient",
            thread_id="test-thread-123",
            success=True,
            details={"tickets": ["SN-12345"]}
        )
        
        assert result.message == "Successfully onboarded TestClient"
        assert result.thread_id == "test-thread-123"
        assert result.success is True
        assert result.details["tickets"] == ["SN-12345"]
    
    def test_invalid_redirect_uri(self):
        """Test invalid redirect URI validation."""
        with pytest.raises(ValidationError):
            RedirectUris(
                web_callback="not-a-valid-url"
            )
