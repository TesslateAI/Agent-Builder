"""
Database models and utilities for Agent-Builder
Provides SQLite storage for flows and projects
"""
import os
import json
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Projects, Flow, FlowExecution, Organizations, Users, Roles, UserProjectRoles, AuditLog, UserSession

logger = logging.getLogger("Database")

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "agent_builder.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)
LocalSession = sessionmaker(bind=engine)

# Project management
def create_project(
    project_id: str,
    name: str,
    description: str = "",
    organization_id: str = "default_org",
    owner_id: str = "system"
) -> Dict[str, Any]:
    """Create a new project (with organization and owner support)"""
    with LocalSession() as session:
        new_project = Projects(
            id=project_id,
            name=name,
            description=description,
            organization_id=organization_id,
            owner_id=owner_id
        )
        session.add(new_project)
        session.commit()
        session.refresh(new_project)
        return {
            "id": new_project.id,
            "name": new_project.name,
            "description": new_project.description,
            "organization_id": new_project.organization_id,
            "owner_id": new_project.owner_id,
            "created_at": new_project.created_at,
            "updated_at": new_project.updated_at
        }

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get a project by ID"""
    with LocalSession() as session:
        project = session.query(Projects).filter(Projects.id == project_id).first()
        if project:
            return {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "created_at": project.created_at,
                "updated_at": project.updated_at
            }
        return None
    
def list_projects() -> List[Dict[str, Any]]:
    """List all projects"""
    with LocalSession() as session:
        projects = session.query(Projects).order_by(Projects.updated_at.desc()).all()
        return [{
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        } for project in projects]

# Flow management
def save_flow(
    flow_id: str,
    project_id: str,
    name: str,
    nodes: List[Dict],
    edges: List[Dict],
    description: str = "",
    flow_metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """Save or update a flow"""
    with LocalSession() as session:
        # Check if flow exists
        flow = session.query(Flow).filter(Flow.id == flow_id).first()

        if flow:
            flow.name = name
            flow.description = description
            flow.nodes = nodes
            flow.edges = edges
            flow.flow_metadata = flow_metadata or {}
            flow.updated_at = datetime.now(timezone.utc)
        else:
            flow = Flow(
                id=flow_id,
                project_id=project_id,
                name=name,
                description=description,
                nodes=nodes,
                edges=edges,
                flow_metadata=flow_metadata or {},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(flow)

        session.commit()
        session.refresh(flow)

        return {
            "id": flow.id,
            "project_id": flow.project_id,
            "name": flow.name,
            "description": flow.description,
            "nodes": flow.nodes,
            "edges": flow.edges,
            "flow_metadata": flow.flow_metadata,
            "created_at": flow.created_at.isoformat() if flow.created_at else None,
            "updated_at": flow.updated_at.isoformat() if flow.updated_at else None
        }

def get_flow(flow_id: str) -> Optional[Dict[str, Any]]:
    """Get a flow by ID"""
    with LocalSession() as session:
        flow = session.query(Flow).filter(Flow.id == flow_id).first()
        if flow:
            return {
                "id": flow.id,
                "project_id": flow.project_id,
                "name": flow.name,
                "description": flow.description,
                "nodes": flow.nodes,
                "edges": flow.edges,
                "flow_metadata": flow.flow_metadata,
                "created_at": flow.created_at.isoformat(),
                "updated_at": flow.updated_at.isoformat()
            }
        return None

def list_flows(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List flows, optionally filtered by project"""
    with LocalSession() as session:
        query = session.query(Flow)
        if project_id:
            query = query.filter(Flow.project_id == project_id)
        flows = query.order_by(Flow.updated_at.desc()).all()
        return [{
            "id": flow.id,
            "project_id": flow.project_id,
            "name": flow.name,
            "description": flow.description,
            "nodes": flow.nodes,
            "edges": flow.edges,
            "flow_metadata": flow.flow_metadata,
            "created_at": flow.created_at.isoformat(),
            "updated_at": flow.updated_at.isoformat()
        } for flow in flows]

