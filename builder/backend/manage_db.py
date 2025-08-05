#!/usr/bin/env python
"""
Database management script for Agent-Builder
Handles migrations and database initialization
"""
import os
import sys
import argparse
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Base
from database import (
    engine, LocalSession,
    create_organization, create_default_roles,
    create_user, create_project, create_role
)

def get_alembic_config():
    """Get Alembic configuration"""
    alembic_cfg = Config("alembic.ini")
    return alembic_cfg

def init_db():
    """Initialize database with default data"""
    print("Initializing database...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create default organization
    try:
        org = create_organization(
            org_id="default_org",
            name="Default Organization",
            description="Default organization for standalone deployment"
        )
        print(f"Created organization: {org['name']}")
        
        # Create default roles
        create_default_roles("default_org")
        print("Created default roles")
        
        # Create system user
        user = create_user(
            user_id="system",
            keycloak_id="system",
            email="system@local",
            username="system",
            organization_id="default_org",
            first_name="System",
            last_name="User"
        )
        print(f"Created system user: {user['username']}")
        
        # Create default project
        project = create_project(
            project_id="default_project",
            name="Default Project",
            description="Default project for getting started",
            organization_id="default_org",
            owner_id="system"
        )
        print(f"Created default project: {project['name']}")
        
    except Exception as e:
        print(f"Warning: Some default data may already exist: {e}")
    
    print("Database initialization complete!")

def create_migration(message):
    """Create a new migration"""
    alembic_cfg = get_alembic_config()
    command.revision(alembic_cfg, message=message, autogenerate=True)
    print(f"Created migration: {message}")

def upgrade_db(revision="head"):
    """Upgrade database to a revision"""
    alembic_cfg = get_alembic_config()
    command.upgrade(alembic_cfg, revision)
    print(f"Upgraded database to: {revision}")

def downgrade_db(revision):
    """Downgrade database to a revision"""
    alembic_cfg = get_alembic_config()
    command.downgrade(alembic_cfg, revision)
    print(f"Downgraded database to: {revision}")

def current_revision():
    """Show current revision"""
    alembic_cfg = get_alembic_config()
    command.current(alembic_cfg)

def migration_history():
    """Show migration history"""
    alembic_cfg = get_alembic_config()
    command.history(alembic_cfg)

def main():
    parser = argparse.ArgumentParser(description="Agent-Builder Database Management")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Init command
    subparsers.add_parser("init", help="Initialize database with default data")
    
    # Create migration
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument("--revision", default="head", help="Target revision (default: head)")
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", help="Target revision")
    
    # Current revision
    subparsers.add_parser("current", help="Show current revision")
    
    # History
    subparsers.add_parser("history", help="Show migration history")
    
    args = parser.parse_args()
    
    if args.command == "init":
        init_db()
    elif args.command == "create":
        create_migration(args.message)
    elif args.command == "upgrade":
        upgrade_db(args.revision)
    elif args.command == "downgrade":
        downgrade_db(args.revision)
    elif args.command == "current":
        current_revision()
    elif args.command == "history":
        migration_history()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()