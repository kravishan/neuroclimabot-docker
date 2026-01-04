"""
Common utility functions and helpers
"""

import re
import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import hashlib


logger = logging.getLogger(__name__)


class TextProcessor:
    """Text processing utilities"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        
        return text
    
    @staticmethod
    def truncate_text(text: str, max_words: int = 4000, suffix: str = "...") -> str:
        """Truncate text to maximum word count"""
        if not text:
            return text
        
        words = text.split()
        if len(words) <= max_words:
            return text
        
        return " ".join(words[:max_words]) + suffix
    
    @staticmethod
    def extract_sentences(text: str, max_sentences: int = None) -> List[str]:
        """Extract sentences from text"""
        if not text:
            return []
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if max_sentences:
            sentences = sentences[:max_sentences]
        
        return sentences
    
    @staticmethod
    def count_words(text: str) -> int:
        """Count words in text"""
        if not text:
            return 0
        return len(text.split())
    
    @staticmethod
    def count_characters(text: str, include_spaces: bool = True) -> int:
        """Count characters in text"""
        if not text:
            return 0
        
        if include_spaces:
            return len(text)
        else:
            return len(text.replace(' ', ''))
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 3, max_count: int = 20) -> List[str]:
        """Extract potential keywords from text"""
        if not text:
            return []
        
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{' + str(min_length) + ',}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our',
            'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way',
            'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'with', 'have', 'this',
            'that', 'from', 'they', 'know', 'want', 'been', 'good', 'much', 'some', 'time', 'very', 'when',
            'come', 'here', 'just', 'like', 'long', 'make', 'many', 'over', 'such', 'take', 'than', 'them',
            'well', 'will'
        }
        
        keywords = [word for word in words if word not in stop_words]
        
        # Count frequency and return most common
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_keywords[:max_count]]


class FileUtils:
    """File and path utilities"""
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension from filename"""
        if not filename or '.' not in filename:
            return ""
        return filename.split('.')[-1].lower()
    
    @staticmethod
    def is_document_file(filename: str) -> bool:
        """Check if file is a supported document type"""
        if not filename:
            return False
        
        supported_extensions = ['pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv', 'txt']
        extension = FileUtils.get_file_extension(filename)
        return extension in supported_extensions
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        if not filename:
            return "unnamed_file"
        
        # Remove invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Ensure not empty
        if not sanitized:
            sanitized = "unnamed_file"
        
        return sanitized
    
    @staticmethod
    def generate_file_hash(content: bytes) -> str:
        """Generate hash for file content"""
        return hashlib.md5(content).hexdigest()


class DataUtils:
    """Data processing utilities"""
    
    @staticmethod
    def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Safely get value from dictionary"""
        return dictionary.get(key, default) if dictionary else default
    
    @staticmethod
    def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two dictionaries"""
        if not dict1:
            return dict2 or {}
        if not dict2:
            return dict1
        
        merged = dict1.copy()
        merged.update(dict2)
        return merged
    
    @staticmethod
    def filter_none_values(dictionary: Dict[str, Any]) -> Dict[str, Any]:
        """Remove None values from dictionary"""
        if not dictionary:
            return {}
        
        return {k: v for k, v in dictionary.items() if v is not None}
    
    @staticmethod
    def flatten_list(nested_list: List[List[Any]]) -> List[Any]:
        """Flatten nested list"""
        if not nested_list:
            return []
        
        flattened = []
        for item in nested_list:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)
        
        return flattened
    
    @staticmethod
    def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split list into chunks of specified size"""
        if not lst or chunk_size <= 0:
            return []
        
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


class ValidationUtils:
    """Validation utilities"""
    
    @staticmethod
    def is_valid_bucket_name(bucket_name: str) -> bool:
        """Validate bucket name format"""
        if not bucket_name:
            return False
        
        # Check length
        if len(bucket_name) < 3 or len(bucket_name) > 63:
            return False
        
        # Check characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', bucket_name):
            return False
        
        return True
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """Basic email validation"""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Basic URL validation"""
        if not url:
            return False
        
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
        return bool(re.match(pattern, url))


class LoggingUtils:
    """Logging utilities"""
    
    @staticmethod
    def setup_logging(level: str = "INFO", format_string: str = None) -> None:
        """Setup basic logging configuration"""
        
        if format_string is None:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=getattr(logging, level.upper()),
            format=format_string,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    @staticmethod
    def log_processing_step(step_name: str, filename: str, status: str = "started", **kwargs) -> None:
        """Log processing step with consistent format"""
        logger = logging.getLogger(__name__)
        
        message = f"Processing step '{step_name}' {status} for file '{filename}'"
        
        if kwargs:
            details = ", ".join(f"{k}={v}" for k, v in kwargs.items())
            message += f" ({details})"
        
        if status.lower() in ["started", "begin", "beginning"]:
            logger.info(message)
        elif status.lower() in ["completed", "finished", "success", "successful"]:
            logger.info(f"✓ {message}")
        elif status.lower() in ["failed", "error", "failed"]:
            logger.error(f"✗ {message}")
        else:
            logger.info(message)


class DateTimeUtils:
    """Date and time utilities"""
    
    @staticmethod
    def get_current_timestamp() -> str:
        """Get current timestamp in ISO format"""
        return datetime.now().isoformat()
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """Parse ISO timestamp string"""
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None


class MetricsUtils:
    """Metrics and statistics utilities"""
    
    @staticmethod
    def calculate_success_rate(successful: int, total: int) -> str:
        """Calculate success rate as percentage string"""
        if total == 0:
            return "0%"
        return f"{(successful / total) * 100:.1f}%"
    
    @staticmethod
    def calculate_average(values: List[Union[int, float]]) -> float:
        """Calculate average of numeric values"""
        if not values:
            return 0.0
        return sum(values) / len(values)
    
    @staticmethod
    def calculate_percentile(values: List[Union[int, float]], percentile: float) -> float:
        """Calculate percentile of numeric values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index
            
            if upper_index >= len(sorted_values):
                return sorted_values[lower_index]
            
            return sorted_values[lower_index] * (1 - weight) + sorted_values[upper_index] * weight


# Common helper functions for backward compatibility
def clean_text(text: str) -> str:
    """Clean and normalize text - backward compatibility"""
    return TextProcessor.clean_text(text)


def truncate_text(text: str, max_words: int = 4000) -> str:
    """Truncate text to maximum word count - backward compatibility"""
    return TextProcessor.truncate_text(text, max_words)


def safe_get(dictionary: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary - backward compatibility"""
    return DataUtils.safe_get(dictionary, key, default)


def get_current_timestamp() -> str:
    """Get current timestamp - backward compatibility"""
    return DateTimeUtils.get_current_timestamp()


def calculate_success_rate(successful: int, total: int) -> str:
    """Calculate success rate - backward compatibility"""
    return MetricsUtils.calculate_success_rate(successful, total)