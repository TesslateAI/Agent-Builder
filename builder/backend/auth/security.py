"""
Simple authentication security utilities
Handles failed login tracking and basic rate limiting
"""
import os
import redis
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from functools import wraps
from flask import request, jsonify

logger = logging.getLogger(__name__)

# Redis client for tracking auth attempts
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)

# Simple configuration
MAX_FAILED_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 5))
LOCKOUT_DURATION = int(os.getenv('LOGIN_LOCKOUT_MINUTES', 15))
RATE_LIMIT_WINDOW = 60  # 1 minute
RATE_LIMIT_MAX_ATTEMPTS = 10  # max attempts per minute


def log_auth_attempt(email: str, success: bool, ip_address: str, user_agent: str = None) -> None:
    """Log authentication attempt with details"""
    try:
        # Create structured log entry
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'email': email,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        if success:
            logger.info(f"Successful login: {email} from {ip_address}")
            # Clear failed attempts on successful login
            redis_client.delete(f"failed_login:{email}")
        else:
            logger.warning(f"Failed login attempt: {email} from {ip_address}")
            # Track failed attempt
            _track_failed_attempt(email)
            
    except Exception as e:
        logger.error(f"Error logging auth attempt: {e}")


def _track_failed_attempt(email: str) -> None:
    """Track failed login attempts in Redis"""
    key = f"failed_login:{email}"
    
    # Increment failed attempts
    count = redis_client.incr(key)
    
    # Set expiration on first attempt
    if count == 1:
        redis_client.expire(key, LOCKOUT_DURATION * 60)
    
    # Check if account should be locked
    if count >= MAX_FAILED_ATTEMPTS:
        lock_account(email)


def lock_account(email: str) -> None:
    """Lock account after too many failed attempts"""
    lockout_key = f"account_locked:{email}"
    redis_client.setex(lockout_key, LOCKOUT_DURATION * 60, "locked")
    logger.warning(f"Account locked due to failed attempts: {email}")


def is_account_locked(email: str) -> bool:
    """Check if account is locked"""
    return redis_client.exists(f"account_locked:{email}") > 0


def get_failed_attempts(email: str) -> int:
    """Get current failed attempt count"""
    count = redis_client.get(f"failed_login:{email}")
    return int(count) if count else 0


def reset_failed_attempts(email: str) -> None:
    """Reset failed login attempts (e.g., after password reset)"""
    redis_client.delete(f"failed_login:{email}")
    redis_client.delete(f"account_locked:{email}")


def check_rate_limit(ip_address: str) -> bool:
    """Simple IP-based rate limiting"""
    key = f"rate_limit:{ip_address}"
    
    try:
        # Increment counter
        count = redis_client.incr(key)
        
        # Set expiration on first request
        if count == 1:
            redis_client.expire(key, RATE_LIMIT_WINDOW)
        
        # Check if over limit
        if count > RATE_LIMIT_MAX_ATTEMPTS:
            logger.warning(f"Rate limit exceeded for IP: {ip_address}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Rate limit check error: {e}")
        # Allow request on error to avoid blocking legitimate users
        return True


def get_auth_metrics(email: str) -> Dict[str, Any]:
    """Get authentication metrics for monitoring"""
    return {
        'failed_attempts': get_failed_attempts(email),
        'is_locked': is_account_locked(email),
        'max_attempts': MAX_FAILED_ATTEMPTS,
        'lockout_duration_minutes': LOCKOUT_DURATION
    }


def rate_limit(max_requests: int = 10, window_seconds: int = 60):
    """Simple rate limiting decorator - disabled in development"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting in development
            if os.getenv('ENVIRONMENT', 'development') == 'development':
                return f(*args, **kwargs)
                
            ip_address = request.remote_addr
            key = f"rate_limit:{f.__name__}:{ip_address}"
            
            try:
                # Increment counter
                count = redis_client.incr(key)
                
                # Set expiration on first request
                if count == 1:
                    redis_client.expire(key, window_seconds)
                
                # Check if over limit
                if count > max_requests:
                    logger.warning(f"Rate limit exceeded for {f.__name__} from IP: {ip_address}")
                    return jsonify({
                        'error': 'Rate limit exceeded',
                        'message': f'Too many requests. Try again in {window_seconds} seconds.'
                    }), 429
                    
                return f(*args, **kwargs)
                
            except Exception as e:
                logger.error(f"Rate limit check error: {e}")
                # Allow request on error
                return f(*args, **kwargs)
                
        return decorated_function
    return decorator