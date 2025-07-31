"""
Database models and utilities for Agent-Builder
Provides SQLite storage for flows and projects
"""
import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger("Database")

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "agent_builder.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# SQL Schema
CREATE_TABLES_SQL = """
-- Organizations table
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    settings TEXT,        -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    keycloak_id TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    first_name TEXT,
    last_name TEXT,
    organization_id TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    permissions TEXT NOT NULL,  -- JSON array of permissions
    organization_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    UNIQUE(name, organization_id)
);

-- User project roles (many-to-many relationship)
CREATE TABLE IF NOT EXISTS user_project_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(id),
    UNIQUE(user_id, project_id, role_id)
);

-- Projects table (updated with organization reference)
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    organization_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (owner_id) REFERENCES users(id)
);

-- Flows table (unchanged but will inherit organization isolation through projects)
CREATE TABLE IF NOT EXISTS flows (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    nodes TEXT NOT NULL,  -- JSON
    edges TEXT NOT NULL,  -- JSON
    metadata TEXT,        -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Flow execution history (updated with user tracking)
CREATE TABLE IF NOT EXISTS flow_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id TEXT NOT NULL,
    user_id TEXT,
    status TEXT NOT NULL,  -- 'running', 'completed', 'failed'
    input_data TEXT,       -- JSON
    output_data TEXT,      -- JSON
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (flow_id) REFERENCES flows(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    organization_id TEXT,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details TEXT,          -- JSON
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
);

-- User sessions table (for tracking active sessions)
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    refresh_token_jti TEXT UNIQUE,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create indexes
-- Original indexes
CREATE INDEX IF NOT EXISTS idx_flows_project_id ON flows(project_id);
CREATE INDEX IF NOT EXISTS idx_flow_executions_flow_id ON flow_executions(flow_id);
CREATE INDEX IF NOT EXISTS idx_flow_executions_status ON flow_executions(status);

-- New indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_keycloak_id ON users(keycloak_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_organization_id ON projects(organization_id);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);
CREATE INDEX IF NOT EXISTS idx_user_project_roles_user_id ON user_project_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_project_roles_project_id ON user_project_roles(project_id);
CREATE INDEX IF NOT EXISTS idx_roles_organization_id ON roles(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs(organization_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);
"""

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize the database with required tables"""
    with get_db() as conn:
        # Check if we have old schema and need migration
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
        existing_projects_table = cursor.fetchone()
        
        if existing_projects_table:
            # Check if projects table has organization_id column
            cursor.execute("PRAGMA table_info(projects)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'organization_id' not in columns:
                logger.info("Migrating from old schema to enterprise schema...")
                # Drop and recreate tables for enterprise schema
                cursor.execute("DROP TABLE IF EXISTS flow_executions")
                cursor.execute("DROP TABLE IF EXISTS flows")
                cursor.execute("DROP TABLE IF EXISTS projects")
                conn.commit()
        
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")

# Project management
def create_project(project_id: str, name: str, description: str = "", organization_id: str = "default_org", owner_id: str = "system") -> Dict[str, Any]:
    """Create a new project - backward compatible with old schema"""
    with get_db() as conn:
        cursor = conn.cursor()
        # Check if we have new schema with organization_id
        cursor.execute("PRAGMA table_info(projects)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'organization_id' in columns:
            # New enterprise schema
            cursor.execute(
                "INSERT INTO projects (id, name, description, organization_id, owner_id) VALUES (?, ?, ?, ?, ?)",
                (project_id, name, description, organization_id, owner_id)
            )
        else:
            # Old schema fallback
            cursor.execute(
                "INSERT INTO projects (id, name, description) VALUES (?, ?, ?)",
                (project_id, name, description)
            )
        
        conn.commit()
        return {
            "id": project_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat()
        }

def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Get a project by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def list_projects() -> List[Dict[str, Any]]:
    """List all projects"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        return [dict(row) for row in cursor.fetchall()]

