"""
Authentication routes for Agent-Builder
Handles OAuth flow, user registration, and session management
"""
import os
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, redirect, make_response, url_for, g
from urllib.parse import urlencode

from auth.keycloak_client import keycloak_client, KeycloakError
from auth.rbac import get_user_effective_permissions
from auth.security import (
    log_auth_attempt, is_account_locked, check_rate_limit,
    reset_failed_attempts, rate_limit
)
from middleware.auth import (
    create_access_token, create_refresh_token, revoke_token,
    require_auth, get_current_user_id
)
from database import (
    get_user_by_keycloak_id, create_user, get_organization,
    create_organization, create_default_roles, update_user_last_login,
    create_user_session, delete_user_session, cleanup_expired_sessions,
    create_audit_log
)

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/login', methods=['GET'])
@rate_limit(max_requests=5, window_seconds=300)  # 5 requests per 5 minutes
def login():
    """Initiate OAuth login flow"""
    try:
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state in session or cache (in production, use Redis)
        # For now, we'll pass it through and validate on callback
        
        # Get authorization URL from Keycloak
        auth_url = keycloak_client.get_authorization_url(state=state)
        
        return jsonify({
            'auth_url': auth_url,
            'state': state
        })
        
    except Exception as e:
        logger.error(f"Login initiation failed: {e}")
        return jsonify({
            'error': 'Login failed',
            'message': 'Unable to initiate login process'
        }), 500

