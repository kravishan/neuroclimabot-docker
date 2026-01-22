"""
Unified Document Extraction
Handles all document types with specialized extractors
"""

import requests
import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import io
import asyncio
from io import BytesIO
from PIL import Image

from config import config
from shared.clients.vision_client import get_vision_client

logger = logging.getLogger(__name__)


class DocumentExtractor:
    """Unified document extractor with caching and type-specific handling"""
    
    def __init__(self):
        # Use the config instance instead of class attributes
        unstructured_config = config.get('unstructured')
        self.api_url = f"{unstructured_config['api_url']}/general/v0/general"
        self.timeout = unstructured_config['timeout']

        # Get cache settings
        cache_settings = config.get_cache_settings()
        self.cache_enabled = cache_settings['enable_cache']
        self.cache_dir = Path(cache_settings['extraction_cache_dir'])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Get vision configuration for image extraction
        vision_config = config.get_vision_config()
        self.image_extraction_enabled = vision_config.get('enabled', False)
        self.extract_images_from_pdf = vision_config.get('extract_from_pdf', True)
        self.extract_images_from_docx = vision_config.get('extract_from_docx', True)
        self.replace_images_with_descriptions = vision_config.get('replace_with_descriptions', True)

        # Initialize vision client if image extraction is enabled
        self.vision_client = None
        if self.image_extraction_enabled:
            self.vision_client = get_vision_client()
            logger.info(f"🖼️ Image extraction enabled with vision model")

        logger.info(f"DocumentExtractor initialized with API: {self.api_url}")
        
    def extract_content(self, document_content: bytes, filename: str, 
                       strategy: str = "auto") -> List[Dict[str, Any]]:
        """Main extraction method with caching and enhanced debugging"""
        file_type = self._detect_file_type(filename)
        
        logger.info(f"🔍 Extracting {file_type} file: {filename} ({len(document_content)} bytes)")
        
        # Use cache if enabled
        if self.cache_enabled:
            cache_key = self._get_cache_key(document_content, filename, strategy)
            cached_result = self._load_from_cache(cache_key)
            if cached_result:
                total_text_length = sum(len(elem.get('text', '')) for elem in cached_result)
                logger.info(f"📋 Cache hit for {filename} - {len(cached_result)} elements, {total_text_length} chars")
                return cached_result
        
        # Extract based on file type
        if file_type == "excel":
            elements = self._extract_excel(document_content, filename)
        elif file_type == "csv":
            elements = self._extract_csv(document_content, filename)
        elif file_type == "pdf":
            elements = self._extract_pdf(document_content, filename, strategy)
        else:
            elements = self._extract_generic(document_content, filename, strategy)
        
        # Post-process and cache
        elements = self._post_process_elements(elements, filename, file_type)
        
        if self.cache_enabled and elements:
            self._save_to_cache(cache_key, elements)
        
        # Enhanced debugging
        total_text_length = sum(len(elem.get('text', '')) for elem in elements)
        logger.info(f"📊 Extracted {len(elements)} elements from {filename}")
        logger.info(f"📈 Total extracted text length: {total_text_length} characters")
        
        # Log element type breakdown
        element_types = {}
        for elem in elements:
            elem_type = elem.get('type', 'Unknown')
            element_types[elem_type] = element_types.get(elem_type, 0) + 1
        
        if element_types:
            logger.info(f"📋 Element breakdown: {element_types}")
        
        return elements
    
    def _detect_file_type(self, filename: str) -> str:
        """Detect file type from filename"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith(('.xlsx', '.xls')):
            return "excel"
        elif filename_lower.endswith('.csv'):
            return "csv"
        elif filename_lower.endswith('.pdf'):
            return "pdf"
        elif filename_lower.endswith(('.docx', '.doc')):
            return "word"
        elif filename_lower.endswith('.txt'):
            return "text"
        
        return "unknown"
    
    def _extract_excel(self, document_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Extract from Excel files"""
        try:
            logger.info(f"📊 Processing Excel file: {filename}")
            
            # Read Excel file
            df = pd.read_excel(io.BytesIO(document_content), header=1, engine='openpyxl')
            
            elements = []
            
            # Add title element
            elements.append({
                "type": "Title",
                "text": f"Excel Data: {filename}",
                "metadata": {"source": "excel_title"}
            })
            
            # Process each row as an element
            for index, row in df.iterrows():
                # Extract non-null values
                row_data = {}
                for col, value in row.items():
                    if pd.notna(value) and str(value).strip():
                        row_data[str(col)] = str(value).strip()
                
                if row_data:
                    # Create text representation
                    text_parts = []
                    for key, value in row_data.items():
                        text_parts.append(f"{key}: {value}")
                    
                    elements.append({
                        "type": "Table",
                        "text": " | ".join(text_parts),
                        "metadata": {
                            "row_index": index + 1,
                            "column_count": len(row_data),
                            "source": "excel_row",
                            "row_data": row_data
                        }
                    })
            
            logger.info(f"✅ Excel extraction successful: {len(elements)} elements")
            return elements
            
        except Exception as e:
            logger.error(f"❌ Excel extraction failed: {e}")
            logger.info("🔄 Falling back to generic extraction")
            return self._extract_generic(document_content, filename, "hi_res")
    
    def _extract_csv(self, document_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Extract from CSV files"""
        try:
            logger.info(f"📊 Processing CSV file: {filename}")
            
            # Read CSV
            df = pd.read_csv(io.BytesIO(document_content))
            
            elements = []
            
            # Add header as title
            elements.append({
                "type": "Title",
                "text": f"CSV Data: {filename}",
                "metadata": {"source": "csv_header"}
            })
            
            # Process rows
            for index, row in df.iterrows():
                row_data = {}
                for col, value in row.items():
                    if pd.notna(value):
                        row_data[str(col)] = str(value)
                
                if row_data:
                    text_parts = [f"{k}: {v}" for k, v in row_data.items()]
                    
                    elements.append({
                        "type": "Table",
                        "text": " | ".join(text_parts),
                        "metadata": {
                            "row_index": index + 1,
                            "source": "csv_row",
                            "row_data": row_data
                        }
                    })
            
            logger.info(f"✅ CSV extraction successful: {len(elements)} elements")
            return elements
            
        except Exception as e:
            logger.error(f"❌ CSV extraction failed: {e}")
            return []
    
    def _extract_pdf(self, document_content: bytes, filename: str, strategy: str) -> List[Dict[str, Any]]:
        """Extract from PDF files using Unstructured API"""
        logger.info(f"📄 Processing PDF file: {filename} with strategy: {strategy}")
        
        return self._call_unstructured_api(
            document_content, filename, strategy,
            extra_params={
                "pdf_infer_table_structure": True,
                "include_page_breaks": True
            }
        )
    
    def _extract_generic(self, document_content: bytes, filename: str, strategy: str) -> List[Dict[str, Any]]:
        """Generic extraction using Unstructured API"""
        logger.info(f"📋 Processing generic file: {filename} with strategy: {strategy}")
        return self._call_unstructured_api(document_content, filename, strategy)
    
    def _call_unstructured_api(self, document_content: bytes, filename: str,
                              strategy: str, extra_params: Dict = None) -> List[Dict[str, Any]]:
        """Call Unstructured API"""
        try:
            # Determine if we should extract images based on file type and config
            file_type = self._detect_file_type(filename)
            should_extract_images = False

            if self.image_extraction_enabled:
                if file_type == "pdf" and self.extract_images_from_pdf:
                    should_extract_images = True
                elif file_type == "word" and self.extract_images_from_docx:
                    should_extract_images = True

            data = {
                "strategy": strategy,
                "coordinates": True,
                "extract_images": should_extract_images,
                "languages": ["eng"]
            }

            if should_extract_images:
                logger.info(f"🖼️ Image extraction enabled for {filename} ({file_type})")
            
            if extra_params:
                data.update(extra_params)
            
            files = {"files": (filename, document_content)}
            
            logger.info(f"🌐 Calling Unstructured API for {filename}")

            response = requests.post(
                self.api_url,
                files=files,
                data=data,
                timeout=float(self.timeout)
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Unstructured API success: {len(result)} elements")
                return result
            else:
                logger.error(f"❌ Unstructured API error: {response.status_code} - {response.text}")
                return self._fallback_extraction(document_content, filename)
                
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Cannot connect to Unstructured API at {self.api_url}")
            return self._fallback_extraction(document_content, filename)
        except requests.exceptions.Timeout:
            logger.error(f"❌ Unstructured API timeout after {self.timeout}s")
            return self._fallback_extraction(document_content, filename)
        except Exception as e:
            logger.error(f"❌ API call failed: {e}")
            return self._fallback_extraction(document_content, filename)
    
    def _fallback_extraction(self, document_content: bytes, filename: str) -> List[Dict[str, Any]]:
        """Fallback extraction when API is unavailable"""
        logger.warning(f"⚠️ Using fallback extraction for {filename}")
        
        try:
            # Simple text extraction for common formats
            file_type = self._detect_file_type(filename)
            
            if file_type == "text":
                text_content = document_content.decode('utf-8', errors='ignore')
                logger.info(f"📝 Fallback text extraction: {len(text_content)} characters")
                return [{
                    "type": "NarrativeText",
                    "text": text_content,
                    "metadata": {"source": "fallback_text_extraction"}
                }]
            elif file_type in ["excel", "csv"]:
                # Already handled in specific methods
                return []
            else:
                # For other types, create a meaningful placeholder
                placeholder_text = f"Document content from {filename}. Original file size: {len(document_content)} bytes. File type: {file_type}. Content extraction requires Unstructured API service to be available."
                logger.info(f"📄 Fallback placeholder created: {len(placeholder_text)} characters")
                return [{
                    "type": "NarrativeText", 
                    "text": placeholder_text,
                    "metadata": {
                        "source": "fallback_extraction",
                        "original_size": len(document_content),
                        "file_type": file_type,
                        "extraction_method": "fallback_placeholder"
                    }
                }]
        except Exception as e:
            logger.error(f"❌ Fallback extraction failed: {e}")
            # Last resort - create minimal element
            return [{
                "type": "NarrativeText",
                "text": f"Document: {filename} (extraction failed)",
                "metadata": {"source": "minimal_fallback", "error": str(e)}
            }]
    
    async def _process_images_async(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process extracted images with vision model asynchronously"""
        if not self.image_extraction_enabled or not self.vision_client:
            return elements

        processed_elements = []
        images_processed = 0
        images_described = 0

        for element in elements:
            element_type = element.get("type", "")

            # Check if this is an image element
            if element_type == "Image":
                images_processed += 1
                metadata = element.get("metadata", {})

                # Get image data from metadata (Unstructured API returns base64 in metadata)
                image_base64 = metadata.get("image_base64")
                image_path = metadata.get("image_path")

                if image_base64:
                    try:
                        # Decode base64 image
                        import base64
                        image_bytes = base64.b64decode(image_base64)
                        image = Image.open(BytesIO(image_bytes))

                        # Get description from vision model
                        logger.info(f"🖼️ Processing image from document...")
                        description = await self.vision_client.describe_image(image)

                        if description:
                            images_described += 1
                            logger.info(f"✅ Image described: {description[:100]}...")

                            if self.replace_images_with_descriptions:
                                # Replace image element with text description
                                element["type"] = "NarrativeText"
                                element["text"] = f"[Image Description]: {description}"
                                element["metadata"]["original_type"] = "Image"
                                element["metadata"]["image_described"] = True
                                processed_elements.append(element)
                            else:
                                # Keep image element but add description to metadata
                                element["metadata"]["description"] = description
                                processed_elements.append(element)
                        else:
                            logger.warning(f"⚠️ Failed to describe image, skipping")
                            if not self.replace_images_with_descriptions:
                                processed_elements.append(element)

                    except Exception as e:
                        logger.error(f"❌ Error processing image: {e}")
                        if not self.replace_images_with_descriptions:
                            processed_elements.append(element)
                elif image_path:
                    # Handle file path based images if present
                    try:
                        logger.info(f"🖼️ Processing image from path: {image_path}")
                        description = await self.vision_client.describe_image(image_path)

                        if description:
                            images_described += 1
                            logger.info(f"✅ Image described: {description[:100]}...")

                            if self.replace_images_with_descriptions:
                                element["type"] = "NarrativeText"
                                element["text"] = f"[Image Description]: {description}"
                                element["metadata"]["original_type"] = "Image"
                                element["metadata"]["image_described"] = True
                                processed_elements.append(element)
                            else:
                                element["metadata"]["description"] = description
                                processed_elements.append(element)
                        else:
                            if not self.replace_images_with_descriptions:
                                processed_elements.append(element)

                    except Exception as e:
                        logger.error(f"❌ Error processing image from path: {e}")
                        if not self.replace_images_with_descriptions:
                            processed_elements.append(element)
                else:
                    logger.warning(f"⚠️ Image element has no image data")
                    if not self.replace_images_with_descriptions:
                        processed_elements.append(element)
            else:
                # Not an image element, keep as-is
                processed_elements.append(element)

        if images_processed > 0:
            logger.info(f"🖼️ Processed {images_processed} images, {images_described} successfully described")

        return processed_elements

    def _process_images(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Synchronous wrapper for async image processing"""
        if not self.image_extraction_enabled or not self.vision_client:
            return elements

        # Run async processing
        try:
            return asyncio.run(self._process_images_async(elements))
        except Exception as e:
            logger.error(f"❌ Failed to process images: {e}")
            return elements

    def _post_process_elements(self, elements: List[Dict[str, Any]],
                              filename: str, file_type: str) -> List[Dict[str, Any]]:
        """Post-process extracted elements"""
        # First process images if enabled
        elements = self._process_images(elements)

        processed = []

        for element in elements:
            text_content = element.get("text", "").strip()
            if not text_content:
                continue

            # Add metadata
            if "metadata" not in element:
                element["metadata"] = {}

            element["metadata"].update({
                "filename": filename,
                "file_type": file_type,
                "extraction_timestamp": self._get_current_timestamp(),
                "text_length": len(text_content)
            })

            # Clean text - preserve structure but remove excessive whitespace
            element["text"] = " ".join(text_content.split())

            processed.append(element)

        logger.info(f"📝 Post-processed {len(processed)} elements for {filename}")
        return processed
    
    def _get_cache_key(self, content: bytes, filename: str, strategy: str) -> str:
        """Generate cache key"""
        content_hash = hashlib.md5(content).hexdigest()[:8]
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.'))
        return f"{safe_filename}_{strategy}_{content_hash}"
    
    def _load_from_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """Load from cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                import json
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Cache load failed: {e}")
        return None
    
    def _save_to_cache(self, cache_key: str, elements: List[Dict[str, Any]]):
        """Save to cache"""
        try:
            cache_file = self.cache_dir / f"{cache_key}.json"
            import json
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(elements, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 Saved extraction to cache: {cache_key}")
        except Exception as e:
            logger.warning(f"⚠️ Cache save failed: {e}")
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def extract_text_only(self, document_content: bytes, filename: str) -> str:
        """Extract only text content for summarization"""
        elements = self.extract_content(document_content, filename, "basic")
        
        text_parts = []
        for element in elements:
            if element.get("type") in ["Title", "NarrativeText", "ListItem", "Table"]:
                text = element.get("text", "").strip()
                if text and len(text) > 10:
                    text_parts.append(text)
        
        combined_text = "\n\n".join(text_parts)
        logger.info(f"📝 Extracted text only: {len(combined_text)} characters from {len(text_parts)} elements")
        return combined_text
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        cache_files = list(self.cache_dir.glob("*.json")) if self.cache_dir.exists() else []
        
        return {
            "cache_enabled": self.cache_enabled,
            "cache_directory": str(self.cache_dir),
            "cached_extractions": len(cache_files),
            "api_url": self.api_url,
            "timeout": self.timeout
        }
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear extraction cache"""
        if not self.cache_dir.exists():
            return {"cleared": 0, "message": "Cache directory does not exist"}
        
        cache_files = list(self.cache_dir.glob("*.json"))
        cleared_count = 0
        
        for cache_file in cache_files:
            try:
                cache_file.unlink()
                cleared_count += 1
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete cache file {cache_file}: {e}")
        
        logger.info(f"🗑️ Cleared {cleared_count} cache files")
        return {
            "cleared": cleared_count,
            "total_found": len(cache_files),
            "message": f"Cleared {cleared_count} cache files"
        }


# Global extractor instance
extractor = DocumentExtractor()