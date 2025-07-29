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
-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Flows table
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

-- Flow execution history
CREATE TABLE IF NOT EXISTS flow_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'running', 'completed', 'failed'
    input_data TEXT,       -- JSON
    output_data TEXT,      -- JSON
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (flow_id) REFERENCES flows(id) ON DELETE CASCADE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_flows_project_id ON flows(project_id);
CREATE INDEX IF NOT EXISTS idx_flow_executions_flow_id ON flow_executions(flow_id);
CREATE INDEX IF NOT EXISTS idx_flow_executions_status ON flow_executions(status);
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
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info(f"Database initialized at {DB_PATH}")

# Project management
def create_project(project_id: str, name: str, description: str = "") -> Dict[str, Any]:
    """Create a new project"""
    with get_db() as conn:
        cursor = conn.cursor()
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

# Initialize database on import
init_database()