# Flow management
def save_flow(
    flow_id: str,
    project_id: str,
    name: str,
    nodes: List[Dict],
    edges: List[Dict],
    description: str = "",
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """Save or update a flow"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if flow exists
        cursor.execute("SELECT id FROM flows WHERE id = ?", (flow_id,))
        exists = cursor.fetchone() is not None
        
        if exists:
            # Update existing flow
            cursor.execute("""
                UPDATE flows 
                SET name = ?, description = ?, nodes = ?, edges = ?, 
                    metadata = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                name, description, 
                json.dumps(nodes), json.dumps(edges),
                json.dumps(metadata or {}),
                flow_id
            ))
        else:
            # Create new flow
            cursor.execute("""
                INSERT INTO flows (id, project_id, name, description, nodes, edges, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                flow_id, project_id, name, description,
                json.dumps(nodes), json.dumps(edges),
                json.dumps(metadata or {})
            ))
        
        conn.commit()
        
        return {
            "id": flow_id,
            "project_id": project_id,
            "name": name,
            "description": description,
            "nodes": nodes,
            "edges": edges,
            "metadata": metadata,
            "updated_at": datetime.now().isoformat()
        }

def get_flow(flow_id: str) -> Optional[Dict[str, Any]]:
    """Get a flow by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM flows WHERE id = ?", (flow_id,))
        row = cursor.fetchone()
        if row:
            flow = dict(row)
            flow['nodes'] = json.loads(flow['nodes'])
            flow['edges'] = json.loads(flow['edges'])
            flow['metadata'] = json.loads(flow['metadata'] or '{}')
            return flow
        return None

def list_flows(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List flows, optionally filtered by project"""
    with get_db() as conn:
        cursor = conn.cursor()
        if project_id:
            cursor.execute(
                "SELECT * FROM flows WHERE project_id = ? ORDER BY updated_at DESC",
                (project_id,)
            )
        else:
            cursor.execute("SELECT * FROM flows ORDER BY updated_at DESC")
        
        flows = []
        for row in cursor.fetchall():
            flow = dict(row)
            flow['nodes'] = json.loads(flow['nodes'])
            flow['edges'] = json.loads(flow['edges'])
            flow['metadata'] = json.loads(flow['metadata'] or '{}')
            flows.append(flow)
        
        return flows

def delete_flow(flow_id: str) -> bool:
    """Delete a flow"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM flows WHERE id = ?", (flow_id,))
        conn.commit()
        return cursor.rowcount > 0

# Flow execution tracking
def create_flow_execution(
    flow_id: str,
    input_data: Optional[Dict] = None
) -> int:
    """Create a new flow execution record"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO flow_executions (flow_id, status, input_data)
            VALUES (?, 'running', ?)
        """, (flow_id, json.dumps(input_data or {})))
        conn.commit()
        return cursor.lastrowid

def update_flow_execution(
    execution_id: int,
    status: str,
    output_data: Optional[Dict] = None,
    error_message: Optional[str] = None
):
    """Update flow execution status"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE flow_executions
            SET status = ?, output_data = ?, error_message = ?, 
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            status,
            json.dumps(output_data) if output_data else None,
            error_message,
            execution_id
        ))
        conn.commit()

def get_flow_executions(flow_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent executions for a flow"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM flow_executions 
            WHERE flow_id = ? 
            ORDER BY started_at DESC 
            LIMIT ?
        """, (flow_id, limit))
        
        executions = []
        for row in cursor.fetchall():
            execution = dict(row)
            execution['input_data'] = json.loads(execution['input_data'] or '{}')
            execution['output_data'] = json.loads(execution['output_data'] or '{}')
            executions.append(execution)
        
        return executions

# Organization management
def create_organization(org_id: str, name: str, description: str = "", settings: Optional[Dict] = None) -> Dict[str, Any]:
    """Create a new organization"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO organizations (id, name, description, settings) VALUES (?, ?, ?, ?)",
            (org_id, name, description, json.dumps(settings or {}))
        )
        conn.commit()
        return {
            "id": org_id,
            "name": name,
            "description": description,
            "settings": settings or {},
            "created_at": datetime.now().isoformat()
        }

def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
    """Get organization by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
        row = cursor.fetchone()
        if row:
            org = dict(row)
            org['settings'] = json.loads(org['settings'] or '{}')
            return org
        return None

