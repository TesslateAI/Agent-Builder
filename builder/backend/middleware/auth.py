"""
JWT Authentication Middleware for Agent-Builder
Handles JWT token validation, user context, and permission checks
"""
import os
import jwt
import logging
import redis
from functools import wraps
from flask import request, jsonify, g, current_app
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Redis connection for session management
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)

class AuthError(Exception):
    """Custom authentication error"""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class JWTMiddleware:
    """JWT Authentication middleware for Flask"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the middleware with Flask app"""
        app.config.setdefault('JWT_SECRET_KEY', os.getenv('JWT_SECRET_KEY', 'dev-secret-key'))
        app.config.setdefault('JWT_ALGORITHM', 'HS256')
        app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))
        app.config.setdefault('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
        
        # Register error handlers
        app.errorhandler(AuthError)(self._handle_auth_error)
        
        # Add before_request handler for automatic token validation
        app.before_request(self._before_request)
    
    def _handle_auth_error(self, error):
        """Handle authentication errors"""
        return jsonify({
            'error': 'Authentication failed',
            'message': error.message
        }), error.status_code
    
    def _before_request(self):
        """Validate JWT token before each request (if present)"""
        # Skip authentication for certain endpoints
        if self._should_skip_auth():
            return
        
        token = self._extract_token()
        if token:
            try:
                payload = self._decode_token(token)
                g.current_user = payload
                g.user_id = payload.get('sub')
                g.organization_id = payload.get('organization_id')
                g.permissions = payload.get('permissions', [])
                logger.debug(f"User context set: user_id={g.user_id}, permissions={g.permissions}")
            except AuthError:
                # Let individual routes handle authentication as needed
                pass
    
    def _should_skip_auth(self) -> bool:
        """Check if authentication should be skipped for this endpoint"""
        skip_endpoints = [
            '/health',
            '/api/auth/login',
            '/api/auth/callback',
            '/api/auth/refresh',
            '/'  # Frontend routes
        ]
        
        # Skip static files and frontend routes
        if (request.endpoint == 'static' or 
            request.path.startswith('/static/') or
            not request.path.startswith('/api/')):
            return True
        
        return request.path in skip_endpoints
    
    def _extract_token(self) -> Optional[str]:
        """Extract JWT token from request headers or cookies"""
        # Try Authorization header first
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        
        # Try cookies (for httpOnly cookie storage)
        return request.cookies.get('access_token')
    
    def _decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=[current_app.config['JWT_ALGORITHM']]
            )
            
            # Check if token is expired
            if payload.get('exp', 0) < datetime.utcnow().timestamp():
                raise AuthError('Token has expired')
            
            # Check if token is revoked (using Redis blacklist)
            jti = payload.get('jti')  # JWT ID
            if jti and redis_client.get(f"revoked_token:{jti}"):
                raise AuthError('Token has been revoked')
            
            return payload
            
        except jwt.ExpiredSignatureError:
            raise AuthError('Token has expired')
        except jwt.InvalidTokenError:
            raise AuthError('Invalid token')
        except Exception as e:
            logger.error(f"Token decode error: {e}")
            raise AuthError('Token validation failed')

def require_auth(f):
    """Decorator to require authentication for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user') or not g.current_user:
            token = request.headers.get('Authorization') or request.cookies.get('access_token')
            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'No authentication token provided'
                }), 401
            
            # If we have a token but no user context, try to decode it
            try:
                if token.startswith('Bearer '):
                    token = token.split(' ')[1]
                
                middleware = JWTMiddleware()
                payload = middleware._decode_token(token)
                g.current_user = payload
                g.user_id = payload.get('sub')
                g.organization_id = payload.get('organization_id')
                g.permissions = payload.get('permissions', [])
                logger.debug(f"Require auth: user_id={g.user_id}, permissions={g.permissions}")
                
            except AuthError as e:
                return jsonify({
                    'error': 'Authentication failed',
                    'message': e.message
                }), e.status_code
        
        return f(*args, **kwargs)
    return decorated_function

def require_permission(permission: str):
    """Decorator to require specific permission for a route"""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user_permissions = getattr(g, 'permissions', [])
            
            # Check for admin permission (grants all access)
            if '*' in user_permissions or 'admin' in user_permissions:
                return f(*args, **kwargs)
            
            # Check for specific permission
            if permission not in user_permissions:
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'Permission "{permission}" required',
                    'required_permission': permission,
                    'user_permissions': user_permissions
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_organization_access(f):
    """Decorator to ensure user has access to the organization in request"""
    @wraps(f)
    @require_auth
    def decorated_function(*args, **kwargs):
        # Get organization ID from request (URL param, JSON body, or query param)
        org_id = (
            kwargs.get('organization_id') or
            request.json.get('organization_id') if request.json else None or
            request.args.get('organization_id')
        )
        
        if org_id and org_id != g.organization_id:
            return jsonify({
                'error': 'Access denied',
                'message': 'You do not have access to this organization'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def create_access_token(user_data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token"""
    if expires_delta is None:
        expires_delta = current_app.config['JWT_ACCESS_TOKEN_EXPIRES']
    
    # Generate unique JWT ID for revocation support
    import uuid
    jti = str(uuid.uuid4())
    
    payload = {
        'sub': user_data['user_id'],
        'email': user_data['email'],
        'organization_id': user_data.get('organization_id'),
        'permissions': user_data.get('permissions', []),
        'roles': user_data.get('roles', []),
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires_delta,
        'jti': jti,
        'type': 'access'
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )
    
    # Store token metadata in Redis for session management
    redis_client.setex(
        f"token:{jti}",
        int(expires_delta.total_seconds()),
        user_data['user_id']
    )
    
    return token

def create_refresh_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a new refresh token"""
    if expires_delta is None:
        expires_delta = current_app.config['JWT_REFRESH_TOKEN_EXPIRES']
    
    import uuid
    jti = str(uuid.uuid4())
    
    payload = {
        'sub': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires_delta,
        'jti': jti,
        'type': 'refresh'
    }
    
    token = jwt.encode(
        payload,
        current_app.config['JWT_SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM']
    )
    
    # Store refresh token in Redis
    redis_client.setex(
        f"refresh_token:{jti}",
        int(expires_delta.total_seconds()),
        user_id
    )
    
    return token

def revoke_token(jti: str):
    """Revoke a token by adding it to blacklist"""
    # Add to blacklist with expiration (tokens expire anyway)
    redis_client.setex(f"revoked_token:{jti}", 86400 * 30, "revoked")  # 30 days

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current authenticated user from request context"""
    return getattr(g, 'current_user', None)

def get_current_user_id() -> Optional[str]:
    """Get current user ID from request context"""
    return getattr(g, 'user_id', None)

def get_current_organization_id() -> Optional[str]:
    """Get current organization ID from request context"""
    return getattr(g, 'organization_id', None)

def get_user_permissions() -> List[str]:
    """Get current user's permissions"""
    return getattr(g, 'permissions', [])