"""
Role-Based Access Control (RBAC) utilities for Agent-Builder
Provides advanced permission checking and role management
"""
import logging
from typing import List, Dict, Any, Optional, Set
from functools import wraps
from flask import request, jsonify, g

from database import (
    get_user_permissions_in_project,
    get_user_project_roles,
    create_audit_log
)

logger = logging.getLogger(__name__)

class PermissionError(Exception):
    """Permission denied error"""
    def __init__(self, message: str, required_permission: str = None):
        self.message = message
        self.required_permission = required_permission
        super().__init__(self.message)

class RBACManager:
    """Advanced RBAC management"""
    
    # Define permission hierarchy (parent permissions include child permissions)
    PERMISSION_HIERARCHY = {
        "*": "all",  # Super admin permission
        "admin": [  # Organization admin permissions
            "users.*", "projects.*", "flows.*", "roles.*", "audit.*"
        ],
        "users.*": ["users.create", "users.read", "users.update", "users.delete"],
        "projects.*": ["projects.create", "projects.read", "projects.update", "projects.delete"],
        "flows.*": ["flows.create", "flows.read", "flows.update", "flows.delete", "flows.execute"],
        "roles.*": ["roles.create", "roles.read", "roles.update", "roles.delete"],
        "audit.*": ["audit.read", "audit.export"]
    }
    
    # Resource-specific permissions
    RESOURCE_PERMISSIONS = {
        "flows": ["create", "read", "update", "delete", "execute", "share"],
        "projects": ["create", "read", "update", "delete", "manage_users"],
        "users": ["create", "read", "update", "delete", "invite"],
        "roles": ["create", "read", "update", "delete", "assign"],
        "audit": ["read", "export"],
        "organizations": ["read", "update", "delete"]
    }
    
    @classmethod
    def expand_permissions(cls, permissions: List[str]) -> Set[str]:
        """Expand wildcard and hierarchical permissions"""
        expanded = set()
        
        for permission in permissions:
            if permission == "*":
                # Super admin gets all permissions
                for resource, actions in cls.RESOURCE_PERMISSIONS.items():
                    for action in actions:
                        expanded.add(f"{resource}.{action}")
                expanded.add("*")
            elif permission in cls.PERMISSION_HIERARCHY:
                if isinstance(cls.PERMISSION_HIERARCHY[permission], list):
                    expanded.update(cls.PERMISSION_HIERARCHY[permission])
                expanded.add(permission)
            else:
                expanded.add(permission)
        
        return expanded
    
    @classmethod
    def check_permission(cls, user_permissions: List[str], required_permission: str) -> bool:
        """Check if user has the required permission"""
        expanded_permissions = cls.expand_permissions(user_permissions)
        
        # Check for exact match
        if required_permission in expanded_permissions:
            return True
        
        # Check for wildcard permissions
        if "*" in expanded_permissions:
            return True
        
        # Check for resource-level permissions (e.g., flows.* covers flows.execute)
        resource = required_permission.split('.')[0]
        if f"{resource}.*" in expanded_permissions:
            return True
        
        return False
    
    @classmethod
    def get_user_context_permissions(cls, user_id: str, project_id: str = None) -> List[str]:
        """Get user's permissions in current context"""
        if not project_id:
            # For now, return basic permissions if no project context
            return getattr(g, 'permissions', [])
        
        # Get project-specific permissions
        return get_user_permissions_in_project(user_id, project_id)
    
    @classmethod
    def audit_permission_check(cls, user_id: str, organization_id: str, permission: str, granted: bool, resource_id: str = None):
        """Log permission check for audit purposes"""
        try:
            create_audit_log(
                user_id=user_id,
                organization_id=organization_id,
                action="permission_check",
                resource_type="permission",
                resource_id=resource_id,
                details={
                    "permission": permission,
                    "granted": granted,
                    "ip_address": request.remote_addr,
                    "user_agent": request.headers.get('User-Agent')
                },
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent')
            )
        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

