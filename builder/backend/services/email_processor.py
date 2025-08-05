"""
Email Processor - Handles email-based triggers
Monitors email via IMAP and POP3 protocols
"""
import logging
import asyncio
import email
import imaplib
import poplib
import ssl
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from .trigger_service import TriggerProcessor, TriggerExecutionContext
from models import Triggers

logger = logging.getLogger("EmailProcessor")

class EmailProcessor(TriggerProcessor):
    """Handles email triggers using IMAP/POP3 monitoring"""
    
    def __init__(self, trigger_service):
        super().__init__(trigger_service)
        self.monitors: Dict[str, asyncio.Task] = {}  # trigger_id -> monitoring task
        self._running = False
        
    async def start(self):
        """Start the email processor"""
        self._running = True
        logger.info("Email processor started")
        
    async def stop(self):
        """Stop the email processor"""
        self._running = False
        
        # Cancel all monitoring tasks
        for task in self.monitors.values():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        self.monitors.clear()
        logger.info("Email processor stopped")
        
    async def setup(self, trigger: Triggers) -> None:
        """Setup email monitoring for the trigger"""
        if trigger.type != 'email':
            return
            
        config = trigger.config
        monitor_type = config.get('monitorType', 'imap')
        
        # Validate email configuration
        if not config.get('host') or not config.get('username') or not config.get('password'):
            raise ValueError("Email host, username, and password are required")
            
        # Stop existing monitor if it exists
        if trigger.id in self.monitors:
            task = self.monitors[trigger.id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        # Start new monitoring task
        if monitor_type == 'imap':
            task = asyncio.create_task(self._monitor_imap(trigger))
        elif monitor_type == 'pop3':
            task = asyncio.create_task(self._monitor_pop3(trigger))
        else:
            raise ValueError(f"Unsupported email monitor type: {monitor_type}")
            
        self.monitors[trigger.id] = task
        logger.info(f"Started email monitoring for trigger {trigger.id} using {monitor_type}")
        
    async def teardown(self, trigger: Triggers) -> None:
        """Stop email monitoring for the trigger"""
        if trigger.type != 'email':
            return
            
        if trigger.id in self.monitors:
            task = self.monitors[trigger.id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.monitors[trigger.id]
            logger.info(f"Stopped email monitoring for trigger {trigger.id}")
            
    async def _monitor_imap(self, trigger: Triggers):
        """Monitor emails using IMAP protocol"""
        config = trigger.config
        host = config['host']
        port = config.get('port', 993)
        username = config['username']
        password = config['password']
        folder = config.get('folder', 'INBOX')
        use_ssl = config.get('use_ssl', True)
        check_interval = config.get('check_interval', 60)  # seconds
        
        logger.info(f"Starting IMAP monitoring for {username}@{host}")
        
        # Track processed messages to avoid duplicates
        processed_uids = set()
        
        while self._running:
            try:
                # Connect to IMAP server
                if use_ssl:
                    mail = imaplib.IMAP4_SSL(host, port)
                else:
                    mail = imaplib.IMAP4(host, port)
                    
                mail.login(username, password)
                mail.select(folder)
                
                # Search for new messages based on trigger filters
                search_criteria = self._build_imap_search_criteria(config)
                result, data = mail.search(None, search_criteria)
                
                if result == 'OK':
                    message_ids = data[0].split()
                    
                    for msg_id in message_ids:
                        uid = msg_id.decode()
                        
                        # Skip if already processed
                        if uid in processed_uids:
                            continue
                            
                        # Fetch message
                        result, msg_data = mail.fetch(msg_id, '(RFC822)')
                        if result == 'OK':
                            raw_email = msg_data[0][1]
                            message = email.message_from_bytes(raw_email)
                            
                            # Check if message matches trigger criteria
                            if self._matches_criteria(message, config):
                                processed_uids.add(uid)
                                
                                # Extract email data
                                email_data = self._extract_email_data(message)
                                
                                # Fire trigger
                                payload = {
                                    'email': email_data,
                                    'trigger_type': 'email',
                                    'received_at': datetime.now(timezone.utc).isoformat()
                                }
                                
                                await self.trigger_service.fire_trigger(trigger.id, payload)
                                logger.info(f"Email trigger {trigger.id} fired for message from {email_data.get('from')}")
                
                mail.close()
                mail.logout()
                
            except Exception as e:
                logger.error(f"Error monitoring IMAP for trigger {trigger.id}: {e}")
                
            # Wait before next check
            await asyncio.sleep(check_interval)
            
    async def _monitor_pop3(self, trigger: Triggers):
        """Monitor emails using POP3 protocol"""
        config = trigger.config
        host = config['host']
        port = config.get('port', 995)
        username = config['username']
        password = config['password']
        use_ssl = config.get('use_ssl', True)
        check_interval = config.get('check_interval', 60)  # seconds
        delete_after_read = config.get('delete_after_read', False)
        
        logger.info(f"Starting POP3 monitoring for {username}@{host}")
        
        while self._running:
            try:
                # Connect to POP3 server
                if use_ssl:
                    mail = poplib.POP3_SSL(host, port)
                else:
                    mail = poplib.POP3(host, port)
                    
                mail.user(username)
                mail.pass_(password)
                
                # Get message count
                msg_count = len(mail.list()[1])
                
                if msg_count > 0:
                    # Process each message
                    for i in range(1, msg_count + 1):
                        try:
                            # Retrieve message
                            raw_message = b'\n'.join(mail.retr(i)[1])
                            message = email.message_from_bytes(raw_message)
                            
                            # Check if message matches trigger criteria
                            if self._matches_criteria(message, config):
                                # Extract email data
                                email_data = self._extract_email_data(message)
                                
                                # Fire trigger
                                payload = {
                                    'email': email_data,
                                    'trigger_type': 'email',
                                    'received_at': datetime.now(timezone.utc).isoformat()
                                }
                                
                                await self.trigger_service.fire_trigger(trigger.id, payload)
                                logger.info(f"Email trigger {trigger.id} fired for message from {email_data.get('from')}")
                                
                            # Delete message if configured
                            if delete_after_read:
                                mail.dele(i)
                                
                        except Exception as e:
                            logger.error(f"Error processing POP3 message {i}: {e}")
                            
                mail.quit()
                
            except Exception as e:
                logger.error(f"Error monitoring POP3 for trigger {trigger.id}: {e}")
                
            # Wait before next check
            await asyncio.sleep(check_interval)
            
    def _build_imap_search_criteria(self, config: Dict[str, Any]) -> str:
        """Build IMAP search criteria from trigger configuration"""
        criteria = []
        
        # Filter by sender
        if config.get('from_filter'):
            criteria.append(f'FROM "{config["from_filter"]}"')
            
        # Filter by subject
        if config.get('subject_filter'):
            criteria.append(f'SUBJECT "{config["subject_filter"]}"')
            
        # Filter by date (only new messages)
        if config.get('only_new', True):
            criteria.append('UNSEEN')
            
        # Default to all messages if no criteria
        if not criteria:
            criteria.append('ALL')
            
        return ' '.join(criteria)
        
    def _matches_criteria(self, message: email.message.Message, config: Dict[str, Any]) -> bool:
        """Check if email message matches trigger criteria"""
        
        # Check sender filter
        if config.get('from_filter'):
            from_address = message.get('From', '').lower()
            if config['from_filter'].lower() not in from_address:
                return False
                
        # Check subject filter  
        if config.get('subject_filter'):
            subject = message.get('Subject', '').lower()
            if config['subject_filter'].lower() not in subject:
                return False
                
        # Check body filter
        if config.get('body_filter'):
            body = self._get_email_body(message).lower()
            if config['body_filter'].lower() not in body:
                return False
                
        return True
        
    def _extract_email_data(self, message: email.message.Message) -> Dict[str, Any]:
        """Extract data from email message"""
        return {
            'from': message.get('From'),
            'to': message.get('To'),
            'cc': message.get('Cc'),
            'bcc': message.get('Bcc'),
            'subject': message.get('Subject'),
            'date': message.get('Date'),
            'message_id': message.get('Message-ID'),
            'body': self._get_email_body(message),
            'attachments': self._get_attachments(message)
        }
        
    def _get_email_body(self, message: email.message.Message) -> str:
        """Extract body text from email message"""
        body = ""
        
        if message.is_multipart():
            for part in message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode('utf-8')
                        break
                    except:
                        continue
        else:
            try:
                body = message.get_payload(decode=True).decode('utf-8')
            except:
                body = str(message.get_payload())
                
        return body
        
    def _get_attachments(self, message: email.message.Message) -> List[Dict[str, Any]]:
        """Extract attachment information from email message"""
        attachments = []
        
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_disposition() == 'attachment':
                    filename = part.get_filename()
                    if filename:
                        attachments.append({
                            'filename': filename,
                            'content_type': part.get_content_type(),
                            'size': len(part.get_payload(decode=True)) if part.get_payload(decode=True) else 0
                        })
                        
        return attachments
        
    async def process(self, context: TriggerExecutionContext) -> Dict[str, Any]:
        """Process email trigger execution"""
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
            logger.error(f"Failed to execute flow from email trigger {context.trigger.id}: {e}")
            raise
            
    def get_monitor_status(self, trigger_id: str) -> Dict[str, Any]:
        """Get monitoring status for a trigger"""
        if trigger_id not in self.monitors:
            return {'status': 'not_monitoring'}
            
        task = self.monitors[trigger_id]
        return {
            'status': 'monitoring' if not task.done() else 'stopped',
            'task_done': task.done(),
            'task_cancelled': task.cancelled() if hasattr(task, 'cancelled') else False
        }