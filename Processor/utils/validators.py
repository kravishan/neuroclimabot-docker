"""
Input Validation Logic
Centralized validation for all API inputs and data
"""

import re
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException
from pydantic import BaseModel, validator


# ============ Base Validators ============

class ValidationError(Exception):
    """Custom validation error"""
    pass


def validate_required(value: Any, field_name: str) -> Any:
    """Validate required field"""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required")
    return value


def validate_string_length(value: str, field_name: str, min_length: int = 1, max_length: int = 1000) -> str:
    """Validate string length"""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
    
    if len(value) > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters")
    
    return value


def validate_integer_range(value: int, field_name: str, min_value: int = None, max_value: int = None) -> int:
    """Validate integer range"""
    if not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer")
    
    if min_value is not None and value < min_value:
        raise ValidationError(f"{field_name} must be at least {min_value}")
    
    if max_value is not None and value > max_value:
        raise ValidationError(f"{field_name} must be at most {max_value}")
    
    return value


def validate_choice(value: Any, field_name: str, choices: List[Any]) -> Any:
    """Validate value is in allowed choices"""
    if value not in choices:
        raise ValidationError(f"{field_name} must be one of: {', '.join(map(str, choices))}")
    return value


# ============ Document/File Validators ============

def validate_filename(filename: str) -> str:
    """Validate filename format and safety"""
    filename = validate_required(filename, "filename")
    filename = validate_string_length(filename, "filename", 1, 255)
    
    # Check for invalid characters
    invalid_chars = '<>:"/\\|?*'
    if any(char in filename for char in invalid_chars):
        raise ValidationError(f"filename contains invalid characters: {invalid_chars}")
    
    # Check for reserved names (Windows)
    reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
    if filename.upper().split('.')[0] in reserved_names:
        raise ValidationError(f"filename uses reserved name: {filename}")
    
    return filename


def validate_bucket_name(bucket: str) -> str:
    """Validate bucket name"""
    bucket = validate_required(bucket, "bucket")
    bucket = validate_string_length(bucket, "bucket", 1, 100)
    
    # Check bucket name format
    if not re.match(r'^[a-zA-Z0-9_-]+$', bucket):
        raise ValidationError("bucket name can only contain letters, numbers, hyphens, and underscores")
    
    return bucket


def validate_file_size(content_length: int, max_size_mb: int = 100) -> int:
    """Validate file size"""
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if content_length > max_size_bytes:
        raise ValidationError(f"File size ({content_length} bytes) exceeds maximum allowed size ({max_size_mb} MB)")
    
    return content_length


def validate_file_type(filename: str, allowed_types: List[str] = None) -> str:
    """Validate file type by extension"""
    if allowed_types is None:
        allowed_types = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']
    
    filename_lower = filename.lower()
    if not any(filename_lower.endswith(ext) for ext in allowed_types):
        raise ValidationError(f"File type not supported. Allowed types: {', '.join(allowed_types)}")
    
    return filename


# ============ Processing Option Validators ============

def validate_processing_options(options: Dict[str, Any]) -> Dict[str, Any]:
    """Validate processing options"""
    validated = {}
    
    # Boolean options
    bool_options = ['include_chunking', 'include_summarization', 'include_graphrag', 'skip_processed']
    for option in bool_options:
        if option in options:
            if not isinstance(options[option], bool):
                raise ValidationError(f"{option} must be a boolean")
            validated[option] = options[option]
    
    # Integer options
    int_options = {
        'max_documents': (1, 10000),
        'max_documents_per_bucket': (1, 10000),
        'chunk_limit': (1, 100),
        'summary_limit': (1, 50),
        'limit': (1, 1000)
    }
    
    for option, (min_val, max_val) in int_options.items():
        if option in options:
            try:
                value = int(options[option])
                validated[option] = validate_integer_range(value, option, min_val, max_val)
            except (ValueError, TypeError):
                raise ValidationError(f"{option} must be an integer")
    
    # At least one processing step must be enabled
    processing_steps = ['include_chunking', 'include_summarization', 'include_graphrag']
    enabled_steps = [validated.get(step, True) for step in processing_steps if step in validated]
    
    if enabled_steps and not any(enabled_steps):
        raise ValidationError("At least one processing step must be enabled (chunking, summarization, or GraphRAG)")
    
    return validated


# ============ Search/Query Validators ============

def validate_search_query(query: str) -> str:
    """Validate search query"""
    query = validate_required(query, "query")
    query = validate_string_length(query, "query", 1, 1000)
    
    # Clean query
    query = query.strip()
    
    # Check for minimum meaningful length
    if len(query) < 2:
        raise ValidationError("Search query must be at least 2 characters long")
    
    return query


