"""
Webhook Processor - Handles incoming webhook requests
Provides dynamic endpoint creation and request validation
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from flask import request, jsonify
from jsonschema import validate, ValidationError
from .trigger_service import TriggerProcessor, TriggerExecutionContext
from models import Triggers

logger = logging.getLogger("WebhookProcessor")

class WebhookProcessor(TriggerProcessor):
    """Handles incoming webhook requests"""
    
    def __init__(self, trigger_service, app):
        super().__init__(trigger_service)
        self.app = app
        self.webhook_routes: Dict[str, str] = {}  # webhook_url -> trigger_id
        
    async def setup(self, trigger: Triggers) -> None:
        """Setup webhook endpoint for the trigger"""
        if trigger.type != 'webhook':
            return
            
        webhook_url = trigger.webhook_url
        if not webhook_url:
            # Generate webhook URL if not exists
            webhook_url = f"/api/webhook/{trigger.id}"
            
        # Register the route
        self.webhook_routes[webhook_url] = trigger.id
        
        # Add Flask route dynamically
        endpoint_name = f"webhook_{trigger.id}"
        
        # Remove existing route if it exists
        if endpoint_name in self.app.view_functions:
            del self.app.view_functions[endpoint_name]
            
        # Add new route
        self.app.add_url_rule(
            webhook_url,
            endpoint_name,
            self._create_webhook_handler(trigger.id),
            methods=['GET', 'POST', 'PUT', 'DELETE']
        )
        
        logger.info(f"Setup webhook endpoint: {webhook_url} for trigger {trigger.id}")
        
    async def teardown(self, trigger: Triggers) -> None:
        """Remove webhook endpoint for the trigger"""
        if trigger.type != 'webhook':
            return
            
        webhook_url = trigger.webhook_url
        if webhook_url in self.webhook_routes:
            del self.webhook_routes[webhook_url]
            
        # Remove Flask route
        endpoint_name = f"webhook_{trigger.id}"
        if endpoint_name in self.app.view_functions:
            del self.app.view_functions[endpoint_name]
            
        logger.info(f"Removed webhook endpoint: {webhook_url} for trigger {trigger.id}")
        
    def _create_webhook_handler(self, trigger_id: str):
        """Create a Flask handler function for the webhook"""
        
        def webhook_handler():
            try:
                # Get trigger configuration
                from database import LocalSession
                trigger = None
                config = None
                with LocalSession() as session:
                    trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
                    
                    if not trigger or not trigger.enabled:
                        return jsonify({'error': 'Webhook not found or disabled'}), 404
                    
                    # Extract config while session is still active
                    config = trigger.config
                    # Store trigger data we need for later use
                    trigger_data = {
                        'id': trigger.id,
                        'flow_id': trigger.flow_id,
                        'type': trigger.type,
                        'name': trigger.name,
                        'enabled': trigger.enabled,
                        'config': trigger.config
                    }
                
                # Validate HTTP method
                allowed_method = config.get('method', 'POST')
                if request.method != allowed_method:
                    return jsonify({'error': f'Method {request.method} not allowed'}), 405
                    
                # Validate authentication
                auth_result = self._validate_auth(request, config)
                if not auth_result['valid']:
                    return jsonify({'error': auth_result['error']}), 401
                    
                # Extract payload
                payload = self._extract_payload(request)
                
                # Validate payload schema if configured
                if config.get('bodySchema'):
                    try:
                        validate(instance=payload, schema=config['bodySchema'])
                    except ValidationError as e:
                        return jsonify({'error': f'Invalid payload: {e.message}'}), 400
                    
                # Prepare trigger payload
                trigger_payload = {
                    'webhook': {
                        'method': request.method,
                        'headers': dict(request.headers),
                        'url': request.url,
                        'remote_addr': request.remote_addr,
                        'user_agent': request.headers.get('User-Agent', ''),
                        'received_at': datetime.now(timezone.utc).isoformat()
                    },
                    'data': payload
                }
                
                # Fire the trigger asynchronously
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    execution_id = loop.run_until_complete(
                        self.trigger_service.fire_trigger(trigger_id, trigger_payload)
                    )
                    
                    return jsonify({
                        'success': True,
                        'execution_id': execution_id,
                        'message': 'Webhook processed successfully'
                    }), 200
                    
                finally:
                    loop.close()
                    
            except Exception as e:
                logger.error(f"Webhook handler error for trigger {trigger_id}: {e}", exc_info=True)
                return jsonify({
                    'error': 'Internal server error',
                    'details': str(e) if self.app.debug else None
                }), 500
                
        return webhook_handler
        
    def _validate_auth(self, request, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate webhook authentication"""
        auth_type = config.get('authType', 'none')
        
        if auth_type == 'none':
            return {'valid': True}
            
        elif auth_type == 'token':
            auth_config = config.get('authConfig', {})
            expected_token = auth_config.get('token')
            
            if not expected_token:
                return {'valid': False, 'error': 'No token configured'}
                
            # Check Authorization header
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]  # Remove 'Bearer ' prefix
            else:
                # Check query parameter
                token = request.args.get('token', '')
                
            if not token:
                return {'valid': False, 'error': 'Missing authentication token'}
                
            if token != expected_token:
                return {'valid': False, 'error': 'Invalid authentication token'}
                
            return {'valid': True}
            
        elif auth_type == 'hmac':
            auth_config = config.get('authConfig', {})
            secret = auth_config.get('secret')
            
            if not secret:
                return {'valid': False, 'error': 'No HMAC secret configured'}
                
            # Get signature from headers
            signature_header = request.headers.get('X-Hub-Signature-256') or request.headers.get('X-Signature-256')
            if not signature_header:
                return {'valid': False, 'error': 'Missing HMAC signature header'}
                
            # Extract signature
            if signature_header.startswith('sha256='):
                received_signature = signature_header[7:]
            else:
                received_signature = signature_header
                
            # Calculate expected signature
            payload = request.get_data()
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            if not hmac.compare_digest(received_signature, expected_signature):
                return {'valid': False, 'error': 'Invalid HMAC signature'}
                
            return {'valid': True}
            
        else:
            return {'valid': False, 'error': f'Unsupported auth type: {auth_type}'}
            
    def _extract_payload(self, request) -> Dict[str, Any]:
        """Extract payload from request"""
        if request.method == 'GET':
            return dict(request.args)
            
        elif request.content_type and 'application/json' in request.content_type:
            try:
                return request.get_json() or {}
            except Exception:
                return {}
                
        elif request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            return dict(request.form)
            
        else:
            # Try to parse as JSON, fall back to text
            try:
                data = request.get_data(as_text=True)
                if data:
                    return json.loads(data)
                return {}
            except Exception:
                return {'raw_data': request.get_data(as_text=True)}
                
    async def process(self, context: TriggerExecutionContext) -> Dict[str, Any]:
        """Process webhook trigger execution"""
        # For webhooks, the actual processing happens in the handler
        # This method executes the flow
        
        logger.info(f"Processing webhook trigger {context.trigger.id} for flow {context.trigger.flow_id}")
        logger.info(f"Trigger payload: {context.payload}")
        
        # Execute the flow with the trigger context
        from flow_translator import execute_flow_from_trigger
        try:
            flow_execution_id = await execute_flow_from_trigger(
                context.trigger,
                context.payload
            )
            
            return {
                'flow_execution_id': flow_execution_id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to execute flow from webhook trigger {context.trigger.id}: {e}")
            raise