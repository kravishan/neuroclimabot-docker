"""Helper utility functions."""

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import UUID


def generate_id() -> str:
    """Generate a secure random ID."""
    return secrets.token_urlsafe(16)


def hash_content(content: str) -> str:
    """Generate SHA-256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


def utc_now() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(timezone.utc)


def safe_get(data: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safely get value from dictionary."""
    return data.get(key, default)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage."""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def validate_uuid(uuid_string: str) -> bool:
    """Validate UUID string format."""
    try:
        UUID(uuid_string)
        return True
    except ValueError:
        return False