import pytest
from unittest.mock import AsyncMock, patch

from app.models import CommandRequest, EnvName, EnvState
from app.agent import PingSSOAgent


class TestPingSSOAgent:
    """Test PydanticAI agent functionality."""
    
    @pytest.mark.asyncio
    async def test_parse_command_intent_onboard(self, test_agent):
        """Test parsing onboard command."""
        intent = test_agent._parse_command_intent("Onboard Galaxy")
        
        assert intent["intent"] == "onboard"
        assert intent["client"] == "galaxy"
        assert intent["params"] == {}
    
    @pytest.mark.asyncio
    async def test_parse_command_intent_status(self, test_agent):
        """Test parsing status command."""
        intent = test_agent._parse_command_intent("Status of BusinessBanking")
        
        assert intent["intent"] == "status"
        assert intent["client"] == "businessbanking"
        assert intent["params"] == {}
        
        # Alternative format
        intent = test_agent._parse_command_intent("Status Galaxy")
        assert intent["intent"] == "status"
        assert intent["client"] == "galaxy"
    
    @pytest.mark.asyncio
    async def test_parse_command_intent_move(self, test_agent):
        """Test parsing move command."""
        intent = test_agent._parse_command_intent("Move Galaxy to staging")
        
        assert intent["intent"] == "move"
        assert intent["client"] == "galaxy"
        assert intent["params"]["target_env"] == "staging"
    
    @pytest.mark.asyncio
    async def test_parse_command_intent_prepare_prod(self, test_agent):
        """Test parsing prepare prod command."""
        intent = test_agent._parse_command_intent("Prepare prod for Galaxy")
        
        assert intent["intent"] == "prepare_prod"
        assert intent["client"] == "galaxy"
        assert intent["params"] == {}
    
    @pytest.mark.asyncio
    async def test_parse_command_intent_unknown(self, test_agent):
        """Test parsing unknown command."""
        intent = test_agent._parse_command_intent("Do something weird")
        
        assert intent["intent"] == "unknown"
        assert intent["client"] is None
    
    def test_redact_pii(self, test_agent):
        """Test PII redaction."""
        text = "User ABC-123 with email john.doe@company.com created ticket SN-98765"
        redacted = test_agent._redact_pii(text)
        
        assert "ABC-123" not in redacted
        assert "john.doe@company.com" not in redacted
        assert "SN-98765" not in redacted
        assert "LANID-" in redacted
        assert "EMAIL-" in redacted
        assert "SN-****" in redacted
    
    @pytest.mark.asyncio
    async def test_execute_command_onboard(self, test_agent):
        """Test executing onboard command."""
        request = CommandRequest(
            text="Onboard TestClient",
            user_id="test_user"
        )
        
        with patch('app.tools.create_client_thread') as mock_create, \
             patch('app.tools.generate_redirect_uris') as mock_uris, \
             patch('app.tools.create_nssr_ticket') as mock_nssr, \
             patch('app.tools.create_glam_gwam_ticket') as mock_glam, \
             patch('app.tools.update_env_state') as mock_update:
            
            # Setup mocks
            mock_create.return_value = "test-thread-123"
            mock_uris.return_value = AsyncMock()
            mock_nssr.return_value = AsyncMock()
            mock_glam.return_value = AsyncMock()
            mock_update.return_value = True
            
            result = await test_agent.execute_command(request)
            
            assert result.success
            assert "TestClient" in result.message
            assert result.thread_id == "test-thread-123"
            
            # Verify tools were called
            mock_create.assert_called_once()
            mock_nssr.assert_called_once()
            mock_glam.assert_called_once()
            mock_update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_command_status_not_found(self, test_agent, thread_repo):
        """Test status command for non-existent client."""
        request = CommandRequest(
            text="Status of NonExistentClient",
            user_id="test_user"
        )
        
        result = await test_agent.execute_command(request)
        
        assert not result.success
        assert "not found" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_execute_command_status_found(self, test_agent, sample_thread):
        """Test status command for existing client."""
        request = CommandRequest(
            text="Status of TestClient",
            user_id="test_user"
        )
        
        with patch('app.tools.get_thread_status') as mock_status:
            mock_status.return_value = {
                "thread_id": sample_thread.thread_id,
                "display_name": sample_thread.display_name,
                "overall_progress": 0.1,
                "current_environment": "dev",
                "environments": {
                    "dev": {
                        "state": "NotStarted",
                        "evidence": {
                            "tickets": 0,
                            "screenshots": 0,
                            "has_secret": False
                        }
                    },
                    "staging": {"state": "NotStarted", "evidence": {"tickets": 0, "screenshots": 0, "has_secret": False}},
                    "prod": {"state": "NotStarted", "evidence": {"tickets": 0, "screenshots": 0, "has_secret": False}}
                },
                "blockers": [],
                "next_actions": ["Create NSSR/OAuth ticket"]
            }
            
            result = await test_agent.execute_command(request)
            
            assert result.success
            assert "TestClient" in result.message
            assert "Progress: 10.0%" in result.message
            assert result.thread_id == sample_thread.thread_id
    
    @pytest.mark.asyncio
    async def test_execute_command_unknown(self, test_agent):
        """Test executing unknown command."""
        request = CommandRequest(
            text="Do something weird",
            user_id="test_user"
        )
        
        result = await test_agent.execute_command(request)
        
        assert not result.success
        assert "Unknown command" in result.message
        assert "Available commands" in result.message
    
    @pytest.mark.asyncio
    async def test_execute_command_error_handling(self, test_agent):
        """Test error handling in command execution."""
        request = CommandRequest(
            text="Onboard TestClient",
            user_id="test_user"
        )
        
        with patch('app.tools.create_client_thread') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            result = await test_agent.execute_command(request)
            
            assert not result.success
            assert "Error executing command" in result.message
            assert "Database error" in result.message
