"""
Input Services for Document Sources
Handles MinIO and other document input sources
"""

import logging
from typing import List, Dict, Any, Optional, BinaryIO
from io import BytesIO

from config import config

logger = logging.getLogger(__name__)


class MinioInput:
    """MinIO input service for document storage"""
    
    def __init__(self):
        # Get MinIO configuration
        minio_config = config.get('minio')
        
        self.endpoint = minio_config['endpoint']
        self.access_key = minio_config['access_key']
        self.secret_key = minio_config['secret_key']
        self.secure = minio_config['secure']
        self.processable_buckets = minio_config['processable_buckets']
        
        # Initialize MinIO client
        self.client = None
        self.connected = False
        
        self._connect()
    
    def _connect(self):
        """Connect to MinIO server"""
        try:
            # Only import minio when actually connecting
            try:
                from minio import Minio
                from minio.error import S3Error
                self._minio_available = True
                self._S3Error = S3Error
            except ImportError:
                logger.warning("minio package not installed - MinIO storage will not be available")
                self._minio_available = False
                return
            
            if not self.access_key or not self.secret_key:
                logger.error("MinIO credentials not provided")
                return
            
            self.client = Minio(
                endpoint=self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            
            # Test connection
            self.client.list_buckets()
            self.connected = True
            logger.info(f"✓ Connected to MinIO at {self.endpoint}")
            
        except Exception as e:
            logger.error(f"✗ MinIO connection failed: {e}")
            self.connected = False
            self._minio_available = False
    
    def health_check(self) -> bool:
        """Check MinIO health"""
        if not self._minio_available or not self.client:
            return False
        
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False
    
    def list_buckets(self) -> List[str]:
        """List all MinIO buckets"""
        if not self._minio_available or not self.client:
            return []
        
        try:
            buckets = self.client.list_buckets()
            return [bucket.name for bucket in buckets]
        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            return []
    
    def list_objects(self, bucket_name: str, prefix: str = None) -> List[str]:
        """List objects in bucket - updated to handle nested folders"""
        if not self._minio_available or not self.client:
            return []
        
        try:
            objects = self.client.list_objects(
                bucket_name, 
                prefix=prefix, 
                recursive=True  # Always use recursive to find all files
            )
            object_names = []
            
            for obj in objects:
                # Skip folders (objects ending with '/')
                if not obj.object_name.endswith('/'):
                    object_names.append(obj.object_name)
            
            return object_names
        except Exception as e:
            logger.error(f"Failed to list objects in {bucket_name}: {e}")
            return []
    
    def find_file_in_bucket(self, bucket: str, filename: str) -> str:
        """Find file in specified bucket (searches recursively)"""
        if not self._minio_available or not self.client:
            raise Exception("MinIO client not connected")
        
        try:
            # Try direct path first
            try:
                self.client.stat_object(bucket, filename)
                return filename
            except self._S3Error:
                pass
            
            # Search recursively
            objects = self.client.list_objects(bucket, recursive=True)
            for obj in objects:
                if obj.object_name.endswith(filename) or obj.object_name == filename:
                    return obj.object_name
            
            raise Exception(f"File '{filename}' not found in bucket '{bucket}'")
            
        except Exception as e:
            raise Exception(f"Error finding file in bucket: {e}")
    
    def get_document(self, bucket_name: str, object_name: str) -> bytes:
        """Get document content from MinIO - now with file finding"""
        if not self._minio_available or not self.client:
            raise Exception("MinIO client not connected")
        
        try:
            # First try to find the actual file path
            actual_path = self.find_file_in_bucket(bucket_name, object_name)
            
            response = self.client.get_object(bucket_name, actual_path)
            content = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"Retrieved {actual_path} from {bucket_name} ({len(content)} bytes)")
            return content
            
        except self._S3Error as e:
            logger.error(f"MinIO S3 error getting {object_name}: {e}")
            raise Exception(f"Document not found: {object_name}")
        except Exception as e:
            logger.error(f"Failed to get document {object_name}: {e}")
            raise
    
    def put_document(self, bucket_name: str, object_name: str, 
                    content: bytes, content_type: str = "application/octet-stream") -> bool:
        """Put document content to MinIO"""
        if not self._minio_available or not self.client:
            raise Exception("MinIO client not connected")
        
        try:
            content_stream = BytesIO(content)
            
            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=content_stream,
                length=len(content),
                content_type=content_type
            )
            
            logger.info(f"Uploaded {object_name} to {bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to put document {object_name}: {e}")
            return False
    
    def delete_document(self, bucket_name: str, object_name: str) -> bool:
        """Delete document from MinIO"""
        if not self._minio_available or not self.client:
            raise Exception("MinIO client not connected")
        
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted {object_name} from {bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {object_name}: {e}")
            return False
    
    def document_exists(self, bucket_name: str, object_name: str) -> bool:
        """Check if document exists in MinIO - now with file finding"""
        if not self._minio_available or not self.client:
            return False
        
        try:
            self.find_file_in_bucket(bucket_name, object_name)
            return True
        except Exception:
            return False
    
    def get_document_info(self, bucket_name: str, object_name: str) -> Dict[str, Any]:
        """Get document metadata - now with file finding"""
        if not self._minio_available or not self.client:
            return {}
        
        try:
            # Find the actual file path first
            actual_path = self.find_file_in_bucket(bucket_name, object_name)
            stat = self.client.stat_object(bucket_name, actual_path)
            return {
                "object_name": actual_path,
                "bucket_name": bucket_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
        except Exception as e:
            logger.error(f"Failed to get document info for {object_name}: {e}")
            return {}
    
    def create_bucket(self, bucket_name: str) -> bool:
        """Create MinIO bucket"""
        if not self._minio_available or not self.client:
            return False
        
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
                return True
            else:
                logger.info(f"Bucket already exists: {bucket_name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            return False
    
    def get_processable_buckets(self) -> List[str]:
        """Get list of processable buckets"""
        return self.processable_buckets.copy()
    
    def is_bucket_processable(self, bucket_name: str) -> bool:
        """Check if bucket is processable"""
        return bucket_name in self.processable_buckets
    
    def get_bucket_documents(self, bucket_name: str, 
                           file_extensions: List[str] = None) -> List[Dict[str, Any]]:
        """Get all documents in bucket with metadata"""
        if file_extensions is None:
            file_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']
        
        documents = []
        objects = self.list_objects(bucket_name)
        
        for object_name in objects:
            # Filter by file extension
            if any(object_name.lower().endswith(ext) for ext in file_extensions):
                doc_info = self.get_document_info(bucket_name, object_name)
                if doc_info:
                    documents.append(doc_info)
        
        return documents
    
    def get_stats(self) -> Dict[str, Any]:
        """Get MinIO service statistics"""
        stats = {
            "connected": self.connected,
            "endpoint": self.endpoint,
            "processable_buckets": len(self.processable_buckets),
            "bucket_stats": {},
            "minio_available": self._minio_available
        }
        
        if self.connected and self._minio_available:
            all_buckets = self.list_buckets()
            stats["total_buckets"] = len(all_buckets)
            
            # Get stats for processable buckets
            for bucket in self.processable_buckets:
                if bucket in all_buckets:
                    try:
                        documents = self.get_bucket_documents(bucket)
                        stats["bucket_stats"][bucket] = {
                            "document_count": len(documents),
                            "total_size": sum(doc.get("size", 0) for doc in documents)
                        }
                    except Exception as e:
                        stats["bucket_stats"][bucket] = {"error": str(e)}
                else:
                    stats["bucket_stats"][bucket] = {"status": "not_found"}
        
        return stats
    
    def close(self):
        """Close MinIO connection"""
        # MinIO client doesn't need explicit closing
        self.connected = False
        logger.info("MinIO connection closed")


class InputManager:
    """Manager for all input services"""
    
    def __init__(self):
        self.services = {}
        self.primary_service = None
    
    def add_service(self, name: str, service: Any, is_primary: bool = False):
        """Add input service"""
        self.services[name] = service
        if is_primary or not self.primary_service:
            self.primary_service = name
        logger.info(f"Added input service: {name}")
    
    def get_service(self, name: str = None):
        """Get input service"""
        service_name = name or self.primary_service
        service = self.services.get(service_name)
        if not service:
            raise Exception(f"Input service not found: {service_name}")
        return service
    
    def get_available_services(self) -> List[str]:
        """Get list of available services"""
        return list(self.services.keys())
    
    def health_check_all(self) -> Dict[str, bool]:
        """Health check all services"""
        results = {}
        for name, service in self.services.items():
            try:
                results[name] = service.health_check() if hasattr(service, 'health_check') else True
            except Exception:
                results[name] = False
        return results


# Global instances
minio_input = None
input_manager = InputManager()

def get_minio_input() -> MinioInput:
    """Get global MinIO input instance"""
    global minio_input
    if not minio_input:
        minio_input = MinioInput()
        input_manager.add_service('minio', minio_input, is_primary=True)
    return minio_input

def get_input_manager() -> InputManager:
    """Get global input manager instance"""
    return input_manager

# Initialize default MinIO service
def initialize_inputs():
    """Initialize input services"""
    try:
        minio_service = get_minio_input()
        logger.info("Input services initialized")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize input services: {e}")
        return False