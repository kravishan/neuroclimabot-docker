"""
Updated MinIO object storage client with public shareable URLs for references.
Handles different buckets with 30-minute expiry and folder path resolution.
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.core.exceptions import RAGException
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MinIOClient:
    """Updated MinIO client with public shareable URLs for references."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = None
        self.is_connected = False
        
        # MinIO configuration from environment
        self.endpoint = self.settings.MINIO_ENDPOINT
        self.access_key = self.settings.MINIO_ACCESS_KEY
        self.secret_key = self.settings.MINIO_SECRET_KEY
        self.secure = self.settings.MINIO_SECURE
        
        # Bucket names based on source types
        self.bucket_mapping = {
            "news": "news",
            "policy": "policy", 
            "researchpapers": "researchpapers",
            "scientificdata": "scientificdata"
        }
        
        # Public shareable URL expiry (30 minutes)
        self.presigned_url_expiry = timedelta(minutes=30)
        
        # Cache for file path resolution
        self.path_cache = {}
        self.cache_expiry = {}
        self.cache_duration = timedelta(hours=1)  # Cache paths for 1 hour
        
        logger.info(f"MinIO configured: {self.endpoint} (secure: {self.secure}) - 30min URL expiry")
    
    async def initialize(self):
        """Initialize MinIO client with secure connection."""
        try:
            self.client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
            
            # Test connection
            if await self.health_check():
                self.is_connected = True
                logger.info("✅ Connected to MinIO for public shareable URLs")
                
                # Verify buckets exist
                await self._verify_buckets()
            else:
                raise RAGException("MinIO connection test failed")
                
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            raise RAGException(f"MinIO initialization failed: {str(e)}")
    
    async def _verify_buckets(self):
        """Verify that all required buckets exist."""
        for bucket_type, bucket_name in self.bucket_mapping.items():
            try:
                if self.client.bucket_exists(bucket_name):
                    logger.info(f"✅ Bucket '{bucket_name}' exists")
                else:
                    logger.warning(f"⚠️  Bucket '{bucket_name}' does not exist")
            except S3Error as e:
                logger.warning(f"Could not check bucket {bucket_name}: {e}")
    
    async def generate_shareable_reference_url(self, doc_name: str, bucket_source: str) -> Optional[str]:
        """
        Generate public shareable URL for references with 30-minute expiry.
        Handles folder structures and provides URLs that work without authentication.

        Args:
            doc_name: Document filename (may or may not include folder path)
            bucket_source: Source bucket type (policy, researchpapers, scientificdata, news)

        Returns:
            Public shareable URL with 30-minute expiry, or None if document not found
        """
        try:
            # Get bucket name from mapping
            bucket_name = self.bucket_mapping.get(bucket_source.lower())

            if not bucket_name:
                logger.warning(f"Unknown bucket source: {bucket_source}")
                return None

            # Check if bucket exists
            if not self.client.bucket_exists(bucket_name):
                logger.warning(f"Bucket {bucket_name} does not exist")
                return None

            # Find the actual file path (handles folders)
            actual_file_path = await self._find_document_path(doc_name, bucket_name)

            if not actual_file_path:
                logger.warning(f"Document {doc_name} not found in bucket {bucket_name}")
                return None

            # Generate public shareable presigned URL with 30-minute expiry
            presigned_url = self.client.presigned_get_object(
                bucket_name,
                actual_file_path,
                expires=self.presigned_url_expiry
            )

            logger.debug(f"Generated 30min shareable URL for {doc_name} -> {actual_file_path}")
            return presigned_url

        except Exception as e:
            logger.error(f"Failed to generate shareable URL for {doc_name}: {e}")
            return None
    
    async def _find_document_path(self, doc_name: str, bucket_name: str) -> Optional[str]:
        """
        Find the actual path of a document in MinIO bucket, handling folder structures.
        Uses caching to improve performance for repeated requests.
        """
        
        # Check cache first
        cache_key = f"{bucket_name}:{doc_name}"
        now = datetime.now()
        
        if (cache_key in self.path_cache and 
            cache_key in self.cache_expiry and 
            now < self.cache_expiry[cache_key]):
            logger.debug(f"Using cached path for {doc_name}")
            return self.path_cache[cache_key]
        
        try:
            # First, try direct access (file might be in root)
            try:
                self.client.stat_object(bucket_name, doc_name)
                actual_path = doc_name
                logger.debug(f"Found {doc_name} in bucket root")
                
                # Cache the result
                self.path_cache[cache_key] = actual_path
                self.cache_expiry[cache_key] = now + self.cache_duration
                
                return actual_path
                
            except S3Error:
                # File not in root, search recursively
                logger.debug(f"Searching for {doc_name} in subfolders...")
                
                # Search through all objects in bucket
                for obj in self.client.list_objects(bucket_name, recursive=True):
                    object_name = obj.object_name
                    
                    # Check if this object matches our document name
                    if object_name.endswith(doc_name):
                        # logger.info(f"Found {doc_name} at path: {object_name}")
                        
                        # Cache the result
                        self.path_cache[cache_key] = object_name
                        self.cache_expiry[cache_key] = now + self.cache_duration
                        
                        return object_name
                    
                    # Also check if the filename matches (case-insensitive)
                    if object_name.lower().endswith(doc_name.lower()):
                        # logger.info(f"Found {doc_name} (case-insensitive) at path: {object_name}")
                        
                        # Cache the result
                        self.path_cache[cache_key] = object_name
                        self.cache_expiry[cache_key] = now + self.cache_duration
                        
                        return object_name
                
                logger.warning(f"Document {doc_name} not found in bucket {bucket_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error searching for document {doc_name}: {e}")
            return None
    
    
    def _clean_path_cache(self):
        """Clean expired entries from path cache."""
        now = datetime.now()
        expired_keys = [
            key for key, expiry_time in self.cache_expiry.items() 
            if now >= expiry_time
        ]
        
        for key in expired_keys:
            self.path_cache.pop(key, None)
            self.cache_expiry.pop(key, None)
        
        if expired_keys:
            logger.debug(f"Cleaned {len(expired_keys)} expired cache entries")
    
    async def list_documents_in_bucket(self, bucket_source: str, prefix: str = "") -> List[Dict[str, Any]]:
        """List all documents in a bucket for debugging."""
        try:
            bucket_name = self.bucket_mapping.get(bucket_source.lower())
            if not bucket_name:
                return []
            
            documents = []
            for obj in self.client.list_objects(bucket_name, prefix=prefix, recursive=True):
                documents.append({
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "etag": obj.etag,
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Failed to list documents in bucket {bucket_source}: {e}")
            return []
    
    async def upload_file(
        self,
        bucket: str,
        object_name: str,
        file_path: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload a file to MinIO."""
        try:
            # Get actual bucket name
            actual_bucket = self.bucket_mapping.get(bucket.lower(), bucket)
            
            self.client.fput_object(
                actual_bucket,
                object_name,
                file_path,
                metadata=metadata
            )
            logger.info(f"Uploaded file {object_name} to bucket {actual_bucket}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to upload file {object_name}: {e}")
            raise RAGException(f"File upload failed: {str(e)}")
    
    async def upload_data(
        self,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """Upload data to MinIO."""
        try:
            from io import BytesIO
            
            # Get actual bucket name
            actual_bucket = self.bucket_mapping.get(bucket.lower(), bucket)
            
            self.client.put_object(
                actual_bucket,
                object_name,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
                metadata=metadata
            )
            logger.info(f"Uploaded data {object_name} to bucket {actual_bucket}")
            return True
            
        except S3Error as e:
            logger.error(f"Failed to upload data {object_name}: {e}")
            raise RAGException(f"Data upload failed: {str(e)}")
    
    async def health_check(self) -> bool:
        """Check MinIO health."""
        try:
            if not self.client:
                return False
            
            # Test by listing buckets
            list(self.client.list_buckets())
            return True
            
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get MinIO statistics."""
        try:
            buckets = []
            for bucket in self.client.list_buckets():
                bucket_info = {
                    "name": bucket.name,
                    "creation_date": bucket.creation_date,
                    "object_count": 0
                }
                
                # Count objects in bucket
                try:
                    objects = list(self.client.list_objects(bucket.name))
                    bucket_info["object_count"] = len(objects)
                except:
                    pass
                
                buckets.append(bucket_info)
            
            # Clean expired cache entries
            self._clean_path_cache()
            
            return {
                "connected": self.is_connected,
                "config": {
                    "endpoint": self.endpoint,
                    "secure": self.secure,
                    "bucket_mapping": self.bucket_mapping,
                    "presigned_url_expiry_minutes": self.presigned_url_expiry.total_seconds() / 60,
                    "url_type": "public_shareable_30min_expiry"
                },
                "buckets": buckets,
                "cache_stats": {
                    "path_cache_size": len(self.path_cache),
                    "cache_expiry_entries": len(self.cache_expiry)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get MinIO stats: {e}")
            return {"connected": False, "error": str(e)}


# Global MinIO client instance
minio_client = MinIOClient()


def get_minio_client() -> MinIOClient:
    """Get MinIO client instance."""
    return minio_client


# Legacy compatibility function
async def generate_document_url(doc_name: str, bucket_source: str) -> str:
    """Legacy function - generates shareable URL."""
    return await minio_client.generate_shareable_reference_url(doc_name, bucket_source)