def list_organizations() -> List[Dict[str, Any]]:
    """List all organizations"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM organizations ORDER BY name")
        orgs = []
        for row in cursor.fetchall():
            org = dict(row)
            org['settings'] = json.loads(org['settings'] or '{}')
            orgs.append(org)
        return orgs

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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (id, keycloak_id, email, username, organization_id, first_name, last_name)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, keycloak_id, email, username, organization_id, first_name, last_name))
        conn.commit()
        return {
            "id": user_id,
            "keycloak_id": keycloak_id,
            "email": email,
            "username": username,
            "organization_id": organization_id,
            "first_name": first_name,
            "last_name": last_name,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_keycloak_id(keycloak_id: str) -> Optional[Dict[str, Any]]:
    """Get user by Keycloak ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE keycloak_id = ?", (keycloak_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_user_last_login(user_id: str):
    """Update user's last login timestamp"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
            (user_id,)
        )
        conn.commit()

def list_users_in_organization(org_id: str) -> List[Dict[str, Any]]:
    """List all users in an organization"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE organization_id = ? ORDER BY email",
            (org_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

# Role management
def create_role(role_id: str, name: str, permissions: List[str], organization_id: str, description: str = "") -> Dict[str, Any]:
    """Create a new role"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO roles (id, name, description, permissions, organization_id)
            VALUES (?, ?, ?, ?, ?)
        """, (role_id, name, description, json.dumps(permissions), organization_id))
        conn.commit()
        return {
            "id": role_id,
            "name": name,
            "description": description,
            "permissions": permissions,
            "organization_id": organization_id,
            "created_at": datetime.now().isoformat()
        }

def get_role(role_id: str) -> Optional[Dict[str, Any]]:
    """Get role by ID"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM roles WHERE id = ?", (role_id,))
        row = cursor.fetchone()
        if row:
            role = dict(row)
            role['permissions'] = json.loads(role['permissions'])
            return role
        return None

def list_roles_in_organization(org_id: str) -> List[Dict[str, Any]]:
    """List all roles in an organization"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM roles WHERE organization_id = ? ORDER BY name",
            (org_id,)
        )
        roles = []
        for row in cursor.fetchall():
            role = dict(row)
            role['permissions'] = json.loads(role['permissions'])
            roles.append(role)
        return roles

# User project role assignments
def assign_user_project_role(user_id: str, project_id: str, role_id: str, assigned_by: str = None):
    """Assign a role to a user for a specific project"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_project_roles (user_id, project_id, role_id, assigned_by)
            VALUES (?, ?, ?, ?)
        """, (user_id, project_id, role_id, assigned_by))
        conn.commit()

def remove_user_project_role(user_id: str, project_id: str, role_id: str):
    """Remove a role from a user for a specific project"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_project_roles WHERE user_id = ? AND project_id = ? AND role_id = ?",
            (user_id, project_id, role_id)
        )
        conn.commit()

def get_user_project_roles(user_id: str, project_id: str) -> List[Dict[str, Any]]:
    """Get all roles for a user in a specific project"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, upr.assigned_at, upr.assigned_by
            FROM roles r
            JOIN user_project_roles upr ON r.id = upr.role_id
            WHERE upr.user_id = ? AND upr.project_id = ?
        """, (user_id, project_id))
        
        roles = []
        for row in cursor.fetchall():
            role = dict(row)
            role['permissions'] = json.loads(role['permissions'])
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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (user_id, organization_id, action, resource_type, resource_id, details, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, organization_id, action, resource_type, resource_id,
            json.dumps(details or {}), ip_address, user_agent
        ))
        conn.commit()

def get_audit_logs(
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Get audit logs with optional filters"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        conditions = []
        params = []
        
        if organization_id:
            conditions.append("organization_id = ?")
            params.append(organization_id)
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.append(limit)
        
        cursor.execute(f"""
            SELECT * FROM audit_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ?
        """, params)
        
        logs = []
        for row in cursor.fetchall():
            log = dict(row)
            log['details'] = json.loads(log['details'] or '{}')
            logs.append(log)
        
        return logs

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
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_sessions (id, user_id, refresh_token_jti, ip_address, user_agent, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, user_id, refresh_token_jti, ip_address, user_agent, expires_at))
        conn.commit()

def update_session_activity(session_id: str):
    """Update session last activity timestamp"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE user_sessions SET last_activity = CURRENT_TIMESTAMP WHERE id = ?",
            (session_id,)
        )
        conn.commit()

def delete_user_session(session_id: str):
    """Delete a user session"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE id = ?", (session_id,))
        conn.commit()

def cleanup_expired_sessions():
    """Remove expired sessions"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP")
        conn.commit()
        return cursor.rowcount

def get_user_sessions(user_id: str) -> List[Dict[str, Any]]:
    """Get all active sessions for a user"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM user_sessions WHERE user_id = ? AND expires_at > CURRENT_TIMESTAMP ORDER BY last_activity DESC",
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]

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

# Initialize database on import
init_database()