"""
Processing API - Document Processing, Batch Operations, Queues, and Webhooks

Provides:
- Document processing (single documents, chunks, summaries, GraphRAG, STP)
- Batch processing (all buckets, specific buckets)
- Task management (background tasks)
- Queue operations
- MinIO bucket management
- Webhook handling for MinIO events
"""

from fastapi import FastAPI, Query
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import uuid
import logging

from models import ProcessRequest, EnhancedProcessRequest, BatchProcessRequest, BucketProcessRequest
from api.framework import APIResponse, api_response, QueueResponseBuilder
from config import config

logger = logging.getLogger(__name__)

# Global task storage for tracking background tasks
background_tasks_store = {}


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTaskManager:
    """Manages background processing tasks"""

    def __init__(self):
        self.tasks = {}
        self.task_results = {}

    def create_task(self, task_id: str, coro, task_type: str, metadata: Dict[str, Any] = None):
        """Create and store a background task"""
        task = asyncio.create_task(coro)

        self.tasks[task_id] = {
            "task": task,
            "task_type": task_type,
            "status": TaskStatus.PENDING,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "metadata": metadata or {},
            "error": None
        }

        task.add_done_callback(lambda t: self._task_completed(task_id, t))
        return task_id

    def _task_completed(self, task_id: str, task):
        """Handle task completion"""
        task_info = self.tasks.get(task_id)
        if not task_info:
            return

        task_info["completed_at"] = datetime.now().isoformat()

        try:
            result = task.result()
            task_info["status"] = TaskStatus.COMPLETED
            self.task_results[task_id] = result
            logger.info(f"✅ Background task {task_id} completed successfully")
        except Exception as e:
            task_info["status"] = TaskStatus.FAILED
            task_info["error"] = str(e)
            logger.error(f"❌ Background task {task_id} failed: {e}")

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status and result"""
        task_info = self.tasks.get(task_id)
        if not task_info:
            return {"error": "Task not found"}

        status = {
            "task_id": task_id,
            "task_type": task_info["task_type"],
            "status": task_info["status"],
            "created_at": task_info["created_at"],
            "started_at": task_info["started_at"],
            "completed_at": task_info["completed_at"],
            "metadata": task_info["metadata"]
        }

        if task_info["status"] == TaskStatus.COMPLETED and task_id in self.task_results:
            status["result"] = self.task_results[task_id]

        if task_info["status"] == TaskStatus.FAILED:
            status["error"] = task_info["error"]

        return status

    def mark_task_started(self, task_id: str):
        """Mark task as started"""
        if task_id in self.tasks:
            self.tasks[task_id]["status"] = TaskStatus.RUNNING
            self.tasks[task_id]["started_at"] = datetime.now().isoformat()

    def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Clean up old completed tasks"""
        from datetime import datetime, timedelta

        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        tasks_to_remove = []
        for task_id, task_info in self.tasks.items():
            if task_info["status"] in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if task_info.get("completed_at"):
                    try:
                        completed_time = datetime.fromisoformat(task_info["completed_at"])
                        if completed_time < cutoff_time:
                            tasks_to_remove.append(task_id)
                    except ValueError:
                        pass

        for task_id in tasks_to_remove:
            self.tasks.pop(task_id, None)
            self.task_results.pop(task_id, None)

        return len(tasks_to_remove)

    def get_all_tasks(self) -> Dict[str, Any]:
        """Get all tasks summary"""
        status_counts = {}
        for task_info in self.tasks.values():
            status = task_info["status"]
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_tasks": len(self.tasks),
            "status_breakdown": status_counts,
            "active_tasks": status_counts.get(TaskStatus.RUNNING, 0)
        }


# Global task manager
task_manager = BackgroundTaskManager()


async def background_document_processor(task_id: str, document_content: bytes, filename: str,
                                       bucket: str, include_chunking: bool, include_summarization: bool,
                                       include_graphrag: bool, include_stp: bool, get_services_func):
    """Background document processing task with STP support"""
    try:
        task_manager.mark_task_started(task_id)
        logger.info(f"🚀 Starting background processing for {filename}")

        from processors.pipeline import processor

        result = await processor.process_document(
            document_content, filename, bucket,
            include_chunking, include_summarization, include_graphrag, include_stp
        )

        logger.info(f"✅ Background processing completed for {filename}")
        return result

    except Exception as e:
        logger.error(f"❌ Background processing failed for {filename}: {e}")
        raise


