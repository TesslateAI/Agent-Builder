"""
Trigger Service - Core service for managing triggers
Handles trigger registration, execution, and lifecycle management
"""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Triggers, TriggerExecutions, Flow
from database import LocalSession

logger = logging.getLogger("TriggerService")

class TriggerExecutionContext:
    """Context object passed to trigger processors"""
    def __init__(self, trigger: Triggers, payload: Dict[str, Any], execution_id: str):
        self.trigger = trigger
        self.payload = payload
        self.execution_id = execution_id
        self.started_at = datetime.now(timezone.utc)

class TriggerProcessor:
    """Base class for trigger processors"""
    
    def __init__(self, trigger_service: 'TriggerService'):
        self.trigger_service = trigger_service
        
    async def setup(self, trigger: Triggers) -> None:
        """Setup the processor for a specific trigger"""
        pass
        
    async def teardown(self, trigger: Triggers) -> None:
        """Cleanup when trigger is removed"""
        pass
        
    async def process(self, context: TriggerExecutionContext) -> Dict[str, Any]:
        """Process the trigger execution"""
        raise NotImplementedError

class TriggerService:
    """Core service for managing triggers"""
    
    def __init__(self):
        self.processors: Dict[str, TriggerProcessor] = {}
        self.active_triggers: Dict[str, Triggers] = {}
        self._running = False
        
    def register_processor(self, trigger_type: str, processor: TriggerProcessor):
        """Register a processor for a specific trigger type"""
        self.processors[trigger_type] = processor
        logger.info(f"Registered processor for trigger type: {trigger_type}")
        
    async def start(self):
        """Start the trigger service"""
        self._running = True
        logger.info("Trigger service started")
        
        # Load and setup all enabled triggers
        await self._load_active_triggers()
        
    async def stop(self):
        """Stop the trigger service"""
        self._running = False
        
        # Teardown all active triggers
        for trigger in self.active_triggers.values():
            await self._teardown_trigger(trigger)
            
        self.active_triggers.clear()
        logger.info("Trigger service stopped")
        
    async def _load_active_triggers(self):
        """Load all enabled triggers from database and set them up"""
        with LocalSession() as session:
            triggers = session.query(Triggers).filter(Triggers.enabled == True).all()
            
            for trigger in triggers:
                try:
                    await self._setup_trigger(trigger)
                    self.active_triggers[trigger.id] = trigger
                    logger.info(f"Loaded and setup trigger: {trigger.name} ({trigger.id})")
                except Exception as e:
                    logger.error(f"Failed to setup trigger {trigger.id}: {e}", exc_info=True)
                    # Mark trigger as error
                    await self._update_trigger_error(trigger.id, str(e))
    
    async def register_trigger(self, flow_id: str, trigger_config: Dict[str, Any]) -> Triggers:
        """Register a new trigger and start monitoring"""
        trigger_id = str(uuid.uuid4())
        
        with LocalSession() as session:
            # Validate flow exists
            flow = session.query(Flow).filter(Flow.id == flow_id).first()
            if not flow:
                raise ValueError(f"Flow {flow_id} not found")
            
            # Create trigger record
            trigger = Triggers(
                id=trigger_id,
                flow_id=flow_id,
                type=trigger_config['type'],
                name=trigger_config['name'],
                description=trigger_config.get('description', ''),
                config=trigger_config['config'],
                enabled=trigger_config.get('enabled', True),
                created_by=trigger_config.get('created_by'),
                organization_id=trigger_config.get('organization_id')
            )
            
            # Set webhook URL for webhook triggers
            if trigger.type == 'webhook':
                trigger.webhook_url = f"/api/webhook/{trigger_id}"
            
            session.add(trigger)
            session.commit()
            session.refresh(trigger)
        
        # Setup the trigger if enabled
        if trigger.enabled:
            try:
                await self._setup_trigger(trigger)
                self.active_triggers[trigger.id] = trigger
                logger.info(f"Registered and setup trigger: {trigger.name} ({trigger.id})")
            except Exception as e:
                logger.error(f"Failed to setup trigger {trigger.id}: {e}", exc_info=True)
                await self._update_trigger_error(trigger.id, str(e))
                
        return trigger
        
    async def unregister_trigger(self, trigger_id: str) -> None:
        """Stop and remove a trigger"""
        # Remove from active triggers
        if trigger_id in self.active_triggers:
            trigger = self.active_triggers[trigger_id]
            await self._teardown_trigger(trigger)
            del self.active_triggers[trigger_id]
            
        # Remove from database
        with LocalSession() as session:
            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
            if trigger:
                session.delete(trigger)
                session.commit()
                logger.info(f"Unregistered trigger: {trigger_id}")
            
    async def update_trigger(self, trigger_id: str, updates: Dict[str, Any]) -> Triggers:
        """Update trigger configuration"""
        with LocalSession() as session:
            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
            if not trigger:
                raise ValueError(f"Trigger {trigger_id} not found")
                
            # Update fields
            for key, value in updates.items():
                if hasattr(trigger, key):
                    setattr(trigger, key, value)
                    
            trigger.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(trigger)
            
        # If trigger is active, reconfigure it
        if trigger_id in self.active_triggers:
            await self._teardown_trigger(self.active_triggers[trigger_id])
            if trigger.enabled:
                await self._setup_trigger(trigger)
                self.active_triggers[trigger_id] = trigger
            else:
                del self.active_triggers[trigger_id]
                
        return trigger
        
    async def fire_trigger(self, trigger_id: str, payload: Dict[str, Any]) -> str:
        """Execute a flow from a trigger"""
        execution_id = str(uuid.uuid4())
        
        # Load trigger and create execution record
        with LocalSession() as session:
            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
            if not trigger:
                raise ValueError(f"Trigger {trigger_id} not found")
                
            if not trigger.enabled:
                raise ValueError(f"Trigger {trigger_id} is disabled")
                
            # Create execution record
            execution = TriggerExecutions(
                id=execution_id,
                trigger_id=trigger_id,
                payload=payload,
                status='running'
            )
            session.add(execution)
            session.commit()
            
            # Create execution context with fresh trigger object within session
            context = TriggerExecutionContext(trigger, payload, execution_id)
            
            # Get processor for trigger type while we have the trigger object
            processor = self.processors.get(trigger.type)
            if not processor:
                raise ValueError(f"No processor registered for trigger type: {trigger.type}")
            
            # Store trigger type for use outside session
            trigger_type = trigger.type
            
        try:
            # Process the trigger using the context created within the session
            result = await processor.process(context)
            
            # Update execution status
            duration_ms = int((datetime.now(timezone.utc) - context.started_at).total_seconds() * 1000)
            
            with LocalSession() as session:
                execution = session.query(TriggerExecutions).filter(TriggerExecutions.id == execution_id).first()
                if execution:
                    execution.status = 'success'
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.duration_ms = duration_ms
                    execution.flow_execution_id = result.get('flow_execution_id')
                    session.commit()
                    
                # Update trigger stats
                trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
                if trigger:
                    trigger.trigger_count += 1
                    trigger.last_triggered_at = datetime.now(timezone.utc)
                    trigger.last_error = None  # Clear any previous error
                    session.commit()
                    
            logger.info(f"Trigger {trigger_id} executed successfully in {duration_ms}ms")
            return execution_id
            
        except Exception as e:
            # Update execution with error
            with LocalSession() as session:
                execution = session.query(TriggerExecutions).filter(TriggerExecutions.id == execution_id).first()
                if execution:
                    execution.status = 'failure'
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.error = str(e)
                    session.commit()
                    
                # Update trigger error count
                trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
                if trigger:
                    trigger.error_count += 1
                    trigger.last_error = str(e)
                    session.commit()
                    
            logger.error(f"Trigger {trigger_id} execution failed: {e}", exc_info=True)
            raise
            
    async def get_trigger_status(self, trigger_id: str) -> Dict[str, Any]:
        """Get current trigger status and health"""
        with LocalSession() as session:
            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
            if not trigger:
                raise ValueError(f"Trigger {trigger_id} not found")
                
            # Get recent executions
            recent_executions = (
                session.query(TriggerExecutions)
                .filter(TriggerExecutions.trigger_id == trigger_id)
                .order_by(TriggerExecutions.triggered_at.desc())
                .limit(5)
                .all()
            )
            
            status = {
                'id': trigger.id,
                'name': trigger.name,
                'type': trigger.type,
                'enabled': trigger.enabled,
                'status': 'armed' if trigger.enabled else 'disarmed',
                'trigger_count': trigger.trigger_count,
                'error_count': trigger.error_count,
                'last_triggered_at': trigger.last_triggered_at.isoformat() if trigger.last_triggered_at else None,
                'last_error': trigger.last_error,
                'next_run_at': trigger.next_run_at.isoformat() if trigger.next_run_at else None,
                'recent_executions': [
                    {
                        'id': ex.id,
                        'status': ex.status,
                        'triggered_at': ex.triggered_at.isoformat(),
                        'duration_ms': ex.duration_ms,
                        'error': ex.error
                    }
                    for ex in recent_executions
                ]
            }
            
            # Determine health status
            if trigger.last_error:
                status['status'] = 'error'
            elif not trigger.enabled:
                status['status'] = 'disarmed'
            elif trigger_id in self.active_triggers:
                status['status'] = 'armed'
            else:
                status['status'] = 'error'
                status['last_error'] = 'Trigger not active in service'
                
            return status
    
    async def list_triggers(self, flow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all triggers, optionally filtered by flow"""
        with LocalSession() as session:
            query = session.query(Triggers)
            if flow_id:
                query = query.filter(Triggers.flow_id == flow_id)
                
            triggers = query.all()
            
            return [
                {
                    'id': t.id,
                    'flow_id': t.flow_id,
                    'type': t.type,
                    'name': t.name,
                    'description': t.description,
                    'enabled': t.enabled,
                    'webhook_url': t.webhook_url,
                    'trigger_count': t.trigger_count,
                    'error_count': t.error_count,
                    'last_triggered_at': t.last_triggered_at.isoformat() if t.last_triggered_at else None,
                    'next_run_at': t.next_run_at.isoformat() if t.next_run_at else None,
                    'created_at': t.created_at.isoformat(),
                    'updated_at': t.updated_at.isoformat()
                }
                for t in triggers
            ]
    
    async def _setup_trigger(self, trigger: Triggers):
        """Setup a trigger with its processor"""
        processor = self.processors.get(trigger.type)
        if not processor:
            raise ValueError(f"No processor registered for trigger type: {trigger.type}")
            
        await processor.setup(trigger)
        
    async def _teardown_trigger(self, trigger: Triggers):
        """Teardown a trigger with its processor"""
        processor = self.processors.get(trigger.type)
        if processor:
            try:
                await processor.teardown(trigger)
            except Exception as e:
                logger.error(f"Error tearing down trigger {trigger.id}: {e}")
                
    async def _update_trigger_error(self, trigger_id: str, error_message: str):
        """Update trigger with error information"""
        with LocalSession() as session:
            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
            if trigger:
                trigger.last_error = error_message
                trigger.error_count += 1
                session.commit()

# Global trigger service instance
_trigger_service = None

def get_trigger_service() -> TriggerService:
    """Get the global trigger service instance"""
    global _trigger_service
    if _trigger_service is None:
        _trigger_service = TriggerService()
    return _trigger_service