from sqlalchemy import create_engine, Column, String, DateTime, JSON, Text, Integer, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any
import json

from app.models import (
    ClientThread, Environment, Evidence, TicketRef, SecretRef, 
    ScreenshotRef, RedirectUris, PeopleSet, EnvName, EnvState,
    AuditLog, AppConfig
)

Base = declarative_base()


class ClientThreadDB(Base):
    __tablename__ = "client_thread"
    
    thread_id = Column(String, primary_key=True)
    display_name = Column(String, nullable=False)
    owner = Column(String, nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    last_update = Column(DateTime, default=func.now(), onupdate=func.now())
    blockers = Column(JSON, default=list)
    next_actions = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)


class EnvironmentStateDB(Base):
    __tablename__ = "environment_state"
    
    thread_id = Column(String, ForeignKey("client_thread.thread_id"), primary_key=True)
    env = Column(String, primary_key=True)
    state = Column(String, nullable=False)
    data = Column(JSON, default=dict)


class EvidenceDB(Base):
    __tablename__ = "evidence"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, nullable=False)
    env = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # 'ticket', 'secret', 'screenshot', 'email'
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now())


class AuditLogDB(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, nullable=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=func.now())


class ThreadRepository:
    """Repository for thread persistence operations."""
    
    def __init__(self, session_factory):
        self.session_factory = session_factory
    
    def _serialize_environment(self, env: Environment) -> Dict[str, Any]:
        """Serialize Environment to JSON-serializable dict."""
        return {
            "name": env.name.value,
            "state": env.state.value,
            "evidence": {
                "tickets": [ticket.model_dump() for ticket in env.evidence.tickets],
                "secret": env.evidence.secret.model_dump() if env.evidence.secret else None,
                "screenshots": [screenshot.model_dump() for screenshot in env.evidence.screenshots],
                "emails": env.evidence.emails,
                "notes": env.evidence.notes
            },
            "redirect_uris": env.redirect_uris.model_dump() if env.redirect_uris else None,
            "people": {
                "lanids": env.people.lanids,
                "approvers": env.people.approvers,
                "contacts": env.people.contacts
            },
            "last_updated": env.last_updated.isoformat()
        }
    
    def _deserialize_environment(self, env_name: str, data: Dict[str, Any]) -> Environment:
        """Deserialize Environment from JSON dict."""
        return Environment(
            name=EnvName(env_name),
            state=EnvState(data["state"]),
            evidence=Evidence(
                tickets=[TicketRef(**t) for t in data["evidence"]["tickets"]],
                secret=SecretRef(**data["evidence"]["secret"]) if data["evidence"]["secret"] else None,
                screenshots=[ScreenshotRef(**s) for s in data["evidence"]["screenshots"]],
                emails=data["evidence"]["emails"],
                notes=data["evidence"]["notes"]
            ),
            redirect_uris=RedirectUris(**data["redirect_uris"]) if data["redirect_uris"] else None,
            people=PeopleSet(
                lanids=data["people"]["lanids"],
                approvers=data["people"]["approvers"],
                contacts=data["people"]["contacts"]
            ),
            last_updated=datetime.fromisoformat(data["last_updated"])
        )
    
    async def create_thread(self, thread: ClientThread) -> ClientThread:
        """Create a new client thread."""
        with self.session_factory() as session:
            # Create main thread record
            thread_db = ClientThreadDB(
                thread_id=thread.thread_id,
                display_name=thread.display_name,
                owner=thread.owner,
                created_by=thread.created_by,
                created_at=thread.created_at,
                last_update=thread.last_update,
                blockers=thread.blockers,
                next_actions=thread.next_actions,
                metadata=thread.metadata
            )
            session.add(thread_db)
            
            # Create environment states
            for env_name, env in thread.environments.items():
                env_data = self._serialize_environment(env)
                env_db = EnvironmentStateDB(
                    thread_id=thread.thread_id,
                    env=env_name.value,
                    state=env.state.value,
                    data=env_data
                )
                session.add(env_db)
            
            session.commit()
            return thread
    
    async def get_thread(self, thread_id: str) -> Optional[ClientThread]:
        """Get a client thread by ID."""
        with self.session_factory() as session:
            thread_db = session.query(ClientThreadDB).filter(
                ClientThreadDB.thread_id == thread_id
            ).first()
            
            if not thread_db:
                return None
            
            # Get environment states
            env_states = session.query(EnvironmentStateDB).filter(
                EnvironmentStateDB.thread_id == thread_id
            ).all()
            
            environments = {}
            for env_state in env_states:
                env = self._deserialize_environment(env_state.env, env_state.data)
                environments[env.name] = env
            
            return ClientThread(
                thread_id=thread_db.thread_id,
                display_name=thread_db.display_name,
                environments=environments,
                owner=thread_db.owner,
                created_by=thread_db.created_by,
                created_at=thread_db.created_at,
                last_update=thread_db.last_update,
                blockers=thread_db.blockers,
                next_actions=thread_db.next_actions,
                metadata=thread_db.metadata
            )
    
    async def update_thread(self, thread: ClientThread) -> ClientThread:
        """Update an existing client thread."""
        with self.session_factory() as session:
            # Update main thread record
            thread_db = session.query(ClientThreadDB).filter(
                ClientThreadDB.thread_id == thread.thread_id
            ).first()
            
            if not thread_db:
                raise ValueError(f"Thread {thread.thread_id} not found")
            
            thread_db.display_name = thread.display_name
            thread_db.owner = thread.owner
            thread_db.last_update = thread.last_update
            thread_db.blockers = thread.blockers
            thread_db.next_actions = thread.next_actions
            thread_db.metadata = thread.metadata
            
            # Update environment states
            for env_name, env in thread.environments.items():
                env_data = self._serialize_environment(env)
                env_db = session.query(EnvironmentStateDB).filter(
                    EnvironmentStateDB.thread_id == thread.thread_id,
                    EnvironmentStateDB.env == env_name.value
                ).first()
                
                if env_db:
                    env_db.state = env.state.value
                    env_db.data = env_data
                else:
                    env_db = EnvironmentStateDB(
                        thread_id=thread.thread_id,
                        env=env_name.value,
                        state=env.state.value,
                        data=env_data
                    )
                    session.add(env_db)
            
            session.commit()
            return thread
    
    async def list_threads(self, owner: Optional[str] = None) -> List[ClientThread]:
        """List client threads, optionally filtered by owner."""
        with self.session_factory() as session:
            query = session.query(ClientThreadDB)
            if owner:
                query = query.filter(ClientThreadDB.owner == owner)
            
            thread_dbs = query.all()
            threads = []
            
            for thread_db in thread_dbs:
                thread = await self.get_thread(thread_db.thread_id)
                if thread:
                    threads.append(thread)
            
            return threads
    
    async def add_audit_log(self, audit_log: AuditLog) -> AuditLog:
        """Add an audit log entry."""
        with self.session_factory() as session:
            audit_db = AuditLogDB(
                thread_id=audit_log.thread_id,
                actor=audit_log.actor,
                action=audit_log.action,
                details=audit_log.details,
                created_at=audit_log.created_at
            )
            session.add(audit_db)
            session.commit()
            
            audit_log.id = audit_db.id
            return audit_log
    
    async def get_audit_logs(self, thread_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for a thread."""
        with self.session_factory() as session:
            audit_dbs = session.query(AuditLogDB).filter(
                AuditLogDB.thread_id == thread_id
            ).order_by(AuditLogDB.created_at.desc()).limit(limit).all()
            
            return [
                AuditLog(
                    id=audit_db.id,
                    thread_id=audit_db.thread_id,
                    actor=audit_db.actor,
                    action=audit_db.action,
                    details=audit_db.details,
                    created_at=audit_db.created_at
                )
                for audit_db in audit_dbs
            ]


def create_database_session(config: AppConfig):
    """Create database session factory."""
    engine = create_engine(config.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_database(config: AppConfig):
    """Initialize database tables."""
    engine = create_engine(config.database_url)
    Base.metadata.create_all(bind=engine)
