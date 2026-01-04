import logging
from typing import Dict, Any, List, Optional
from config import config


logger = logging.getLogger(__name__)


class ServiceManager:
    """Centralized service management"""
    
    def __init__(self):
        self.services = {}
        self.service_configs = {
            'minio': ('inputs', 'MinioInput', "MinIO Storage"),
            'vector_storage': ('database', 'vector_storage', "Vector Storage"),
            'tracker': ('database', 'tracker', "Document Tracker")
        }
    
    def initialize_all_services(self) -> Dict[str, bool]:
        """Initialize all required services"""
        results = {}
        
        for service_name, (module_path, class_name, description) in self.service_configs.items():
            try:
                if module_path == 'database':
                    # Special handling for database instances
                    try:
                        from storage.database import tracker
                        from storage.milvus import milvus_storage
                        if service_name == 'vector_storage':
                            milvus_storage.connect()  # Ensure connection
                            self.services[service_name] = milvus_storage
                        elif service_name == 'tracker':
                            self.services[service_name] = tracker
                    except ImportError as e:
                        logger.error(f"Database module import failed: {e}")
                        self.services[service_name] = None
                        results[service_name] = False
                        continue
                        
                elif module_path == 'inputs':
                    # Handle inputs module
                    try:
                        from inputs import MinioInput
                        self.services[service_name] = MinioInput()
                    except ImportError as e:
                        logger.error(f"Inputs module import failed: {e}")
                        self.services[service_name] = None
                        results[service_name] = False
                        continue
                else:
                    # Dynamic import for other services
                    try:
                        module = __import__(module_path, fromlist=[class_name])
                        service_class = getattr(module, class_name)
                        self.services[service_name] = service_class()
                    except (ImportError, AttributeError) as e:
                        logger.error(f"Service import failed for {service_name}: {e}")
                        self.services[service_name] = None
                        results[service_name] = False
                        continue
                
                logger.info(f"✓ {description} initialized")
                results[service_name] = True
                
            except Exception as e:
                logger.error(f"✗ {description} failed: {e}")
                self.services[service_name] = None
                results[service_name] = False
        
        return results
    
    def get_service(self, service_name: str) -> Any:
        """Get service instance"""
        service = self.services.get(service_name)
        if not service:
            raise Exception(f"Service {service_name} not available")
        return service
    
    def is_service_available(self, service_name: str) -> bool:
        """Check if service is available"""
        return self.services.get(service_name) is not None
    
    def get_available_services(self) -> List[str]:
        """Get list of available services"""
        return [name for name, service in self.services.items() if service is not None]
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        available = self.get_available_services()
        total = len(self.service_configs)
        
        service_status = {}
        for name, service in self.services.items():
            if service:
                try:
                    # Try to get health status if available
                    if hasattr(service, 'health_check'):
                        service_status[name] = "healthy" if service.health_check() else "unhealthy"
                    else:
                        service_status[name] = "available"
                except Exception:
                    service_status[name] = "error"
            else:
                service_status[name] = "unavailable"
        
        return {
            "total_services": total,
            "available_count": len(available),
            "available": available,
            "service_status": service_status,
            "health_score": f"{(len(available)/total)*100:.1f}%"
        }
    
    def check_required_services(self, required: List[str]) -> None:
        """Check if required services are available"""
        missing = [s for s in required if not self.is_service_available(s)]
        if missing:
            raise Exception(f"Required services unavailable: {missing}")
    
    def shutdown_all_services(self):
        """Gracefully shutdown all services"""
        for service_name, service in self.services.items():
            if service:
                try:
                    if hasattr(service, 'disconnect'):
                        service.disconnect()
                    elif hasattr(service, 'close'):
                        service.close()
                    logger.info(f"✓ {service_name} shut down")
                except Exception as e:
                    logger.error(f"✗ Error shutting down {service_name}: {e}")


# Global service manager instance
service_manager = ServiceManager()