async def background_batch_processor(task_id: str, batch_processor, skip_processed: bool,
                                   include_graphrag: bool, include_chunking: bool,
                                   include_summarization: bool, include_stp: bool,
                                   max_documents_per_bucket: Optional[int]):
    """Background batch processing task with STP support"""
    try:
        task_manager.mark_task_started(task_id)
        logger.info(f"🚀 Starting background batch processing")

        result = await batch_processor.process_all_buckets(
            skip_processed, include_graphrag, include_chunking,
            include_summarization, include_stp, max_documents_per_bucket
        )

        logger.info(f"✅ Background batch processing completed")
        return result

    except Exception as e:
        logger.error(f"❌ Background batch processing failed: {e}")
        raise


async def background_bucket_processor(task_id: str, batch_processor, bucket: str, skip_processed: bool,
                                    include_chunking: bool, include_summarization: bool,
                                    include_graphrag: bool, include_stp: bool, max_documents: Optional[int]):
    """Background bucket processing task with STP support"""
    try:
        task_manager.mark_task_started(task_id)
        logger.info(f"🚀 Starting background bucket processing for {bucket}")

        result = await batch_processor.process_bucket(
            bucket, skip_processed, include_graphrag,
            include_chunking, include_summarization, include_stp, max_documents
        )

        logger.info(f"✅ Background bucket processing completed for {bucket}")
        return result

    except Exception as e:
        logger.error(f"❌ Background bucket processing failed for {bucket}: {e}")
        raise


