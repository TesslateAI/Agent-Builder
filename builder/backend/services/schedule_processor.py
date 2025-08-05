"""
Schedule Processor - Handles scheduled triggers
Uses APScheduler for cron and interval-based scheduling
"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.job import Job
import pytz
from .trigger_service import TriggerProcessor, TriggerExecutionContext
from models import Triggers

logger = logging.getLogger("ScheduleProcessor")

class ScheduleProcessor(TriggerProcessor):
    """Handles scheduled triggers using APScheduler"""
    
    def __init__(self, trigger_service):
        super().__init__(trigger_service)
        
        # Configure APScheduler
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': AsyncIOExecutor()
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=pytz.UTC
        )
        
        self.jobs: Dict[str, str] = {}  # trigger_id -> job_id mapping
        
    async def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Schedule processor started")
            
    async def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Schedule processor stopped")
        
    async def setup(self, trigger: Triggers) -> None:
        """Setup scheduled job for the trigger"""
        if trigger.type != 'schedule':
            return
            
        config = trigger.config
        schedule_type = config.get('scheduleType')
        
        if not schedule_type:
            raise ValueError("Schedule type not specified")
            
        # Remove existing job if it exists
        if trigger.id in self.jobs:
            job_id = self.jobs[trigger.id]
            try:
                self.scheduler.remove_job(job_id)
            except Exception:
                pass  # Job might not exist
                
        # Parse timezone
        timezone_str = config.get('timezone', 'UTC')
        try:
            tz = pytz.timezone(timezone_str)
        except pytz.exceptions.UnknownTimeZoneError:
            logger.warning(f"Unknown timezone {timezone_str}, using UTC")
            tz = pytz.UTC
            
        # Create appropriate trigger
        job_trigger = None
        job_id = f"trigger_{trigger.id}"
        
        if schedule_type == 'cron':
            cron_expression = config.get('cronExpression')
            if not cron_expression:
                raise ValueError("Cron expression not specified")
                
            # Parse cron expression (format: "minute hour day month day_of_week")
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid cron expression: {cron_expression}")
                
            minute, hour, day, month, day_of_week = parts
            
            job_trigger = CronTrigger(
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                timezone=tz
            )
            
        elif schedule_type == 'interval':
            interval_config = config.get('interval')
            if not interval_config:
                raise ValueError("Interval configuration not specified")
                
            value = interval_config.get('value')
            unit = interval_config.get('unit')
            
            if not value or not unit:
                raise ValueError("Interval value and unit must be specified")
                
            kwargs = {unit: value}
            job_trigger = IntervalTrigger(timezone=tz, **kwargs)
            
        elif schedule_type == 'once':
            one_time = config.get('oneTime')
            if not one_time:
                raise ValueError("One-time date not specified")
                
            # Parse datetime
            if isinstance(one_time, str):
                run_date = datetime.fromisoformat(one_time.replace('Z', '+00:00'))
            else:
                run_date = one_time
                
            job_trigger = DateTrigger(run_date=run_date, timezone=tz)
            
        else:
            raise ValueError(f"Unsupported schedule type: {schedule_type}")
            
        # Add start/end date constraints if specified
        start_date = config.get('startDate')
        end_date = config.get('endDate')
        
        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            job_trigger.start_date = start_date
            
        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            job_trigger.end_date = end_date
            
        # Add job to scheduler
        job = self.scheduler.add_job(
            func=self._execute_scheduled_trigger,
            trigger=job_trigger,
            args=[trigger.id],
            id=job_id,
            name=f"Trigger: {trigger.name}",
            replace_existing=True
        )
        
        self.jobs[trigger.id] = job_id
        
        # Update next run time in database
        next_run = job.next_run_time
        if next_run:
            from database import LocalSession
            with LocalSession() as session:
                db_trigger = session.query(Triggers).filter(Triggers.id == trigger.id).first()
                if db_trigger:
                    db_trigger.next_run_at = next_run
                    session.commit()
        
        logger.info(f"Scheduled trigger {trigger.id} with job {job_id}, next run: {next_run}")
        
    async def teardown(self, trigger: Triggers) -> None:
        """Remove scheduled job for the trigger"""
        if trigger.type != 'schedule':
            return
            
        if trigger.id in self.jobs:
            job_id = self.jobs[trigger.id]
            try:
                self.scheduler.remove_job(job_id)
                del self.jobs[trigger.id]
                logger.info(f"Removed scheduled job {job_id} for trigger {trigger.id}")
            except Exception as e:
                logger.warning(f"Failed to remove job {job_id}: {e}")
                
    async def _execute_scheduled_trigger(self, trigger_id: str):
        """Execute a scheduled trigger"""
        try:
            payload = {
                'schedule': {
                    'triggered_at': datetime.now(timezone.utc).isoformat(),
                    'trigger_type': 'scheduled'
                }
            }
            
            # Fire the trigger
            await self.trigger_service.fire_trigger(trigger_id, payload)
            
            # Update next run time in database
            job_id = self.jobs.get(trigger_id)
            if job_id:
                try:
                    job = self.scheduler.get_job(job_id)
                    if job and job.next_run_time:
                        from database import LocalSession
                        with LocalSession() as session:
                            trigger = session.query(Triggers).filter(Triggers.id == trigger_id).first()
                            if trigger:
                                trigger.next_run_at = job.next_run_time
                                session.commit()
                except Exception as e:
                    logger.warning(f"Failed to update next run time for trigger {trigger_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to execute scheduled trigger {trigger_id}: {e}", exc_info=True)
            
    async def process(self, context: TriggerExecutionContext) -> Dict[str, Any]:
        """Process scheduled trigger execution"""
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
            logger.error(f"Failed to execute flow from scheduled trigger {context.trigger.id}: {e}")
            raise
            
    def get_next_runs(self, trigger_id: str, count: int = 10) -> List[datetime]:
        """Get next scheduled runs for a trigger"""
        job_id = self.jobs.get(trigger_id)
        if not job_id:
            return []
            
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return []
                
            # Get next run times
            next_runs = []
            current_time = datetime.now(pytz.UTC)
            
            # For cron jobs, calculate next runs
            if hasattr(job.trigger, 'get_next_fire_time'):
                next_time = current_time
                for _ in range(count):
                    next_time = job.trigger.get_next_fire_time(next_time, next_time)
                    if next_time:
                        next_runs.append(next_time)
                        from datetime import timedelta
                        next_time = next_time + timedelta(seconds=1)  # Avoid infinite loop
                    else:
                        break
                        
            return next_runs
            
        except Exception as e:
            logger.error(f"Failed to get next runs for trigger {trigger_id}: {e}")
            return []
            
    def get_job_info(self, trigger_id: str) -> Dict[str, Any]:
        """Get job information for a trigger"""
        job_id = self.jobs.get(trigger_id)
        if not job_id:
            return {}
            
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                return {}
                
            return {
                'job_id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger_type': type(job.trigger).__name__,
                'trigger_info': str(job.trigger)
            }
            
        except Exception as e:
            logger.error(f"Failed to get job info for trigger {trigger_id}: {e}")
            return {}