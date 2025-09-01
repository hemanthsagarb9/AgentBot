import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models import AppConfig, ClientThread, EnvName
from app.database import Base, ThreadRepository
from app.agent import PingSSOAgent
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Test configuration."""
    return AppConfig(
        database_url="sqlite:///./test.db",
        aws_region="us-east-1",
        s3_bucket="test-bucket",
        secrets_manager_prefix="test",
        smtp_host=None,  # Disable email in tests
        servicenow_url=None  # Disable ServiceNow in tests
    )


@pytest.fixture
def test_db_session(test_config):
    """Create test database session."""
    engine = create_engine(test_config.database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def thread_repo(test_db_session):
    """Create thread repository for testing."""
    return ThreadRepository(lambda: test_db_session)


@pytest.fixture
def test_agent(test_config, thread_repo):
    """Create test agent."""
    agent = PingSSOAgent(test_config)
    agent.set_thread_repo(thread_repo)
    return agent


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def sample_thread(thread_repo):
    """Create a sample thread for testing."""
    thread = ClientThread(
        display_name="TestClient",
        owner="test_user",
        created_by="test_user"
    )
    
    # Add some test data
    thread.environments[EnvName.dev].people.lanids = ["TEST123", "TEST456"]
    
    await thread_repo.create_thread(thread)
    return thread
