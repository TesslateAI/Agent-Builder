"""
Trigger API endpoints
Provides REST API for trigger management
"""
import logging
from flask import Blueprint, request, jsonify
from services.trigger_service import get_trigger_service
from models import Triggers, TriggerExecutions
from database import LocalSession

logger = logging.getLogger("TriggerAPI")

triggers_bp = Blueprint('triggers', __name__, url_prefix='/api/triggers')

@triggers_bp.route('', methods=['GET'])
def list_triggers():
    """List all triggers, optionally filtered by flow_id"""
    try:
        flow_id = request.args.get('flow_id')
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        triggers = loop.run_until_complete(trigger_service.list_triggers(flow_id))
        
        return jsonify({
            'success': True,
            'triggers': triggers
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing triggers: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('', methods=['POST'])
def create_trigger():
    """Create a new trigger"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['flow_id', 'type', 'name', 'config']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        trigger = loop.run_until_complete(trigger_service.register_trigger(
            flow_id=data['flow_id'],
            trigger_config=data
        ))
        
        return jsonify({
            'success': True,
            'trigger': {
                'id': trigger.id,
                'flow_id': trigger.flow_id,
                'type': trigger.type,
                'name': trigger.name,
                'description': trigger.description,
                'enabled': trigger.enabled,
                'webhook_url': trigger.webhook_url,
                'created_at': trigger.created_at.isoformat(),
                'updated_at': trigger.updated_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating trigger: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>', methods=['GET'])
def get_trigger(trigger_id):
    """Get trigger details and status"""
    try:
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        status = loop.run_until_complete(trigger_service.get_trigger_status(trigger_id))
        
        return jsonify({
            'success': True,
            'trigger': status
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error getting trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>', methods=['PUT'])
def update_trigger(trigger_id):
    """Update trigger configuration"""
    try:
        data = request.get_json()
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        trigger = loop.run_until_complete(trigger_service.update_trigger(trigger_id, data))
        
        return jsonify({
            'success': True,
            'trigger': {
                'id': trigger.id,
                'flow_id': trigger.flow_id,
                'type': trigger.type,
                'name': trigger.name,
                'description': trigger.description,
                'enabled': trigger.enabled,
                'webhook_url': trigger.webhook_url,
                'updated_at': trigger.updated_at.isoformat()
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error updating trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>', methods=['DELETE'])
def delete_trigger(trigger_id):
    """Delete a trigger"""
    try:
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        loop.run_until_complete(trigger_service.unregister_trigger(trigger_id))
        
        return jsonify({
            'success': True,
            'message': 'Trigger deleted successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>/enable', methods=['POST'])
def enable_trigger(trigger_id):
    """Enable a trigger"""
    try:
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        trigger = loop.run_until_complete(trigger_service.update_trigger(trigger_id, {'enabled': True}))
        
        return jsonify({
            'success': True,
            'message': 'Trigger enabled successfully',
            'trigger': {
                'id': trigger.id,
                'enabled': trigger.enabled
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error enabling trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>/disable', methods=['POST'])
def disable_trigger(trigger_id):
    """Disable a trigger"""
    try:
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        trigger = loop.run_until_complete(trigger_service.update_trigger(trigger_id, {'enabled': False}))
        
        return jsonify({
            'success': True,
            'message': 'Trigger disabled successfully',
            'trigger': {
                'id': trigger.id,
                'enabled': trigger.enabled
            }
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error disabling trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>/test', methods=['POST'])
def test_trigger(trigger_id):
    """Test fire a trigger manually"""
    try:
        data = request.get_json() or {}
        payload = data.get('payload', {})
        
        trigger_service = get_trigger_service()
        
        # Run async function in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        execution_id = loop.run_until_complete(trigger_service.fire_trigger(trigger_id, {
            'test': True,
            'triggered_at': asyncio.get_event_loop().time(),
            'payload': payload
        }))
        
        return jsonify({
            'success': True,
            'message': 'Trigger test executed successfully',
            'execution_id': execution_id
        }), 200
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 404
    except Exception as e:
        logger.error(f"Error testing trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>/executions', methods=['GET'])
def get_trigger_executions(trigger_id):
    """Get execution history for a trigger"""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')
        
        with LocalSession() as session:
            query = session.query(TriggerExecutions).filter(
                TriggerExecutions.trigger_id == trigger_id
            )
            
            if status:
                query = query.filter(TriggerExecutions.status == status)
                
            executions = query.order_by(
                TriggerExecutions.triggered_at.desc()
            ).offset(offset).limit(limit).all()
            
            return jsonify({
                'success': True,
                'executions': [
                    {
                        'id': ex.id,
                        'trigger_id': ex.trigger_id,
                        'flow_execution_id': ex.flow_execution_id,
                        'status': ex.status,
                        'triggered_at': ex.triggered_at.isoformat(),
                        'completed_at': ex.completed_at.isoformat() if ex.completed_at else None,
                        'duration_ms': ex.duration_ms,
                        'payload': ex.payload,
                        'error': ex.error
                    }
                    for ex in executions
                ]
            }), 200
        
    except Exception as e:
        logger.error(f"Error getting executions for trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@triggers_bp.route('/<trigger_id>/schedule/next-runs', methods=['GET'])
def get_next_runs(trigger_id):
    """Get next scheduled runs for a scheduled trigger"""
    try:
        count = int(request.args.get('count', 10))
        
        # Check if trigger is a schedule type
        with LocalSession() as session:
            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
            if not trigger:
                return jsonify({
                    'success': False,
                    'error': 'Trigger not found'
                }), 404
                
            if trigger.type != 'schedule':
                return jsonify({
                    'success': False,
                    'error': 'Trigger is not a scheduled trigger'
                }), 400
        
        # Get schedule processor
        trigger_service = get_trigger_service()
        schedule_processor = trigger_service.processors.get('schedule')
        
        if not schedule_processor:
            return jsonify({
                'success': False,
                'error': 'Schedule processor not available'
            }), 500
            
        next_runs = schedule_processor.get_next_runs(trigger_id, count)
        
        return jsonify({
            'success': True,
            'next_runs': [run.isoformat() for run in next_runs]
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting next runs for trigger {trigger_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500