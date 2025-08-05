"""
File Processor - Handles file-based triggers
Monitors file system for changes, new files, deletions, and modifications
"""
import logging
import asyncio
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Set, Optional
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from .trigger_service import TriggerProcessor, TriggerExecutionContext
from models import Triggers

logger = logging.getLogger("FileProcessor")

class FileTriggerHandler(FileSystemEventHandler):
    """File system event handler for triggers"""
    
    def __init__(self, trigger: Triggers, processor: 'FileProcessor'):
        self.trigger = trigger
        self.processor = processor
        self.config = trigger.config
        
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events"""
        if not event.is_directory and self._matches_criteria(event.src_path, 'created'):
            asyncio.create_task(self._fire_trigger(event, 'created'))
            
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events"""
        if not event.is_directory and self._matches_criteria(event.src_path, 'modified'):
            asyncio.create_task(self._fire_trigger(event, 'modified'))
            
    def on_deleted(self, event: FileSystemEvent):
        """Handle file deletion events"""
        if not event.is_directory and self._matches_criteria(event.src_path, 'deleted'):
            asyncio.create_task(self._fire_trigger(event, 'deleted'))
            
    def on_moved(self, event: FileSystemEvent):
        """Handle file move/rename events"""
        if not event.is_directory and hasattr(event, 'dest_path'):
            if self._matches_criteria(event.dest_path, 'moved'):
                asyncio.create_task(self._fire_trigger(event, 'moved'))
                
    def _matches_criteria(self, file_path: str, event_type: str) -> bool:
        """Check if file matches trigger criteria"""
        config = self.config
        
        # Check if event type is monitored
        watch_events = config.get('watchEvents', ['created'])
        if event_type not in watch_events:
            return False
            
        # Check file pattern
        if config.get('filePattern'):
            import fnmatch
            filename = os.path.basename(file_path)
            if not fnmatch.fnmatch(filename, config['filePattern']):
                return False
                
        # Check file extension
        if config.get('fileExtensions'):
            file_ext = os.path.splitext(file_path)[1].lower()
            allowed_exts = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                          for ext in config['fileExtensions']]
            if file_ext not in allowed_exts:
                return False
                
        # Check minimum file size
        if config.get('minSize') and os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
                if file_size < config['minSize']:
                    return False
            except OSError:
                return False
                
        # Check maximum file size
        if config.get('maxSize') and os.path.exists(file_path):
            try:
                file_size = os.path.getsize(file_path)
                if file_size > config['maxSize']:
                    return False
            except OSError:
                return False
                
        return True
        
    async def _fire_trigger(self, event: FileSystemEvent, event_type: str):
        """Fire the trigger with file event data"""
        try:
            file_path = getattr(event, 'dest_path', None) or event.src_path
            file_data = self._extract_file_data(file_path, event_type)
            
            payload = {
                'file': file_data,
                'event_type': event_type,
                'trigger_type': 'file',
                'detected_at': datetime.now(timezone.utc).isoformat()
            }
            
            if hasattr(event, 'dest_path'):
                payload['file']['moved_from'] = event.src_path
                
            await self.processor.trigger_service.fire_trigger(self.trigger.id, payload)
            logger.info(f"File trigger {self.trigger.id} fired for {event_type} event on {file_path}")
            
        except Exception as e:
            logger.error(f"Error firing file trigger {self.trigger.id}: {e}")
            
    def _extract_file_data(self, file_path: str, event_type: str) -> Dict[str, Any]:
        """Extract file metadata"""
        data = {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'directory': os.path.dirname(file_path),
            'event_type': event_type
        }
        
        # Add file stats if file exists (not for deletion events)
        if event_type != 'deleted' and os.path.exists(file_path):
            try:
                stat = os.stat(file_path)
                data.update({
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    'extension': os.path.splitext(file_path)[1],
                    'is_executable': os.access(file_path, os.X_OK),
                    'permissions': oct(stat.st_mode)[-3:]
                })
                
                # Add file hash for content verification
                if self.config.get('includeHash', False) and stat.st_size < 10 * 1024 * 1024:  # Max 10MB
                    data['hash'] = self._calculate_file_hash(file_path)
                    
            except OSError as e:
                logger.warning(f"Could not get file stats for {file_path}: {e}")
                
        return data
        
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file content"""
        hasher = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return ""

class FileProcessor(TriggerProcessor):
    """Handles file system triggers using watchdog"""
    
    def __init__(self, trigger_service):
        super().__init__(trigger_service)
        self.observers: Dict[str, Observer] = {}  # trigger_id -> observer
        self.handlers: Dict[str, FileTriggerHandler] = {}  # trigger_id -> handler
        
    async def start(self):
        """Start the file processor"""
        logger.info("File processor started")
        
    async def stop(self):
        """Stop the file processor"""
        # Stop all observers
        for observer in self.observers.values():
            observer.stop()
            observer.join()
            
        self.observers.clear()
        self.handlers.clear()
        logger.info("File processor stopped")
        
    async def setup(self, trigger: Triggers) -> None:
        """Setup file system monitoring for the trigger"""
        if trigger.type != 'file':
            return
            
        config = trigger.config
        watch_path = config.get('watchPath')
        
        if not watch_path:
            raise ValueError("Watch path is required for file triggers")
            
        if not os.path.exists(watch_path):
            raise ValueError(f"Watch path does not exist: {watch_path}")
            
        # Stop existing observer if it exists
        if trigger.id in self.observers:
            observer = self.observers[trigger.id]
            observer.stop()
            observer.join()
            
        # Create new observer and handler
        handler = FileTriggerHandler(trigger, self)
        observer = Observer()
        
        # Determine if recursive monitoring is needed
        recursive = config.get('recursive', False)
        
        observer.schedule(handler, watch_path, recursive=recursive)
        observer.start()
        
        self.observers[trigger.id] = observer
        self.handlers[trigger.id] = handler
        
        logger.info(f"Started file monitoring for trigger {trigger.id} on path: {watch_path} (recursive: {recursive})")
        
    async def teardown(self, trigger: Triggers) -> None:
        """Stop file system monitoring for the trigger"""
        if trigger.type != 'file':
            return
            
        if trigger.id in self.observers:
            observer = self.observers[trigger.id]
            observer.stop()
            observer.join()
            del self.observers[trigger.id]
            
        if trigger.id in self.handlers:
            del self.handlers[trigger.id]
            
        logger.info(f"Stopped file monitoring for trigger {trigger.id}")
        
    async def process(self, context: TriggerExecutionContext) -> Dict[str, Any]:
        """Process file trigger execution"""
        from flow_translator import execute_flow_from_trigger
        
        try:
            # Execute the flow with the trigger context
            flow_execution_id = await execute_flow_from_trigger(
                context.trigger,
                context.payload
            )
            
            return {
                'flow_execution_id': flow_execution_id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to execute flow from file trigger {context.trigger.id}: {e}")
            raise
            
    def get_monitor_status(self, trigger_id: str) -> Dict[str, Any]:
        """Get monitoring status for a trigger"""
        if trigger_id not in self.observers:
            return {'status': 'not_monitoring'}
            
        observer = self.observers[trigger_id]
        return {
            'status': 'monitoring' if observer.is_alive() else 'stopped',
            'observer_alive': observer.is_alive()
        }
        
    async def test_trigger(self, trigger: Triggers) -> Dict[str, Any]:
        """Test file trigger configuration"""
        config = trigger.config
        watch_path = config.get('watchPath')
        
        if not watch_path:
            return {'valid': False, 'error': 'Watch path is required'}
            
        if not os.path.exists(watch_path):
            return {'valid': False, 'error': f'Watch path does not exist: {watch_path}'}
            
        if not os.access(watch_path, os.R_OK):
            return {'valid': False, 'error': f'Watch path is not readable: {watch_path}'}
            
        # Check if path is a directory for recursive monitoring
        if config.get('recursive', False) and not os.path.isdir(watch_path):
            return {'valid': False, 'error': 'Recursive monitoring requires a directory path'}
            
        return {
            'valid': True,
            'path_type': 'directory' if os.path.isdir(watch_path) else 'file',
            'readable': os.access(watch_path, os.R_OK),
            'writable': os.access(watch_path, os.W_OK)
        }