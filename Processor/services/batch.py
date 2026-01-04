import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import config
from storage.database import tracker

logger = logging.getLogger(__name__)


class AsyncBatchProcessor:
    """Enhanced async batch document processor with STP support and config-aware concurrency"""
    
    def __init__(self, max_concurrent_tasks: int = None):
        if max_concurrent_tasks is None:
            max_concurrent_tasks = config.get('processing.max_concurrent_tasks', 3)
        
        self.max_concurrent_tasks = max_concurrent_tasks
        logger.info(f"AsyncBatchProcessor initialized with max_concurrent_tasks={self.max_concurrent_tasks}")
        
        self.stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None
        }
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="batch_worker")
    
    async def process_all_buckets(self, skip_processed: bool = True,
                                 include_graphrag: bool = True, include_chunking: bool = True,
                                 include_summarization: bool = True, include_stp: bool = False,
                                 max_documents_per_bucket: Optional[int] = None) -> Dict[str, Any]:
        """Process all documents from all processable buckets with STP support"""
        
        self.stats["start_time"] = datetime.now()
        
        logger.info("🚀 Starting async batch processing of all buckets")
        logger.info(f"📋 Configuration: chunking={include_chunking}, summarization={include_summarization}, graphrag={include_graphrag}, stp={include_stp}")
        logger.info(f"⚙️ Concurrency limit: {self.max_concurrent_tasks} tasks")
        
        try:
            processable_buckets = config.get('minio.processable_buckets', [])
            logger.info(f"📦 Processing {len(processable_buckets)} buckets: {processable_buckets}")
            
            bucket_tasks = []
            bucket_concurrency = min(self.max_concurrent_tasks, len(processable_buckets))
            semaphore = asyncio.Semaphore(bucket_concurrency)
            
            logger.info(f"🔧 Using bucket concurrency limit: {bucket_concurrency}")
            
            for bucket in processable_buckets:
                task = self._process_bucket_with_semaphore(
                    semaphore, bucket, skip_processed, include_graphrag, 
                    include_chunking, include_summarization, include_stp, max_documents_per_bucket
                )
                bucket_tasks.append(task)
            
            bucket_results_list = await asyncio.gather(*bucket_tasks, return_exceptions=True)
            
            bucket_results = {}
            for i, result in enumerate(bucket_results_list):
                bucket_name = processable_buckets[i]
                if isinstance(result, Exception):
                    logger.error(f"❌ Bucket {bucket_name} processing failed: {result}")
                    bucket_results[bucket_name] = {
                        "bucket_name": bucket_name,
                        "documents_processed": 0,
                        "successful_documents": 0,
                        "failed_documents": 0,
                        "processing_errors": [{"bucket_error": str(result)}],
                        "document_results": []
                    }
                else:
                    bucket_results[bucket_name] = result
                    
                    self.stats["total_processed"] += result["documents_processed"]
                    self.stats["successful"] += result["successful_documents"]
                    self.stats["failed"] += result["failed_documents"]
            
            self.stats["end_time"] = datetime.now()
            duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
            
            final_stats = self._build_final_stats(bucket_results, duration)
            
            logger.info(f"🎉 Async batch processing completed: {self.stats['successful']}/{self.stats['total_processed']} successful")
            
            return {
                "status": "completed",
                "message": "Async batch processing completed successfully",
                "bucket_results": bucket_results,
                "final_statistics": final_stats,
                "processing_configuration": {
                    "skip_processed": skip_processed,
                    "include_chunking": include_chunking,
                    "include_summarization": include_summarization,
                    "include_graphrag": include_graphrag,
                    "include_stp": include_stp,
                    "max_concurrent_tasks": self.max_concurrent_tasks
                }
            }
            
        except Exception as e:
            logger.error(f"💥 Async batch processing failed: {e}")
            self.stats["end_time"] = datetime.now()
            
            return {
                "status": "failed",
                "message": f"Async batch processing failed: {str(e)}",
                "error": str(e),
                "partial_results": bucket_results if 'bucket_results' in locals() else {}
            }
    
    async def _process_bucket_with_semaphore(self, semaphore: asyncio.Semaphore, bucket: str, 
                                           skip_processed: bool, include_graphrag: bool, 
                                           include_chunking: bool, include_summarization: bool,
                                           include_stp: bool, max_documents: Optional[int]) -> Dict[str, Any]:
        """Process bucket with semaphore for concurrency control"""
        async with semaphore:
            return await self.process_bucket(
                bucket, skip_processed, include_graphrag, 
                include_chunking, include_summarization, include_stp, max_documents
            )
    
    async def process_bucket(self, bucket: str, skip_processed: bool = True,
                           include_graphrag: bool = True, include_chunking: bool = True,
                           include_summarization: bool = True, include_stp: bool = False,
                           max_documents: Optional[int] = None) -> Dict[str, Any]:
        """Process all documents in a specific bucket with STP support"""
        
        logger.info(f"📂 Starting async bucket processing: {bucket}")
        logger.info(f"⚙️ Document concurrency limit: {self.max_concurrent_tasks}")
        
        bucket_stats = {
            "bucket_name": bucket,
            "documents_processed": 0,
            "successful_documents": 0,
            "failed_documents": 0,
            "processing_errors": [],
            "document_results": []
        }
        
        try:
            if not config.is_bucket_processable(bucket):
                raise Exception(f"Bucket {bucket} is not processable")
            
            minio_service = await self._get_minio_service_async()
            if not minio_service:
                raise Exception("MinIO service not available")
            
            objects = await self._run_in_executor(minio_service.list_objects, bucket)
            logger.info(f"📄 Found {len(objects)} objects in bucket")
            
            documents = self._filter_documents(objects)
            logger.info(f"📋 Found {len(documents)} document files in bucket {bucket}")
            
            if max_documents and len(documents) > max_documents:
                documents = documents[:max_documents]
                logger.info(f"🔢 Limited to {max_documents} documents")
            
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
            
            document_tasks = []
            for i, file_path in enumerate(documents):
                task = self._process_single_document_async(
                    semaphore, file_path, bucket, skip_processed, 
                    include_chunking, include_summarization, include_graphrag, include_stp,
                    i + 1, len(documents)
                )
                document_tasks.append(task)
            
            document_results = await asyncio.gather(*document_tasks, return_exceptions=True)
            
            for i, result in enumerate(document_results):
                filename = documents[i].split('/')[-1] if '/' in documents[i] else documents[i]
                
                if isinstance(result, Exception):
                    bucket_stats["failed_documents"] += 1
                    bucket_stats["documents_processed"] += 1
                    bucket_stats["processing_errors"].append({
                        "document": filename,
                        "error": str(result)
                    })
                    logger.error(f"💥 {filename} processing error: {result}")
                elif result is None:
                    logger.info(f"⏭️ {filename} skipped - already processed")
                else:
                    bucket_stats["document_results"].append(result)
                    bucket_stats["documents_processed"] += 1
                    
                    if result.get("overall_status") in ["success", "partial_success"]:
                        bucket_stats["successful_documents"] += 1
                        logger.info(f"✅ {filename} processed successfully")
                    else:
                        bucket_stats["failed_documents"] += 1
                        logger.warning(f"⚠️ {filename} processing failed: {result.get('message', 'Unknown error')}")
            
            success_rate = (bucket_stats["successful_documents"] / bucket_stats["documents_processed"]) * 100 if bucket_stats["documents_processed"] > 0 else 0
            logger.info(f"🏁 Bucket {bucket} async processing completed: {bucket_stats['successful_documents']}/{bucket_stats['documents_processed']} successful ({success_rate:.1f}%)")
            
            return bucket_stats
            
        except Exception as e:
            logger.error(f"💥 Error processing bucket {bucket}: {e}")
            bucket_stats["processing_errors"].append({"bucket_error": str(e)})
            return bucket_stats
    
    async def _process_single_document_async(self, semaphore: asyncio.Semaphore, file_path: str, 
                                           bucket: str, skip_processed: bool, include_chunking: bool, 
                                           include_summarization: bool, include_graphrag: bool, include_stp: bool,
                                           doc_num: int, total_docs: int):
        """Process single document with semaphore control and STP support"""
        async with semaphore:
            filename = file_path.split('/')[-1] if '/' in file_path else file_path
            logger.info(f"📝 Processing {doc_num}/{total_docs}: {filename}")
            
            if skip_processed:
                is_processed = await self._is_document_processed_async(
                    filename, bucket, include_chunking, include_summarization, include_graphrag, include_stp
                )
                if is_processed:
                    logger.info(f"⏭️ Skipping {filename} - already processed")
                    return None
            
            try:
                minio_service = await self._get_minio_service_async()
                document_content = await self._run_in_executor(
                    minio_service.get_document, bucket, file_path
                )
                
                from processors.pipeline import processor
                
                result = await processor.process_document(
                    document_content, filename, bucket,
                    include_chunking, include_summarization, include_graphrag, include_stp
                )
                
                return result
                
            except Exception as e:
                logger.error(f"💥 {filename} processing error: {e}")
                raise e
    
    async def process_specific_documents(self, document_list: List[Dict[str, str]],
                                       include_graphrag: bool = True, include_chunking: bool = True,
                                       include_summarization: bool = True, include_stp: bool = False) -> Dict[str, Any]:
        """Process specific documents from list with STP support"""
        
        logger.info(f"📋 Processing {len(document_list)} specific documents async")
        logger.info(f"⚙️ Concurrency limit: {self.max_concurrent_tasks}")
        
        successful = 0
        failed = 0
        
        minio_service = await self._get_minio_service_async()
        if not minio_service:
            return {
                "status": "failed",
                "message": "MinIO service not available",
                "total_documents": len(document_list),
                "successful_documents": 0,
                "failed_documents": len(document_list),
                "results": []
            }
        
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)
        
        document_tasks = []
        for i, doc_info in enumerate(document_list):
            task = self._process_specific_document_async(
                semaphore, doc_info, minio_service, 
                include_chunking, include_summarization, include_graphrag, include_stp,
                i + 1, len(document_list)
            )
            document_tasks.append(task)
        
        results = await asyncio.gather(*document_tasks, return_exceptions=True)
        
        final_results = []
        for i, result in enumerate(results):
            doc_info = document_list[i]
            filename = doc_info.get("filename", "unknown")
            
            if isinstance(result, Exception):
                logger.error(f"💥 Error processing {filename}: {result}")
                final_results.append({
                    "doc_name": filename,
                    "bucket_source": doc_info.get("bucket"),
                    "overall_status": "failed",
                    "error": str(result)
                })
                failed += 1
            else:
                final_results.append(result)
                if result.get("overall_status") in ["success", "partial_success"]:
                    successful += 1
                    logger.info(f"✅ {filename} processed successfully")
                else:
                    failed += 1
                    logger.warning(f"⚠️ {filename} processing failed")
        
        return {
            "status": "completed",
            "message": f"Processed {len(document_list)} specific documents async",
            "total_documents": len(document_list),
            "successful_documents": successful,
            "failed_documents": failed,
            "success_rate": f"{(successful/len(document_list))*100:.1f}%" if document_list else "0%",
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "results": final_results
        }
    
    async def _process_specific_document_async(self, semaphore: asyncio.Semaphore, doc_info: Dict[str, str],
                                             minio_service, include_chunking: bool, include_summarization: bool,
                                             include_graphrag: bool, include_stp: bool, doc_num: int, total_docs: int):
        """Process specific document with semaphore control and STP support"""
        async with semaphore:
            bucket = doc_info.get("bucket")
            file_identifier = doc_info.get("filename")
            
            if not bucket or not file_identifier:
                raise ValueError(f"Invalid document info: {doc_info}")
            
            filename = file_identifier.split('/')[-1] if '/' in file_identifier else file_identifier
            logger.info(f"📝 Processing {doc_num}/{total_docs}: {filename} from {bucket}")
            
            document_content = await self._run_in_executor(
                minio_service.get_document, bucket, file_identifier
            )
            
            from processors.pipeline import processor
            
            result = await processor.process_document(
                document_content, filename, bucket,
                include_chunking, include_summarization, include_graphrag, include_stp
            )
            
            return result
    
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking function in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    async def _get_minio_service_async(self):
        """Get MinIO service instance - async version"""
        return await self._run_in_executor(self._get_minio_service_sync)
    
    def _get_minio_service_sync(self):
        """Get MinIO service instance - sync version"""
        try:
            from services.manager import service_manager
            if service_manager.is_service_available('minio'):
                return service_manager.get_service('minio')
        except Exception:
            pass
        
        try:
            from inputs import get_minio_input
            return get_minio_input()
        except Exception:
            pass
        
        return None
    
    def _filter_documents(self, objects: List[str]) -> List[str]:
        """Filter objects to include only document files"""
        document_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']
        
        documents = []
        for obj_path in objects:
            if any(obj_path.lower().endswith(ext) for ext in document_extensions):
                documents.append(obj_path)
        
        return documents
    
    async def _is_document_processed_async(self, filename: str, bucket: str,
                                         include_chunking: bool, include_summarization: bool,
                                         include_graphrag: bool, include_stp: bool) -> bool:
        """Check if document already processed with current configuration including STP"""
        try:
            status = tracker.get_status(filename, bucket)
            
            if status.get("status") == "not_found":
                return False
            
            chunks_done = status.get("chunks_done", False)
            summary_done = status.get("summary_done", False)
            graphrag_done = status.get("graphrag_done", False)
            stp_done = status.get("stp_done", False)
            
            processes_needed = []
            processes_done = []
            
            if include_chunking:
                processes_needed.append("chunks")
                if chunks_done:
                    processes_done.append("chunks")
            
            if include_summarization:
                processes_needed.append("summary")
                if summary_done:
                    processes_done.append("summary")
            
            if include_graphrag:
                processes_needed.append("graphrag")
                if graphrag_done:
                    processes_done.append("graphrag")
            
            if include_stp:
                processes_needed.append("stp")
                if stp_done:
                    processes_done.append("stp")
            
            return len(processes_done) == len(processes_needed) and len(processes_needed) > 0
            
        except Exception as e:
            logger.error(f"❌ Error checking document status for {filename}: {e}")
            return False
    
    def _build_final_stats(self, bucket_results: Dict[str, Any], duration_seconds: float) -> Dict[str, Any]:
        """Build final processing statistics"""
        
        total_docs = sum(r["documents_processed"] for r in bucket_results.values())
        successful_docs = sum(r["successful_documents"] for r in bucket_results.values())
        failed_docs = sum(r["failed_documents"] for r in bucket_results.values())
        
        return {
            "total_documents": total_docs,
            "successful_documents": successful_docs,
            "failed_documents": failed_docs,
            "success_rate": f"{(successful_docs/total_docs)*100:.1f}%" if total_docs > 0 else "0%",
            "processing_time_seconds": duration_seconds,
            "processing_time_minutes": duration_seconds / 60,
            "buckets_processed": len(bucket_results),
            "avg_docs_per_minute": (total_docs / (duration_seconds / 60)) if duration_seconds > 0 else 0,
            "bucket_breakdown": bucket_results,
            "async_processing": True,
            "max_concurrent_tasks": self.max_concurrent_tasks
        }
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics - async"""
        return {
            "total_processed": self.stats["total_processed"],
            "successful": self.stats["successful"],
            "failed": self.stats["failed"],
            "success_rate": f"{(self.stats['successful']/self.stats['total_processed'])*100:.1f}%" if self.stats["total_processed"] > 0 else "0%",
            "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None,
            "end_time": self.stats["end_time"].isoformat() if self.stats["end_time"] else None,
            "is_running": self.stats["start_time"] is not None and self.stats["end_time"] is None,
            "processing_type": "async",
            "max_concurrent_tasks": self.max_concurrent_tasks
        }
    
    def get_processing_stats_sync(self) -> Dict[str, Any]:
        """Get current processing statistics - sync version for compatibility"""
        return {
            "total_processed": self.stats["total_processed"],
            "successful": self.stats["successful"],
            "failed": self.stats["failed"],
            "success_rate": f"{(self.stats['successful']/self.stats['total_processed'])*100:.1f}%" if self.stats["total_processed"] > 0 else "0%",
            "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None,
            "end_time": self.stats["end_time"].isoformat() if self.stats["end_time"] else None,
            "is_running": self.stats["start_time"] is not None and self.stats["end_time"] is None,
            "processing_type": "async",
            "max_concurrent_tasks": self.max_concurrent_tasks
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)


class BatchProcessorCompat:
    """Compatibility wrapper for existing sync code"""
    
    def __init__(self, async_processor):
        self._async_processor = async_processor
    
    async def process_all_buckets(self, *args, **kwargs):
        """Async interface"""
        return await self._async_processor.process_all_buckets(*args, **kwargs)
    
    async def process_bucket(self, *args, **kwargs):
        """Async interface"""
        return await self._async_processor.process_bucket(*args, **kwargs)
    
    async def process_specific_documents(self, *args, **kwargs):
        """Async interface"""
        return await self._async_processor.process_specific_documents(*args, **kwargs)
    
    def process_all_buckets_sync(self, *args, **kwargs):
        """Sync interface for backward compatibility"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._async_processor.process_all_buckets(*args, **kwargs))
    
    def process_bucket_sync(self, *args, **kwargs):
        """Sync interface for backward compatibility"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._async_processor.process_bucket(*args, **kwargs))
    
    def process_specific_documents_sync(self, *args, **kwargs):
        """Sync interface for backward compatibility"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._async_processor.process_specific_documents(*args, **kwargs))
    
    def get_processing_stats(self):
        """Sync stats interface"""
        return self._async_processor.get_processing_stats_sync()


# Global async batch processor instance
async_batch_processor = AsyncBatchProcessor()

# Create compatibility wrapper for existing code
batch_processor = BatchProcessorCompat(async_batch_processor)

# For services that expect the old interface
class LegacyBatchProcessor:
    """Legacy sync interface"""
    
    def __init__(self, async_processor):
        self._async_processor = async_processor
    
    async def process_all_buckets(self, *args, **kwargs):
        return await self._async_processor.process_all_buckets(*args, **kwargs)
    
    async def process_bucket(self, *args, **kwargs):
        return await self._async_processor.process_bucket(*args, **kwargs)
    
    async def process_specific_documents(self, *args, **kwargs):
        return await self._async_processor.process_specific_documents(*args, **kwargs)
    
    def get_processing_stats(self):
        return self._async_processor.get_processing_stats_sync()

# Legacy instance for backward compatibility
legacy_batch_processor = LegacyBatchProcessor(async_batch_processor)