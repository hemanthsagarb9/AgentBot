import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models import CommandRequest, TicketUpdate, EmailUpdate


class TestAPI:
    """Test FastAPI endpoints."""
    
    def test_root_endpoint(self):
        """Test root endpoint."""
        client = TestClient(app)
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Ping SSO Onboarding Agent"
        assert data["version"] == "0.9.0"
        assert data["status"] == "running"
    
    def test_health_check(self):
        """Test health check endpoint."""
        client = TestClient(app)
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    @patch('app.main.agent')
    def test_execute_command_success(self, mock_agent):
        """Test successful command execution."""
        client = TestClient(app)
        
        # Mock agent response
        mock_result = AsyncMock()
        mock_result.success = True
        mock_result.message = "Command executed successfully"
        mock_result.thread_id = "test-thread-123"
        mock_result.details = {}
        mock_result.model_dump.return_value = {
            "message": "Command executed successfully",
            "thread_id": "test-thread-123",
            "success": True,
            "details": {}
        }
        
        mock_agent.execute_command = AsyncMock(return_value=mock_result)
        
        response = client.post("/agent/command", json={
            "text": "Onboard TestClient",
            "user_id": "test_user"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Command executed successfully"
        assert data["thread_id"] == "test-thread-123"
    
    @patch('app.main.agent')
    def test_execute_command_error(self, mock_agent):
        """Test command execution error."""
        client = TestClient(app)
        
        mock_agent.execute_command = AsyncMock(side_effect=Exception("Test error"))
        
        response = client.post("/agent/command", json={
            "text": "Onboard TestClient",
            "user_id": "test_user"
        })
        
        assert response.status_code == 500
        data = response.json()
        assert "Test error" in data["detail"]
    
    @patch('app.main.thread_repo')
    def test_get_thread_status_success(self, mock_repo):
        """Test successful thread status retrieval."""
        client = TestClient(app)
        
        # Mock thread
        mock_thread = AsyncMock()
        mock_thread.thread_id = "test-thread-123"
        mock_thread.display_name = "TestClient"
        mock_thread.environments = {}
        mock_thread.model_dump.return_value = {
            "thread_id": "test-thread-123",
            "display_name": "TestClient"
        }
        
        mock_repo.get_thread = AsyncMock(return_value=mock_thread)
        
        with patch('app.main.StateMachine') as mock_sm:
            mock_sm.calculate_progress.return_value = 0.5
            mock_sm.get_current_environment.return_value = None
            
            response = client.get("/threads/test-thread-123")
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_progress"] == 0.5
            assert "thread" in data
    
    @patch('app.main.thread_repo')
    def test_get_thread_status_not_found(self, mock_repo):
        """Test thread status for non-existent thread."""
        client = TestClient(app)
        
        mock_repo.get_thread = AsyncMock(return_value=None)
        
        response = client.get("/threads/non-existent")
        
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('app.main.thread_repo')
    def test_list_threads_success(self, mock_repo):
        """Test successful thread listing."""
        client = TestClient(app)
        
        # Mock threads
        mock_thread = AsyncMock()
        mock_thread.thread_id = "test-thread-123"
        mock_thread.display_name = "TestClient"
        mock_thread.owner = "test_user"
        mock_thread.created_at.isoformat.return_value = "2024-01-01T00:00:00"
        mock_thread.last_update.isoformat.return_value = "2024-01-01T00:00:00"
        mock_thread.blockers = []
        mock_thread.next_actions = ["Create NSSR ticket"]
        
        mock_repo.list_threads = AsyncMock(return_value=[mock_thread])
        
        with patch('app.main.StateMachine') as mock_sm:
            mock_sm.calculate_progress.return_value = 0.2
            mock_sm.get_current_environment.return_value = AsyncMock()
            mock_sm.get_current_environment.return_value.value = "dev"
            
            response = client.get("/threads")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert len(data["threads"]) == 1
            assert data["threads"][0]["display_name"] == "TestClient"
    
    @patch('app.main.thread_repo')
    def test_handle_ticket_update(self, mock_repo):
        """Test ticket update webhook."""
        client = TestClient(app)
        
        # Mock threads with tickets
        mock_thread = AsyncMock()
        mock_thread.thread_id = "test-thread-123"
        mock_thread.environments = {}
        
        mock_repo.list_threads = AsyncMock(return_value=[mock_thread])
        mock_repo.update_thread = AsyncMock(return_value=mock_thread)
        
        response = client.post("/webhooks/ticketing", json={
            "ticket_id": "SN-12345",
            "system": "ServiceNow",
            "status": "resolved",
            "details": {}
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "Processed ticket update" in data["message"]
        assert "SN-12345" in data["message"]
    
    @patch('app.main.thread_repo')
    def test_handle_email_update(self, mock_repo):
        """Test email update webhook."""
        client = TestClient(app)
        
        # Mock thread
        mock_thread = AsyncMock()
        mock_thread.thread_id = "test-thread-123"
        mock_thread.environments = {}
        
        mock_repo.get_thread = AsyncMock(return_value=mock_thread)
        
        response = client.post("/webhooks/email", json={
            "message_id": "<msg123@test.com>",
            "thread_id": "test-thread-123",
            "subject": "Approved: Ping SSO Dev Sign-off",
            "sender": "approver@company.com",
            "content": "Approved for next environment"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "Processed email update" in data["message"]
    
    @patch('app.main.thread_repo')
    def test_get_audit_logs(self, mock_repo):
        """Test audit logs endpoint."""
        client = TestClient(app)
        
        # Mock audit logs
        mock_log = AsyncMock()
        mock_log.model_dump.return_value = {
            "id": 1,
            "thread_id": "test-thread-123",
            "actor": "test_user",
            "action": "thread_created",
            "details": {},
            "created_at": "2024-01-01T00:00:00"
        }
        
        mock_repo.get_audit_logs = AsyncMock(return_value=[mock_log])
        
        response = client.get("/threads/test-thread-123/audit")
        
        assert response.status_code == 200
        data = response.json()
        assert data["thread_id"] == "test-thread-123"
        assert data["count"] == 1
        assert len(data["logs"]) == 1