@auth_bp.route('/callback', methods=['GET'])
def auth_callback():
    """Handle OAuth callback from Keycloak"""
    try:
        # Rate limiting check
        client_ip = request.remote_addr
        if not check_rate_limit(client_ip):
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=rate_limit_exceeded")
        
        # Get authorization code and state from callback
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        if error:
            logger.error(f"OAuth error: {error}")
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=oauth_error")
        
        if not code:
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=missing_code")
        
        # Exchange code for tokens
        token_data = keycloak_client.exchange_code_for_tokens(code)
        access_token = token_data['access_token']
        refresh_token = token_data['refresh_token']
        
        # Get user info from Keycloak
        user_info = keycloak_client.get_user_info(access_token)
        
        # Check if account is locked
        user_email = user_info.get('email', '')
        if is_account_locked(user_email):
            log_auth_attempt(user_email, False, client_ip, request.headers.get('User-Agent'))
            return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=account_locked")
        
        # Find or create user in our database
        user = get_user_by_keycloak_id(user_info['sub'])
        
        if not user:
            # New user - create organization and user
            user = _create_new_user_and_organization(user_info)
        
        # Update last login
        update_user_last_login(user['id'])
        
        # Get user's permissions and roles
        permissions = _get_user_permissions(user)
        
        # Create our JWT tokens
        user_data = {
            'user_id': user['id'],
            'email': user['email'],
            'organization_id': user['organization_id'],
            'permissions': permissions,
            'roles': _get_user_roles(user)
        }
        
        jwt_access_token = create_access_token(user_data)
        jwt_refresh_token = create_refresh_token(user['id'])
        
        # Create session record
        session_id = str(uuid.uuid4())
        create_user_session(
            session_id=session_id,
            user_id=user['id'],
            refresh_token_jti=_extract_jti_from_token(jwt_refresh_token),
            expires_at=datetime.now() + timedelta(days=30),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Log successful authentication
        log_auth_attempt(user_email, True, client_ip, request.headers.get('User-Agent'))
        reset_failed_attempts(user_email)  # Clear any previous failed attempts
        
        # Create audit log
        create_audit_log(
            user_id=user['id'],
            organization_id=user['organization_id'],
            action='login',
            resource_type='user',
            resource_id=user['id'],
            details={'method': 'oauth', 'provider': 'keycloak'},
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Set httpOnly cookies and redirect to frontend
        response = make_response(redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/dashboard"))
        
        # Set secure cookies
        cookie_secure = os.getenv('ENVIRONMENT', 'development') == 'production'
        response.set_cookie(
            'access_token',
            jwt_access_token,
            httponly=True,
            secure=cookie_secure,
            samesite='Lax',
            max_age=3600  # 1 hour
        )
        response.set_cookie(
            'refresh_token',
            jwt_refresh_token,
            httponly=True,
            secure=cookie_secure,
            samesite='Lax',
            max_age=30*24*3600  # 30 days
        )
        response.set_cookie(
            'session_id',
            session_id,
            httponly=True,
            secure=cookie_secure,
            samesite='Lax',
            max_age=30*24*3600  # 30 days
        )
        
        return response
        
    except KeycloakError as e:
        logger.error(f"Keycloak error during callback: {e}")
        # Log failed attempt if we have user email
        if 'user_email' in locals():
            log_auth_attempt(user_email, False, client_ip, request.headers.get('User-Agent'))
        return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=keycloak_error")
    except Exception as e:
        logger.error(f"Auth callback failed: {e}")
        # Log failed attempt if we have user email
        if 'user_email' in locals():
            log_auth_attempt(user_email, False, client_ip, request.headers.get('User-Agent'))
        return redirect(f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/login?error=internal_error")

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """Logout user and revoke tokens"""
    try:
        user_id = get_current_user_id()
        organization_id = getattr(g, 'organization_id', None)
        
        # Get refresh token from cookies
        refresh_token = request.cookies.get('refresh_token')
        session_id = request.cookies.get('session_id')
        
        # Revoke tokens in Keycloak if refresh token exists
        if refresh_token:
            try:
                keycloak_client.logout_user(refresh_token)
            except Exception as e:
                logger.warning(f"Keycloak logout failed: {e}")
        
        # Revoke our JWT tokens
        if refresh_token:
            jti = _extract_jti_from_token(refresh_token)
            if jti:
                revoke_token(jti)
        
        # Delete session
        if session_id:
            delete_user_session(session_id)
        
        # Create audit log
        create_audit_log(
            user_id=user_id,
            organization_id=organization_id,
            action='logout',
            resource_type='user',
            resource_id=user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Clear cookies
        response = make_response(jsonify({'message': 'Logged out successfully'}))
        response.set_cookie('access_token', '', expires=0, httponly=True)
        response.set_cookie('refresh_token', '', expires=0, httponly=True)
        response.set_cookie('session_id', '', expires=0, httponly=True)
        
        return response
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return jsonify({'error': 'Logout failed'}), 500

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        refresh_token = request.cookies.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'error': 'Refresh token not found'}), 401
        
        # Here you would validate the refresh token and create a new access token
        # This is a simplified implementation
        
        # In a real implementation, you'd:
        # 1. Validate the refresh token
        # 2. Get user data
        # 3. Create new access token
        # 4. Update session
        
        return jsonify({'message': 'Token refresh not yet implemented'}), 501
        
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        return jsonify({'error': 'Token refresh failed'}), 500

@auth_bp.route('/user', methods=['GET'])
@require_auth
def get_current_user():
    """Get current user information"""
    try:
        user_id = get_current_user_id()
        organization_id = getattr(g, 'organization_id', None)
        
        # Handle dev user without database lookup
        if user_id == 'dev-user-123':
            user_data = {
                'id': 'dev-user-123',
                'email': 'dev@agent-builder.local',
                'username': 'devuser',
                'first_name': 'Dev', 
                'last_name': 'User',
                'organization': {'id': 'dev-org-123', 'name': 'Development Org'},
                'permissions': {
                    'organization_permissions': ['*'],
                    'project_permissions': ['*'],
                    'effective_permissions': ['*'],
                    'expanded_permissions': ['*'],
                    'is_admin': True,
                    'is_super_admin': True
                },
                'last_login': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }
            return jsonify(user_data)
        
        # Get user from database for real users
        from database import get_user
        user = get_user(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get organization info
        organization = get_organization(organization_id) if organization_id else None
        
        # Get effective permissions
        permissions_info = get_user_effective_permissions(user_id)
        
        # Remove sensitive information
        user_data = {
            'id': user['id'],
            'email': user['email'],
            'username': user['username'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'organization': organization,
            'permissions': permissions_info,
            'last_login': user['last_login'],
            'created_at': user['created_at']
        }
        
        return jsonify(user_data)
        
    except Exception as e:
        logger.error(f"Get current user failed: {e}")
        return jsonify({'error': 'Failed to get user information'}), 500

@auth_bp.route('/dev-login', methods=['POST'])
@rate_limit(max_requests=3, window_seconds=60)  # 3 attempts per minute
def dev_login():
    """Development-only login bypass"""
    if os.getenv('ENVIRONMENT', 'development') != 'development':
        return jsonify({'error': 'Development login not available in production'}), 403
    
    try:
        # Create a fake user session for development
        user_data = {
            'id': 'dev-user-123',
            'email': 'dev@agent-builder.local',
            'username': 'devuser',
            'first_name': 'Dev',
            'last_name': 'User',
            'organization_id': 'dev-org-123',
            'last_login': datetime.now().isoformat(),
            'created_at': datetime.now().isoformat()
        }
        
        permissions_info = {
            'organization_permissions': ['*'],
            'project_permissions': ['*'],
            'effective_permissions': ['*'],
            'expanded_permissions': ['*'],
            'is_admin': True,
            'is_super_admin': True
        }
        
        # Create JWT tokens without database operations
        jwt_user_data = {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'organization_id': user_data['organization_id'],
            'permissions': ['*'],  # Simple list for dev user with all permissions
            'roles': ['admin']
        }
        
        jwt_access_token = create_access_token(jwt_user_data)
        
        # Set cookie and return user data
        response = make_response(jsonify({
            'user': user_data,
            'organization': {'id': 'dev-org-123', 'name': 'Development Org'},
            'permissions': permissions_info
        }))
        
        response.set_cookie(
            'access_token',
            jwt_access_token,
            httponly=True,
            secure=False,  # Development only
            samesite='Lax',
            max_age=3600
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Dev login failed: {e}")
        return jsonify({'error': 'Development login failed'}), 500

@auth_bp.route('/health', methods=['GET'])
def auth_health():
    """Check authentication service health"""
    try:
        # Check Keycloak connectivity
        keycloak_healthy = keycloak_client.health_check()
        
        # Clean up expired sessions
        cleanup_expired_sessions()
        
        return jsonify({
            'status': 'healthy',
            'keycloak_available': keycloak_healthy,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Auth health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

# Helper functions
def _create_new_user_and_organization(user_info: dict) -> dict:
    """Create new user and organization for first-time login"""
    try:
        # Create organization (use email domain as default org name)
        email_domain = user_info['email'].split('@')[1]
        org_name = f"{email_domain.title()} Organization"
        org_id = str(uuid.uuid4())
        
        organization = create_organization(
            org_id=org_id,
            name=org_name,
            description=f"Auto-created organization for {email_domain}",
            settings={'auto_created': True}
        )
        
        # Create default roles for organization
        create_default_roles(org_id)
        
        # Create user
        user_id = str(uuid.uuid4())
        user = create_user(
            user_id=user_id,
            keycloak_id=user_info['sub'],
            email=user_info['email'],
            username=user_info.get('preferred_username', user_info['email']),
            organization_id=org_id,
            first_name=user_info.get('given_name', ''),
            last_name=user_info.get('family_name', '')
        )
        
        # Assign user as organization admin (first user in org)
        from database import list_roles_in_organization, assign_user_project_role
        roles = list_roles_in_organization(org_id)
        admin_role = next((r for r in roles if r['name'] == 'Organization Admin'), None)
        
        if admin_role:
            # For organization-level roles, we'll use a special project_id
            assign_user_project_role(user_id, f"org:{org_id}", admin_role['id'])
        
        logger.info(f"Created new user {user_id} and organization {org_id}")
        return user
        
    except Exception as e:
        logger.error(f"Failed to create new user and organization: {e}")
        raise

def _get_user_permissions(user: dict) -> list:
    """Get user's base permissions"""
    # This would typically query the user's roles and aggregate permissions
    # For now, return basic permissions - this should be expanded
    return ["flows.read", "flows.execute", "projects.read"]

def _get_user_roles(user: dict) -> list:
    """Get user's roles"""
    # This would query user's roles across projects
    # For now, return empty list - this should be expanded
    return []

def _extract_jti_from_token(token: str) -> str:
    """Extract JWT ID from token without full validation"""
    try:
        import jwt
        # Decode without verification to get JTI
        unverified = jwt.decode(token, options={"verify_signature": False})
        return unverified.get('jti')
    except Exception:
        return None