def delete_flow(flow_id: str) -> bool:
    """Delete a flow"""
    with LocalSession() as session:
        flow = session.query(Flow).filter(Flow.id == flow_id).first()
        if flow:
            session.delete(flow)
            session.commit()
            return True
        return False

# Flow execution tracking
def create_flow_execution(
    flow_id: str,
    input_data: Optional[Dict] = None
) -> int:
    """Create a new flow execution record"""
    with LocalSession() as session:
        execution = FlowExecution(
            flow_id=flow_id,
            status='running',
            input_data=input_data or {}
        )
        session.add(execution)
        session.commit()
        return execution.id

def update_flow_execution(
    execution_id: int,
    status: str,
    output_data: Optional[Dict] = None,
    error_message: Optional[str] = None
):
    """Update flow execution status"""
    with LocalSession() as session:
        execution = session.get(FlowExecution, execution_id)
        if execution:
            execution.status = status
            execution.output_data = output_data or {}
            execution.error_message = error_message
            if status in ['completed', 'failed']:
                execution.completed_at = datetime.now(timezone.utc)
            session.commit()
        else:
            logger.warning(f"FlowExecution with ID {execution_id} not found.")

def get_flow_executions(flow_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent executions for a flow"""
    with LocalSession() as session:
        executions = (
            session.query(FlowExecution)
            .filter(FlowExecution.flow_id == flow_id)
            .order_by(FlowExecution.started_at.desc())
            .limit(limit)
            .all()
        )
        return [{
            "id": execution.id,
            "flow_id": execution.flow_id,
            "status": execution.status,
            "input_data": execution.input_data or {},
            "output_data": execution.output_data or {},
            "error_message": execution.error_message,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None
        } for execution in executions
        ]

# Organization management
def create_organization(
    org_id: str,
    name: str,
    description: str = "",
    settings: Optional[Dict] = None
) -> Dict[str, Any]:
    """Create a new organization"""
    with LocalSession() as session:
        org = Organizations(
            id=org_id,
            name=name,
            description=description,
            settings=settings or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        session.add(org)
        session.commit()
        session.refresh(org)
        return {
            "id": org.id,
            "name": org.name,
            "description": org.description,
            "settings": org.settings or {},
            "created_at": org.created_at.isoformat(),
            "updated_at": org.updated_at.isoformat()
        }

def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
    """Get organization by ID"""
    with LocalSession() as session:
        org = session.query(Organizations).filter(Organizations.id == org_id).first()
        if org:
            return {
                "id": org.id,
                "name": org.name,
                "description": org.description,
                "settings": org.settings or '{}',
                "created_at": org.created_at.isoformat(),
                "updated_at": org.updated_at.isoformat()
            }
    return None

def list_organizations() -> List[Dict[str, Any]]:
    """List all organizations"""
    with LocalSession() as session:
        orgs = session.query(Organizations).order_by(Organizations.name).all()
        return [{
            "id": org.id,
            "name": org.name,
            "description": org.description,
            "settings": json.loads(org.settings or '{}'),
            "created_at": org.created_at.isoformat(),
            "updated_at": org.updated_at.isoformat()
        } for org in orgs]

# User management
def create_user(
    user_id: str,
    keycloak_id: str,
    email: str,
    username: str,
    organization_id: str,
    first_name: str = "",
    last_name: str = ""
) -> Dict[str, Any]:
    """Create a new user"""
    with LocalSession() as session:
        user = Users(
            id=user_id,
            keycloak_id=keycloak_id,
            email=email,
            username=username,
            organization_id=organization_id,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return {
            "id": user.id,
            "keycloak_id": user.keycloak_id,
            "email": user.email,
            "username": user.username,
            "organization_id": user.organization_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    with LocalSession() as session:
        user = session.get(Users, user_id)
        if user:
            return {
                "id": user.id,
                "keycloak_id": user.keycloak_id,
                "email": user.email,
                "username": user.username,
                "organization_id": user.organization_id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat() if user.updated_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        return None

def get_user_by_keycloak_id(keycloak_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Keycloak ID"""
    with LocalSession() as session:
        user = session.query(Users).filter(Users.keycloak_id == keycloak_id).first()
        return get_user(user.id) if user else None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    with LocalSession() as session:
        user = session.query(Users).filter(Users.email == email).first()
        return get_user(user.id) if user else None

def update_user_last_login(user_id: str):
    """Update user's last login timestamp"""
    with LocalSession() as session:
        user = session.get(Users, user_id)
        if user:
            user.last_login = datetime.now()
            session.commit()

def list_users_in_organization(org_id: str) -> List[Dict[str, Any]]:
    """List all users in an organization"""
    with LocalSession() as session:
        users = session.query(Users).filter(Users.organization_id == org_id).all()
        return [get_user(user.id) for user in users]

# Role management
def create_role(role_id: str, name: str, permissions: List[str], organization_id: str, description: str = "") -> Dict[str, Any]:
    """Create a new role"""
    with LocalSession() as session:
        role = Roles(
            id=role_id,
            name=name,
            description=description,
            permissions=permissions,
            organization_id=organization_id
        )
        session.add(role)
        session.commit()
        session.refresh(role)
        return {
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": role.permissions,
            "organization_id": role.organization_id,
            "created_at": role.created_at.isoformat()
        }

def get_role(role_id: str) -> Optional[Dict[str, Any]]:
    """Get role by ID"""
    with LocalSession() as session:
        role = session.get(Roles, role_id)
        if role:
            return {
                "id": role.id,
                "name": role.name,
                "description": role.description,
                "permissions": role.permissions,
                "organization_id": role.organization_id,
                "created_at": role.created_at.isoformat()
            }
        return None

def list_roles_in_organization(org_id: str) -> List[Dict[str, Any]]:
    """List all roles in an organization"""
    with LocalSession() as session:
        roles = session.query(Roles).filter(Roles.organization_id == org_id).order_by(Roles.name).all()
        return [{
            "id": role.id,
            "name": role.name,
            "description": role.description,
            "permissions": role.permissions or [],
            "organization_id": role.organization_id,
            "created_at": role.created_at.isoformat()
        } for role in roles]

# User project role assignments
def assign_user_project_role(user_id: str, project_id: str, role_id: str, assigned_by: str = None):
    """Assign a role to a user for a specific project"""
    with LocalSession() as session:
        user_project_role = UserProjectRoles(
            user_id=user_id,
            project_id=project_id,
            role_id=role_id,
            assigned_by=assigned_by
        )
        session.add(user_project_role)
        session.commit()

def remove_user_project_role(user_id: str, project_id: str, role_id: str):
    """Remove a role from a user for a specific project"""
    with LocalSession() as session:
        user_project_role = session.query(UserProjectRoles).filter(
            UserProjectRoles.user_id == user_id,
            UserProjectRoles.project_id == project_id,
            UserProjectRoles.role_id == role_id
        ).first()
        if user_project_role:
            session.delete(user_project_role)
            session.commit()

def get_user_project_roles(user_id: str, project_id: str) -> List[Dict[str, Any]]:
    """Get all roles for a user in a specific project"""
    with LocalSession() as session:
        user_project_roles = session.query(UserProjectRoles).filter(
            UserProjectRoles.user_id == user_id,
            UserProjectRoles.project_id == project_id
        ).all()
        roles = []
        for user_project_role in user_project_roles:
            role = {
                "id": user_project_role.role.id,
                "name": user_project_role.role.name,
                "description": user_project_role.role.description,
                "permissions": user_project_role.role.permissions or [],
                "organization_id": user_project_role.role.organization_id,
                "created_at": user_project_role.role.created_at.isoformat(),
                "assigned_at": user_project_role.assigned_at,
                "assigned_by": user_project_role.assigned_by
            }
            roles.append(role)
        return roles

def get_user_permissions_in_project(user_id: str, project_id: str) -> List[str]:
    """Get all permissions for a user in a specific project"""
    roles = get_user_project_roles(user_id, project_id)
    permissions = set()
    for role in roles:
        permissions.update(role['permissions'])
    return list(permissions)

# Audit logging
def create_audit_log(
    user_id: Optional[str],
    organization_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[Dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Create an audit log entry"""
    with LocalSession() as session:
        log = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc)
        )
        session.add(log)
        session.commit()

def get_audit_logs(
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get audit logs with optional filters"""
    with LocalSession() as session:
        query = session.query(AuditLog)
        if organization_id:
            query = query.filter(AuditLog.organization_id == organization_id)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
        result = []
        for log in logs:
            details = log.details
            if isinstance(details, str):
                try:
                    details = json.loads(details)
                except Exception:
                    details = {}
            result.append({
                "id": log.id,
                "user_id": log.user_id,
                "organization_id": log.organization_id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": details or {},
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None
            })
        return result

# Session management
def create_user_session(
    session_id: str,
    user_id: str,
    refresh_token_jti: str,
    expires_at: datetime,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Create a user session record"""
    with LocalSession() as session:
        user_session = UserSession(
            id=session_id,
            user_id=user_id,
            refresh_token_jti=refresh_token_jti,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
            last_activity=datetime.now(timezone.utc)
        )
        session.add(user_session)
        session.commit()

def update_session_activity(session_id: str):
    """Update session last activity timestamp"""
    with LocalSession() as session:
        user_session = session.get(UserSession, session_id)
        if user_session:
            user_session.last_activity = datetime.now(timezone.utc)
            session.commit()

def delete_user_session(session_id: str):
    """Delete a user session"""
    with LocalSession() as session:
        user_session = session.get(UserSession, session_id)
        if user_session:
            session.delete(user_session)
            session.commit()

def cleanup_expired_sessions():
    """Remove expired sessions"""
    with LocalSession() as session:
        deleted = session.query(UserSession).filter(UserSession.expires_at < datetime.now(timezone.utc)).delete()
        session.commit()
        return deleted

def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    """Get all active sessions for a user"""
    with LocalSession() as session:
        sessions = (
            session.query(UserSession)
            .filter(UserSession.user_id == user_id, UserSession.expires_at > datetime.now(timezone.utc))
            .order_by(UserSession.last_activity.desc())
            .all()
        )
        return [{
            "id": s.id,
            "user_id": s.user_id,
            "refresh_token_jti": s.refresh_token_jti,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "last_activity": s.last_activity.isoformat() if s.last_activity else None
        } for s in sessions]

# Initialize default roles
def create_default_roles(organization_id: str):
    """Create default roles for a new organization"""
    import uuid
    
    default_roles = [
        {
            "name": "Super Admin",
            "permissions": ["*"],  # All permissions
            "description": "Full system access"
        },
        {
            "name": "Organization Admin", 
            "permissions": [
                "users.create", "users.read", "users.update", "users.delete",
                "projects.create", "projects.read", "projects.update", "projects.delete",
                "flows.create", "flows.read", "flows.update", "flows.delete", "flows.execute",
                "roles.create", "roles.read", "roles.update", "roles.delete",
                "audit.read"
            ],
            "description": "Organization management access"
        },
        {
            "name": "Project Admin",
            "permissions": [
                "projects.read", "projects.update",
                "flows.create", "flows.read", "flows.update", "flows.delete", "flows.execute",
                "users.read"
            ],
            "description": "Project management access"
        },
        {
            "name": "Developer",
            "permissions": [
                "flows.create", "flows.read", "flows.update", "flows.execute",
                "projects.read"
            ],
            "description": "Flow development access"
        },
        {
            "name": "User",
            "permissions": [
                "flows.read", "flows.execute",
                "projects.read"
            ],
            "description": "Basic user access"
        },
        {
            "name": "Viewer",
            "permissions": [
                "flows.read",
                "projects.read"
            ],
            "description": "Read-only access"
        }
    ]
    
    for role_data in default_roles:
        role_id = str(uuid.uuid4())
        create_role(
            role_id=role_id,
            name=role_data["name"],
            permissions=role_data["permissions"],
            organization_id=organization_id,
            description=role_data["description"]
        )