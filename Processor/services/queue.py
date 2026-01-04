import asyncio
import logging
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from models import ProcessingTask, ProcessingStatus

logger = logging.getLogger(__name__)


class ProcessingQueue:
    """Simple auto-start processing queue"""
    
    def __init__(self, batch_processor=None, max_concurrent_tasks: int = 3):
        self.batch_processor = batch_processor
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, ProcessingTask] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.is_processing = False
        self._processing_task = None
        
    async def add_task(self, bucket: str, filename: str, file_path: str = None) -> Optional[str]:
        """Add task and auto-start processing"""
        
        # Check if already exists
        task_key = f"{bucket}:{filename}"
        existing_task = self._find_existing_task(task_key)
        if existing_task:
            return existing_task.task_id if existing_task.status == ProcessingStatus.PENDING else None
        
        # Create new task
        task_id = str(uuid.uuid4())
        task = ProcessingTask(
            task_id=task_id,
            bucket=bucket,
            filename=filename,
            file_path=file_path or filename,
            status=ProcessingStatus.PENDING,
            created_at=datetime.now()
        )
        
        self.tasks[task_id] = task
        logger.info(f"Added task {task_id} for {filename} to queue")
        
        # Auto-start if not processing
        if not self.is_processing and self.batch_processor:
            asyncio.create_task(self.start_processing())
        
        return task_id
    
    def _find_existing_task(self, task_key: str) -> Optional[ProcessingTask]:
        """Find existing task"""
        for task in self.tasks.values():
            if f"{task.bucket}:{task.filename}" == task_key:
                if task.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]:
                    return task
        return None
    
    async def start_processing(self):
        """Start processing queue"""
        if self.is_processing or not self.batch_processor:
            return
        
        pending_tasks = [task for task in self.tasks.values() if task.status == ProcessingStatus.PENDING]
        if not pending_tasks:
            return
        
        self.is_processing = True
        self._processing_task = asyncio.create_task(self._process_queue())
        logger.info(f"Started processing queue with {len(pending_tasks)} tasks")
    
    async def stop_processing(self):
        """Stop processing"""
        if not self.is_processing:
            return
        
        self.is_processing = False
        if self._processing_task:
            self._processing_task.cancel()
        
        for active_task in self.active_tasks.values():
            active_task.cancel()
        self.active_tasks.clear()
        logger.info("Stopped processing queue")
    
    async def _process_queue(self):
        """Main processing loop - FIFO"""
        try:
            while self.is_processing:
                # Get pending tasks (FIFO order)
                pending_tasks = [t for t in self.tasks.values() if t.status == ProcessingStatus.PENDING]
                pending_tasks.sort(key=lambda t: t.created_at)
                
                # Start new tasks
                available_slots = self.max_concurrent_tasks - len(self.active_tasks)
                if available_slots > 0 and pending_tasks:
                    for task in pending_tasks[:available_slots]:
                        await self._start_task(task)
                
                # Clean up completed tasks
                await self._cleanup_completed_tasks()
                
                # Stop if no more work
                remaining = [t for t in self.tasks.values() if t.status in [ProcessingStatus.PENDING, ProcessingStatus.PROCESSING]]
                if not remaining:
                    self.is_processing = False
                    break
                
                await asyncio.sleep(2)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Queue processing error: {e}")
        finally:
            self.is_processing = False
    
    async def _start_task(self, task: ProcessingTask):
        """Start single task"""
        task.status = ProcessingStatus.PROCESSING
        task.started_at = datetime.now()
        
        async_task = asyncio.create_task(self._process_single_task(task))
        self.active_tasks[task.task_id] = async_task
        logger.info(f"Started processing {task.filename}")
    
    async def _process_single_task(self, task: ProcessingTask):
        """Process single task"""
        try:
            result = await self.batch_processor.process_specific_documents([{
                "bucket": task.bucket,
                "filename": task.filename
            }])
            
            task.result = result
            task.status = ProcessingStatus.COMPLETED
            task.completed_at = datetime.now()
            logger.info(f"Completed {task.filename}")
            
        except Exception as e:
            task.error_message = str(e)
            task.attempts += 1
            
            if task.attempts < task.max_attempts:
                task.status = ProcessingStatus.RETRYING
            else:
                task.status = ProcessingStatus.FAILED
                task.completed_at = datetime.now()
            logger.error(f"Failed {task.filename}: {e}")
    
    async def _cleanup_completed_tasks(self):
        """Clean up completed tasks"""
        completed_task_ids = [task_id for task_id, async_task in self.active_tasks.items() if async_task.done()]
        for task_id in completed_task_ids:
            del self.active_tasks[task_id]
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "bucket": task.bucket,
            "filename": task.filename,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message
        }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        status_counts = {}
        for task in self.tasks.values():
            status = task.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "is_processing": self.is_processing,
            "total_tasks": len(self.tasks),
            "pending_tasks": status_counts.get("pending", 0),
            "processing_tasks": status_counts.get("processing", 0),
            "completed_tasks": status_counts.get("completed", 0),
            "failed_tasks": status_counts.get("failed", 0),
            "batch_processor_available": self.batch_processor is not None
        }
    
    async def clear_completed_tasks(self) -> Dict[str, Any]:
        """Clear completed tasks"""
        initial_count = len(self.tasks)
        active_statuses = {ProcessingStatus.PENDING, ProcessingStatus.PROCESSING, ProcessingStatus.RETRYING}
        self.tasks = {task_id: task for task_id, task in self.tasks.items() if task.status in active_statuses}
        cleared_count = initial_count - len(self.tasks)
        return {"cleared_count": cleared_count, "remaining_count": len(self.tasks)}


# Factory function
def create_processing_queue(batch_processor=None, max_concurrent: int = 3) -> ProcessingQueue:
    """Create processing queue"""
    return ProcessingQueue(batch_processor, max_concurrent)


# Global instance
processing_queue: Optional[ProcessingQueue] = None

def get_processing_queue() -> Optional[ProcessingQueue]:
    return processing_queue

def initialize_queue(batch_processor=None, max_concurrent: int = 3) -> ProcessingQueue:
    global processing_queue
    if not processing_queue:
        processing_queue = create_processing_queue(batch_processor, max_concurrent)
        logger.info("Processing queue initialized with auto-start")
    return processing_queue