def setup_processing_routes(app: FastAPI, get_services_func, get_queue_func):
    """Setup all processing API routes"""

    # ============================================================================
    # DOCUMENT PROCESSING ROUTES
    # ============================================================================

    @app.post("/process/document")
    @api_response
    async def process_document(request: EnhancedProcessRequest, include_stp: bool = False):
        """Process a single document with background task and STP support"""

        # Validate configuration
        if not any([request.include_chunking, request.include_summarization, request.include_graphrag, include_stp]):
            APIResponse.error("At least one processing step must be enabled", 400)

        try:
            services = get_services_func()

            # Get document from MinIO
            document_content = services.minio.get_document(request.bucket, request.filename)

            # Create background task
            task_id = str(uuid.uuid4())
            task_manager.create_task(
                task_id,
                background_document_processor(
                    task_id, document_content, request.filename, request.bucket,
                    request.include_chunking, request.include_summarization,
                    request.include_graphrag, include_stp, get_services_func
                ),
                "document_processing",
                {
                    "filename": request.filename,
                    "bucket": request.bucket,
                    "processing_options": {
                        "include_chunking": request.include_chunking,
                        "include_summarization": request.include_summarization,
                        "include_graphrag": request.include_graphrag,
                        "include_stp": include_stp
                    }
                }
            )

            return APIResponse.success({
                "task_id": task_id,
                "message": f"Document processing started for {request.filename}",
                "status_endpoint": f"/tasks/{task_id}",
                "filename": request.filename,
                "bucket": request.bucket
            }, "Processing task created successfully")

        except Exception as e:
            APIResponse.error(f"Failed to start processing: {str(e)}", 500)

    @app.post("/process/chunks")
    @api_response
    async def process_chunks_only(request: ProcessRequest):
        """Process document for chunks only - background task"""
        enhanced_request = EnhancedProcessRequest(
            bucket=request.bucket,
            filename=request.filename,
            include_chunking=True,
            include_summarization=False,
            include_graphrag=False
        )
        return await process_document(enhanced_request, include_stp=False)

    @app.post("/process/summary")
    @api_response
    async def process_summary_only(request: ProcessRequest):
        """Process document for summary only - background task"""
        enhanced_request = EnhancedProcessRequest(
            bucket=request.bucket,
            filename=request.filename,
            include_chunking=False,
            include_summarization=True,
            include_graphrag=False
        )
        return await process_document(enhanced_request, include_stp=False)

    @app.post("/process/graphrag")
    @api_response
    async def process_graphrag_only(request: ProcessRequest):
        """Process document for GraphRAG only - background task"""
        enhanced_request = EnhancedProcessRequest(
            bucket=request.bucket,
            filename=request.filename,
            include_chunking=False,
            include_summarization=False,
            include_graphrag=True
        )
        return await process_document(enhanced_request, include_stp=False)

    @app.post("/process/stp")
    @api_response
    async def process_stp_only(request: ProcessRequest):
        """Process document for STP classification only - background task"""
        enhanced_request = EnhancedProcessRequest(
            bucket=request.bucket,
            filename=request.filename,
            include_chunking=False,
            include_summarization=False,
            include_graphrag=False
        )
        return await process_document(enhanced_request, include_stp=True)

    # ============================================================================
    # BATCH PROCESSING ROUTES
    # ============================================================================

    @app.post("/batch/process-all")
    @api_response
    async def batch_process_all(request: BatchProcessRequest, include_stp: bool = False):
        """Process all documents from all buckets - background task with STP support"""

        if not any([request.include_chunking, request.include_summarization, request.include_graphrag, include_stp]):
            APIResponse.error("At least one processing step must be enabled", 400)

        try:
            services = get_services_func()

            # Check if batch processor is available
            if not services.batch_processor:
                APIResponse.error("Batch processor service is not available. Check server logs for initialization errors.", 503)

            task_id = str(uuid.uuid4())
            task_manager.create_task(
                task_id,
                background_batch_processor(
                    task_id, services.batch_processor, request.skip_processed,
                    request.include_graphrag, request.include_chunking,
                    request.include_summarization, include_stp, request.max_documents_per_bucket
                ),
                "batch_processing_all",
                {
                    "processing_options": {
                        "skip_processed": request.skip_processed,
                        "include_chunking": request.include_chunking,
                        "include_summarization": request.include_summarization,
                        "include_graphrag": request.include_graphrag,
                        "include_stp": include_stp,
                        "max_documents_per_bucket": request.max_documents_per_bucket
                    }
                }
            )

            return APIResponse.success({
                "task_id": task_id,
                "message": "Batch processing started for all buckets",
                "status_endpoint": f"/tasks/{task_id}",
                "processing_options": {
                    "skip_processed": request.skip_processed,
                    "include_chunking": request.include_chunking,
                    "include_summarization": request.include_summarization,
                    "include_graphrag": request.include_graphrag,
                    "include_stp": include_stp
                }
            }, "Batch processing task created successfully")

        except Exception as e:
            APIResponse.error(f"Failed to start batch processing: {str(e)}", 500)

    @app.post("/batch/process-bucket")
    @api_response
    async def batch_process_bucket(request: BucketProcessRequest, include_stp: bool = False):
        """Process all documents in a specific bucket - background task with STP support"""

        if not any([request.include_chunking, request.include_summarization, request.include_graphrag, include_stp]):
            APIResponse.error("At least one processing step must be enabled", 400)

        try:
            services = get_services_func()

            # Check if batch processor is available
            if not services.batch_processor:
                APIResponse.error("Batch processor service is not available. Check server logs for initialization errors.", 503)

            task_id = str(uuid.uuid4())
            task_manager.create_task(
                task_id,
                background_bucket_processor(
                    task_id, services.batch_processor, request.bucket, request.skip_processed,
                    request.include_chunking, request.include_summarization,
                    request.include_graphrag, include_stp, request.max_documents
                ),
                "bucket_processing",
                {
                    "bucket": request.bucket,
                    "processing_options": {
                        "skip_processed": request.skip_processed,
                        "include_chunking": request.include_chunking,
                        "include_summarization": request.include_summarization,
                        "include_graphrag": request.include_graphrag,
                        "include_stp": include_stp,
                        "max_documents": request.max_documents
                    }
                }
            )

            return APIResponse.success({
                "task_id": task_id,
                "message": f"Bucket processing started for {request.bucket}",
                "status_endpoint": f"/tasks/{task_id}",
                "bucket": request.bucket,
                "processing_options": {
                    "skip_processed": request.skip_processed,
                    "include_chunking": request.include_chunking,
                    "include_summarization": request.include_summarization,
                    "include_graphrag": request.include_graphrag,
                    "include_stp": include_stp
                }
            }, "Bucket processing task created successfully")

        except Exception as e:
            APIResponse.error(f"Failed to start bucket processing: {str(e)}", 500)

    # ============================================================================
    # TASK MANAGEMENT ROUTES
    # ============================================================================

    @app.get("/tasks/{task_id}")
    @api_response
    async def get_task_status(task_id: str):
        """Get background task status and result"""
        try:
            task_status = task_manager.get_task_status(task_id)

            if "error" in task_status:
                APIResponse.error(task_status["error"], 404)

            return APIResponse.success(task_status, "Task status retrieved")

        except Exception as e:
            APIResponse.error(f"Failed to get task status: {str(e)}", 500)

    @app.get("/tasks")
    @api_response
    async def get_all_tasks():
        """Get all background tasks summary"""
        try:
            tasks_summary = task_manager.get_all_tasks()
            return APIResponse.success(tasks_summary, "All tasks summary retrieved")

        except Exception as e:
            APIResponse.error(f"Failed to get tasks summary: {str(e)}", 500)

    @app.delete("/tasks/cleanup")
    @api_response
    async def cleanup_completed_tasks(max_age_hours: int = 24):
        """Clean up old completed tasks"""
        try:
            cleaned_count = task_manager.cleanup_completed_tasks(max_age_hours)
            return APIResponse.success({
                "cleaned_tasks": cleaned_count,
                "max_age_hours": max_age_hours,
                "remaining_tasks": task_manager.get_all_tasks()
            }, f"Cleaned up {cleaned_count} old tasks")

        except Exception as e:
            APIResponse.error(f"Failed to cleanup tasks: {str(e)}", 500)

    # ============================================================================
    # QUEUE PROCESSING ROUTES
    # ============================================================================

    @app.post("/queue/add-task")
    @api_response
    async def add_task_to_queue(request: ProcessRequest):
        """Add document processing task to queue"""

        try:
            queue = get_queue_func()
            if not queue:
                APIResponse.error("Processing queue unavailable", 503)

            task_id = await queue.add_task(request.bucket, request.filename, request.file_path)

            if task_id:
                return APIResponse.success({
                    "task_id": task_id,
                    "message": f"Document {request.filename} queued for processing",
                    "queue_status": queue.get_queue_status()
                })
            else:
                return APIResponse.success({
                    "task_id": None,
                    "message": f"Document {request.filename} already processed or queued",
                    "queue_status": queue.get_queue_status()
                })

        except Exception as e:
            APIResponse.error(f"Queue operation failed: {str(e)}", 500)

    @app.get("/queue/status")
    @api_response
    async def get_queue_status():
        """Get processing queue status"""
        try:
            queue = get_queue_func()
            return APIResponse.success(QueueResponseBuilder.build_queue_status(queue))
        except Exception as e:
            APIResponse.error(f"Queue status failed: {str(e)}", 500)

    @app.get("/queue/task/{task_id}")
    @api_response
    async def get_queue_task_status(task_id: str):
        """Get status of specific queue task"""
        try:
            queue = get_queue_func()
            return QueueResponseBuilder.build_task_response(task_id, queue)
        except Exception as e:
            APIResponse.error(f"Task status failed: {str(e)}", 500)

    @app.post("/queue/control")
    @api_response
    async def control_queue(action: str):
        """Control processing queue (start/stop/clear)"""

        try:
            queue = get_queue_func()
            if not queue:
                APIResponse.error("Processing queue unavailable", 503)

            action = action.lower()

            if action == "start":
                if queue.is_processing:
                    return APIResponse.success(queue.get_queue_status(), "Queue already running")

                await queue.start_processing()
                return APIResponse.success(queue.get_queue_status(), "Queue started")

            elif action == "stop":
                if not queue.is_processing:
                    return APIResponse.success(queue.get_queue_status(), "Queue already stopped")

                await queue.stop_processing()
                return APIResponse.success(queue.get_queue_status(), "Queue stopped")

            elif action == "clear":
                result = await queue.clear_completed_tasks()
                return APIResponse.success({
                    "clear_result": result,
                    "queue_status": queue.get_queue_status()
                }, "Completed tasks cleared")

            else:
                APIResponse.error(f"Invalid action: {action}. Use 'start', 'stop', or 'clear'", 400)

        except Exception as e:
            APIResponse.error(f"Queue control failed: {str(e)}", 500)

    # ============================================================================
    # MINIO & BUCKET ROUTES
    # ============================================================================

    @app.get("/minio/buckets")
    @api_response
    async def list_buckets():
        """List all MinIO buckets"""

        try:
            services = get_services_func()
            minio_service = services.minio
            all_buckets = minio_service.list_buckets()

            bucket_info = []
            for bucket in all_buckets:
                is_processable = config.is_bucket_processable(bucket)
                object_count = 0

                if is_processable:
                    try:
                        objects = minio_service.list_objects(bucket)
                        document_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']
                        object_count = sum(1 for obj in objects
                                         if any(obj.lower().endswith(ext) for ext in document_extensions))
                    except Exception as e:
                        object_count = "error"

                bucket_info.append({
                    "bucket_name": bucket,
                    "is_processable": is_processable,
                    "document_count": object_count
                })

            processable_buckets = [b["bucket_name"] for b in bucket_info if b["is_processable"]]

            return APIResponse.success({
                "all_buckets": bucket_info,
                "processable_buckets": processable_buckets,
                "total_buckets": len(all_buckets),
                "processable_count": len(processable_buckets)
            })

        except Exception as e:
            APIResponse.error(f"Bucket listing failed: {str(e)}", 500)

    @app.get("/minio/bucket/{bucket_name}/objects")
    @api_response
    async def list_bucket_objects(bucket_name: str, limit: int = 100, offset: int = 0):
        """List objects in specific bucket"""

        if not config.is_bucket_processable(bucket_name):
            APIResponse.error(f"Bucket {bucket_name} is not processable", 400)

        try:
            services = get_services_func()
            minio_service = services.minio
            objects = minio_service.list_objects(bucket_name)

            document_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']
            documents = [obj for obj in objects
                        if any(obj.lower().endswith(ext) for ext in document_extensions)]

            total_documents = len(documents)
            paginated_documents = documents[offset:offset + limit]

            return APIResponse.success({
                "bucket_name": bucket_name,
                "documents": paginated_documents,
                "total_documents": total_documents,
                "returned_count": len(paginated_documents),
                "pagination": {
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_documents
                }
            })

        except Exception as e:
            APIResponse.error(f"Object listing failed: {str(e)}", 500)

    # ============================================================================
    # WEBHOOK ROUTES
    # ============================================================================

    @app.post("/webhook/minio-events")
    @api_response
    async def handle_minio_events(request: Dict[str, Any], enable_stp: bool = False):
        """Handle MinIO bucket events for automatic processing with STP support"""

        try:
            # Check if webhook is enabled
            from api.health import is_webhook_enabled
            if not is_webhook_enabled():
                logger.info("🚫 Webhook processing is disabled - ignoring event")
                return APIResponse.success({
                    "processed_files": [],
                    "webhook_enabled": False,
                    "message": "Webhook processing is disabled"
                }, "Webhook is disabled")

            queue = get_queue_func()
            if not queue:
                APIResponse.error("Processing queue unavailable", 503)

            import json
            import urllib.parse

            processed_files = []

            for record in request.get("Records", []):
                try:
                    s3_info = record.get("s3", {})
                    bucket = s3_info.get("bucket", {}).get("name", "")
                    object_key_encoded = s3_info.get("object", {}).get("key", "")
                    event_name = record.get("eventName", "")

                    object_key = urllib.parse.unquote_plus(object_key_encoded)

                    if not event_name.startswith("s3:ObjectCreated:"):
                        continue

                    if not bucket or not object_key:
                        continue

                    if not config.is_bucket_processable(bucket):
                        continue

                    document_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']
                    if not any(object_key.lower().endswith(ext) for ext in document_extensions):
                        continue

                    filename = object_key.split('/')[-1] if '/' in object_key else object_key

                    # Add to processing queue
                    task_id = await queue.add_task(bucket, filename, object_key)

                    if enable_stp and task_id:
                        logger.info(f"🎯 STP processing enabled for webhook file: {filename}")

                    processed_files.append({
                        "bucket": bucket,
                        "filename": filename,
                        "object_key": object_key,
                        "task_id": task_id,
                        "status": "queued" if task_id else "skipped",
                        "stp_enabled": enable_stp
                    })

                except Exception as e:
                    logger.error(f"Error processing event record: {e}")
                    continue

            return APIResponse.success({
                "processed_files": processed_files,
                "queue_status": queue.get_queue_status(),
                "stp_enabled": enable_stp
            }, f"Processed {len(processed_files)} files from event")

        except Exception as e:
            APIResponse.error(f"Webhook processing failed: {str(e)}", 500)

    return app