def validate_search_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    """Validate search filters"""
    validated = {}
    
    if 'bucket' in filters and filters['bucket']:
        validated['bucket'] = validate_bucket_name(filters['bucket'])
    
    if 'limit' in filters:
        validated['limit'] = validate_integer_range(int(filters['limit']), 'limit', 1, 1000)
    
    if 'offset' in filters:
        validated['offset'] = validate_integer_range(int(filters['offset']), 'offset', 0, 100000)
    
    return validated


# ============ Batch Processing Validators ============

def validate_batch_request(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate batch processing request"""
    if not documents:
        raise ValidationError("documents list cannot be empty")
    
    if len(documents) > 1000:
        raise ValidationError("Maximum 1000 documents per batch request")
    
    validated_docs = []
    for i, doc in enumerate(documents):
        try:
            validated_doc = {}
            
            if 'bucket' not in doc:
                raise ValidationError("bucket is required")
            validated_doc['bucket'] = validate_bucket_name(doc['bucket'])
            
            if 'filename' not in doc:
                raise ValidationError("filename is required")
            validated_doc['filename'] = validate_filename(doc['filename'])
            
            # Optional file_path
            if 'file_path' in doc:
                validated_doc['file_path'] = validate_string_length(doc['file_path'], 'file_path', 1, 1000)
            
            validated_docs.append(validated_doc)
            
        except ValidationError as e:
            raise ValidationError(f"Document {i+1}: {str(e)}")
    
    return validated_docs


# ============ GraphRAG Validators ============

def validate_graphrag_query(query: str, max_entities: int = None, max_relationships: int = None, 
                           max_communities: int = None) -> Dict[str, Any]:
    """Validate GraphRAG query parameters"""
    validated = {
        'query': validate_search_query(query)
    }
    
    if max_entities is not None:
        validated['max_entities'] = validate_integer_range(max_entities, 'max_entities', 1, 1000)
    
    if max_relationships is not None:
        validated['max_relationships'] = validate_integer_range(max_relationships, 'max_relationships', 1, 1000)
    
    if max_communities is not None:
        validated['max_communities'] = validate_integer_range(max_communities, 'max_communities', 1, 100)
    
    return validated


# ============ API Request Models with Validation ============

class BaseRequest(BaseModel):
    """Base request model with common validation"""
    
    class Config:
        str_strip_whitespace = True
        validate_assignment = True


class DocumentRequest(BaseRequest):
    """Document processing request"""
    bucket: str
    filename: str
    
    @validator('bucket')
    def validate_bucket(cls, v):
        return validate_bucket_name(v)
    
    @validator('filename')
    def validate_filename_field(cls, v):
        return validate_filename(v)


class ProcessingRequest(DocumentRequest):
    """Processing request with options"""
    include_chunking: bool = True
    include_summarization: bool = True
    include_graphrag: bool = False
    
    @validator('include_chunking', 'include_summarization', 'include_graphrag')
    def validate_at_least_one_enabled(cls, v, values):
        # This will be checked after all fields are validated
        return v
    
    @validator('include_graphrag')
    def validate_processing_options_enabled(cls, v, values):
        # Check that at least one processing option is enabled
        enabled = [
            values.get('include_chunking', True),
            values.get('include_summarization', True),
            v
        ]
        if not any(enabled):
            raise ValueError("At least one processing option must be enabled")
        return v


class SearchRequest(BaseRequest):
    """Search request"""
    query: str
    bucket: Optional[str] = None
    limit: int = 10
    
    @validator('query')
    def validate_query_field(cls, v):
        return validate_search_query(v)
    
    @validator('bucket')
    def validate_bucket_field(cls, v):
        return validate_bucket_name(v) if v else v
    
    @validator('limit')
    def validate_limit_field(cls, v):
        return validate_integer_range(v, 'limit', 1, 1000)


class BatchRequest(BaseRequest):
    """Batch processing request"""
    documents: List[Dict[str, str]]
    include_chunking: bool = True
    include_summarization: bool = True
    include_graphrag: bool = False
    
    @validator('documents')
    def validate_documents_field(cls, v):
        return validate_batch_request(v)


# ============ HTTP Exception Helpers ============

def validation_error_to_http_exception(error: ValidationError) -> HTTPException:
    """Convert validation error to HTTP exception"""
    return HTTPException(status_code=422, detail=str(error))


def validate_and_raise(validation_func, *args, **kwargs):
    """Validate and raise HTTP exception on error"""
    try:
        return validation_func(*args, **kwargs)
    except ValidationError as e:
        raise validation_error_to_http_exception(e)


# ============ Utility Functions ============

def sanitize_input(value: str, allow_chars: str = r'a-zA-Z0-9\s\-_\.') -> str:
    """Sanitize input by removing unwanted characters"""
    if not isinstance(value, str):
        return str(value)
    
    pattern = f'[^{allow_chars}]'
    return re.sub(pattern, '', value).strip()


def validate_json_structure(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
    """Validate JSON structure has required fields"""
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
    
    return data


def validate_url(url: str) -> str:
    """Validate URL format"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise ValidationError("Invalid URL format")
    
    return url