def require_permission(permission: str, resource_id_param: str = None, audit: bool = True):
    """
    Enhanced decorator to require specific permission for a route
    
    Args:
        permission: Required permission (e.g., 'flows.execute')
        resource_id_param: Name of parameter containing resource ID for context
        audit: Whether to log permission checks
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get current user context
            user_id = getattr(g, 'user_id', None)
            organization_id = getattr(g, 'organization_id', None)
            
            if not user_id:
                if audit:
                    RBACManager.audit_permission_check(
                        user_id=None,
                        organization_id=organization_id,
                        permission=permission,
                        granted=False
                    )
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'User not authenticated'
                }), 401
            
            # Get resource ID if specified
            resource_id = None
            if resource_id_param:
                resource_id = (
                    kwargs.get(resource_id_param) or
                    request.json.get(resource_id_param) if request.json else None or
                    request.args.get(resource_id_param)
                )
            
            # Get user permissions (project-specific if resource is project-scoped)
            project_id = None
            if permission.startswith(('flows.', 'projects.')):
                # Try to determine project context
                project_id = (
                    kwargs.get('project_id') or
                    request.json.get('project_id') if request.json else None or
                    request.args.get('project_id')
                )
            
            if project_id:
                user_permissions = RBACManager.get_user_context_permissions(user_id, project_id)
            else:
                user_permissions = getattr(g, 'permissions', [])
            
            # Check permission
            has_permission = RBACManager.check_permission(user_permissions, permission)
            
            # Audit the permission check
            if audit:
                RBACManager.audit_permission_check(
                    user_id=user_id,
                    organization_id=organization_id,
                    permission=permission,
                    granted=has_permission,
                    resource_id=resource_id
                )
            
            if not has_permission:
                logger.warning(f"Permission denied for user {user_id}: required '{permission}', have {user_permissions}")
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Permission "{permission}" required',
                    'required_permission': permission,
                    'user_permissions': user_permissions
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_organization_admin(f):
    """Decorator to require organization admin permissions"""
    @wraps(f)
    @require_permission("admin", audit=True)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated_function

def require_project_access(project_id_param: str = 'project_id'):
    """Decorator to ensure user has access to specified project"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = getattr(g, 'user_id', None)
            organization_id = getattr(g, 'organization_id', None)
            
            if not user_id:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Get project ID
            project_id = (
                kwargs.get(project_id_param) or
                request.json.get(project_id_param) if request.json else None or
                request.args.get(project_id_param)
            )
            
            if not project_id:
                return jsonify({
                    'error': 'Project ID required',
                    'message': f'Parameter "{project_id_param}" is required'
                }), 400
            
            # Check if user has any roles in this project
            user_roles = get_user_project_roles(user_id, project_id)
            
            if not user_roles:
                # Check if user is organization admin
                user_permissions = getattr(g, 'permissions', [])
                if not RBACManager.check_permission(user_permissions, "admin"):
                    return jsonify({
                        'error': 'Access denied',
                        'message': 'You do not have access to this project'
                    }), 403
            
            # Add project context to request
            g.project_id = project_id
            g.project_roles = user_roles
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_user_effective_permissions(user_id: str, project_id: str = None) -> Dict[str, Any]:
    """Get user's effective permissions with context"""
    base_permissions = getattr(g, 'permissions', [])
    
    result = {
        'user_id': user_id,
        'organization_permissions': base_permissions,
        'project_permissions': [],
        'effective_permissions': base_permissions,
        'is_admin': RBACManager.check_permission(base_permissions, "admin"),
        'is_super_admin': "*" in base_permissions
    }
    
    if project_id:
        project_permissions = get_user_permissions_in_project(user_id, project_id)
        result['project_permissions'] = project_permissions
        
        # Combine organization and project permissions
        combined_permissions = list(set(base_permissions + project_permissions))
        result['effective_permissions'] = combined_permissions
    
    # Expand permissions for UI
    expanded = RBACManager.expand_permissions(result['effective_permissions'])
    result['expanded_permissions'] = list(expanded)
    
    return result

def validate_permission_list(permissions: List[str]) -> Dict[str, Any]:
    """Validate a list of permissions"""
    valid_permissions = set()
    invalid_permissions = []
    
    # Get all valid permissions from resource definitions
    for resource, actions in RBACManager.RESOURCE_PERMISSIONS.items():
        for action in actions:
            valid_permissions.add(f"{resource}.{action}")
        valid_permissions.add(f"{resource}.*")
    
    # Add special permissions
    valid_permissions.update(["*", "admin"])
    
    for permission in permissions:
        if permission not in valid_permissions and not permission.endswith('.*'):
            invalid_permissions.append(permission)
    
    return {
        'valid': len(invalid_permissions) == 0,
        'invalid_permissions': invalid_permissions,
        'valid_permissions': list(valid_permissions)
    }

# Utility functions for checking specific permissions
def can_user_execute_flows(user_id: str, project_id: str = None) -> bool:
    """Check if user can execute flows"""
    if project_id:
        permissions = get_user_permissions_in_project(user_id, project_id)
    else:
        permissions = getattr(g, 'permissions', [])
    
    return RBACManager.check_permission(permissions, "flows.execute")

def can_user_manage_users(user_id: str) -> bool:
    """Check if user can manage users"""
    permissions = getattr(g, 'permissions', [])
    return RBACManager.check_permission(permissions, "users.create")

def can_user_view_audit_logs(user_id: str) -> bool:
    """Check if user can view audit logs"""
    permissions = getattr(g, 'permissions', [])
    return RBACManager.check_permission(permissions, "audit.read")