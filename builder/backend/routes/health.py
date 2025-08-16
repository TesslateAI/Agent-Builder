"""
Health check endpoints for monitoring application status
"""
import os
import time
from flask import Blueprint, jsonify
from datetime import datetime
import redis
from sqlalchemy import text

from database import engine, LocalSession
from tframex_config import get_tframex_app_instance

health_bp = Blueprint('health', __name__)

# Track application start time
START_TIME = time.time()

def check_database_connection():
    """Check if database is reachable"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

def check_redis_connection():
    """Check if Redis is reachable"""
    try:
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD')
        r = redis.Redis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True, socket_connect_timeout=2)
        r.ping()
        return True, "Connected"
    except Exception as e:
        return False, str(e)

def check_tframex():
    """Check if TFrameX is properly initialized"""
    try:
        tframex_app = get_tframex_app_instance()
        agent_count = len(tframex_app._agents)
        tool_count = len(tframex_app._tools)
        return True, f"{agent_count} agents, {tool_count} tools registered"
    except Exception as e:
        return False, str(e)

@health_bp.route('/health', methods=['GET'])
def health():
    """Basic health check endpoint"""
    uptime = time.time() - START_TIME
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": round(uptime, 2),
        "version": "1.0.0",
        "service": "agent-builder-backend"
    }), 200

@health_bp.route('/health/live', methods=['GET'])
def liveness():
    """Kubernetes liveness probe endpoint"""
    return jsonify({
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }), 200

@health_bp.route('/health/ready', methods=['GET'])
def readiness():
    """Kubernetes readiness probe endpoint"""
    checks = {
        "database": check_database_connection(),
        "redis": check_redis_connection(),
        "tframex": check_tframex()
    }
    
    all_healthy = all(status for status, _ in checks.values())
    status_code = 200 if all_healthy else 503
    
    response = {
        "status": "ready" if all_healthy else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            name: {
                "status": "pass" if status else "fail",
                "message": message
            }
            for name, (status, message) in checks.items()
        }
    }
    
    return jsonify(response), status_code

@health_bp.route('/health/detailed', methods=['GET'])
def detailed_health():
    """Detailed health check with all component statuses"""
    uptime = time.time() - START_TIME
    
    # Perform all checks
    db_status, db_message = check_database_connection()
    redis_status, redis_message = check_redis_connection()
    tframex_status, tframex_message = check_tframex()
    
    # Get additional metrics
    try:
        with LocalSession() as session:
            project_count = session.execute(text("SELECT COUNT(*) FROM projects")).scalar()
            flow_count = session.execute(text("SELECT COUNT(*) FROM flows")).scalar()
            user_count = session.execute(text("SELECT COUNT(*) FROM users")).scalar()
        
        db_metrics = {
            "projects": project_count,
            "flows": flow_count,
            "users": user_count
        }
    except Exception:
        db_metrics = None
    
    # Get TFrameX details
    try:
        tframex_app = get_tframex_app_instance()
        tframex_details = {
            "agents": list(tframex_app._agents.keys()),
            "tools": list(tframex_app._tools.keys()),
            "patterns": ["sequential", "parallel", "router", "discussion"]
        }
    except Exception:
        tframex_details = None
    
    response = {
        "status": "healthy" if all([db_status, redis_status, tframex_status]) else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "agent-builder-backend",
        "uptime": {
            "seconds": round(uptime, 2),
            "human_readable": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
        },
        "components": {
            "database": {
                "status": "healthy" if db_status else "unhealthy",
                "message": db_message,
                "metrics": db_metrics
            },
            "redis": {
                "status": "healthy" if redis_status else "unhealthy",
                "message": redis_message
            },
            "tframex": {
                "status": "healthy" if tframex_status else "unhealthy",
                "message": tframex_message,
                "details": tframex_details
            }
        },
        "environment": {
            "flask_env": os.getenv("FLASK_ENV", "production"),
            "database_url": "postgresql" if "postgresql" in os.getenv("DATABASE_URL", "") else "sqlite",
            "redis_host": os.getenv("REDIS_HOST", "localhost")
        }
    }
    
    status_code = 200 if all([db_status, redis_status, tframex_status]) else 503
    return jsonify(response), status_code