"""
Consolidated Document Chunkers
All chunking strategies in one clean file
"""

import uuid
import logging
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
from langchain.text_splitter import RecursiveCharacterTextSplitter

from models import ChunkData
from config import config

logger = logging.getLogger(__name__)


class BaseChunker(ABC):
    """Base class for all document chunkers"""
    
    def __init__(self):
        self.config = self.get_config()
        logger.info(f"Initialized {self.__class__.__name__} with config: {self.config}")
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get chunker-specific configuration"""
        pass
    
    @abstractmethod
    def create_chunks(self, elements: List[Dict[str, Any]], 
                     filename: str, bucket: str) -> List[ChunkData]:
        """Create chunks from extracted elements"""
        pass
    
    def _create_chunk_data(self, chunk_text: str, filename: str, bucket: str, 
                          chunk_index: int, metadata: Dict[str, Any]) -> ChunkData:
        """Create ChunkData object with common fields"""
        return ChunkData(
            chunk_id=str(uuid.uuid4()),
            doc_name=filename,
            bucket_source=bucket,
            chunk_text=chunk_text,
            chunk_index=chunk_index,
            token_count=len(chunk_text.split()),
            processing_timestamp=datetime.now().isoformat(),
            chunk_metadata=metadata
        )
    
    def _categorize_elements(self, elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize elements by type for processing"""
        categories = {
            "tables": [],
            "headers": [],
            "text": [],
            "figures": [],
            "other": []
        }
        
        for element in elements:
            element_type = element.get("type", "")
            text_content = element.get("text", "")
            
            if not text_content.strip():
                continue
            
            if element_type == "Table":
                categories["tables"].append(element)
            elif element_type == "Title":
                categories["headers"].append(element)
            elif element_type in ["NarrativeText", "ListItem"]:
                categories["text"].append(element)
            elif element_type == "FigureCaption":
                categories["figures"].append(element)
            else:
                categories["other"].append(element)
        
        return categories
    
    def _create_text_splitter(self, chunk_size: int = None, overlap_ratio: float = None,
                             separators: List[str] = None) -> RecursiveCharacterTextSplitter:
        """Create text splitter with configuration"""
        chunk_size = chunk_size or self.config.get("chunk_size", 600)
        overlap_ratio = overlap_ratio or self.config.get("overlap_ratio", 0.15)
        separators = separators or self.config.get("separators", ["\n\n", "\n", ".", " ", ""])
        
        overlap_size = int(chunk_size * overlap_ratio)
        
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap_size,
            separators=separators,
            length_function=len,
            is_separator_regex=False,
            keep_separator=True
        )
    
    def _combine_elements_text(self, elements: List[Dict[str, Any]]) -> str:
        """Combine text from multiple elements"""
        text_parts = []
        
        for element in elements:
            text = element.get("text", "").strip()
            if text:
                text_parts.append(text)
        
        return "\n\n".join(text_parts)
    
    def _process_table_elements(self, table_elements: List[Dict[str, Any]], 
                               filename: str) -> List[Dict[str, Any]]:
        """Process table elements"""
        processed_tables = []
        
        for table_element in table_elements:
            table_text = table_element.get("text", "")
            table_metadata = table_element.get("metadata", {})
            
            if len(table_text.strip()) < 50:
                continue
            
            chunk_metadata = {
                "element_type": "Table",
                "original_metadata": table_metadata,
                "chunk_strategy": "table_preserved",
                "overlap_ratio": 0,
                "priority": "high"
            }
            
            processed_tables.append({
                "text": table_text,
                "metadata": chunk_metadata
            })
        
        return processed_tables
    
    def _process_text_elements(self, text_elements: List[Dict[str, Any]], 
                              chunk_size: int = None, overlap_ratio: float = None) -> List[Dict[str, Any]]:
        """Process text elements with chunking"""
        if not text_elements:
            return []
        
        combined_text = self._combine_elements_text(text_elements)
        
        if not combined_text.strip():
            return []
        
        # Create text splitter
        text_splitter = self._create_text_splitter(chunk_size, overlap_ratio)
        
        # Split text into chunks
        text_chunks = text_splitter.split_text(combined_text)
        
        processed_chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk_metadata = {
                "element_type": "text",
                "chunk_strategy": "recursive_text_splitting",
                "overlap_ratio": overlap_ratio or self.config.get("overlap_ratio", 0.15),
                "chunk_index_in_section": i,
                "priority": "medium"
            }
            
            processed_chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
        
        return processed_chunks
    
    def _process_figure_elements(self, figure_elements: List[Dict[str, Any]], 
                                filename: str) -> List[Dict[str, Any]]:
        """Process figure elements"""
        processed_figures = []
        
        for figure_element in figure_elements:
            figure_text = figure_element.get("text", "")
            figure_metadata = figure_element.get("metadata", {})
            
            if len(figure_text.strip()) < 20:
                continue
            
            chunk_metadata = {
                "element_type": "Figure",
                "original_metadata": figure_metadata,
                "chunk_strategy": "figure_caption_preserved",
                "overlap_ratio": 0,
                "priority": "medium"
            }
            
            processed_figures.append({
                "text": figure_text,
                "metadata": chunk_metadata
            })
        
        return processed_figures
    
    def _finalize_chunks(self, processed_elements: List[Dict[str, Any]], 
                        filename: str, bucket: str) -> List[ChunkData]:
        """Convert processed elements to ChunkData objects"""
        chunks = []
        
        for chunk_index, element in enumerate(processed_elements):
            chunk_text = element.get("text", "")
            chunk_metadata = element.get("metadata", {})
            
            if not chunk_text.strip():
                continue
            
            # Add common metadata
            chunk_metadata.update({
                "specialized_chunker": self.__class__.__name__,
                "total_chunks": len(processed_elements),
                "processing_method": "specialized_chunker"
            })
            
            chunk_data = self._create_chunk_data(
                chunk_text, filename, bucket, chunk_index, chunk_metadata
            )
            chunks.append(chunk_data)
        
        return chunks


class ResearchPaperChunker(BaseChunker):
    """Specialized chunker for research papers following IMRAD structure - EXCLUDES REFERENCES"""
    
    def get_config(self) -> Dict[str, Any]:
        """Get research paper specific configuration"""
        return config.get_chunking_config("researchpapers")
    
    def create_chunks(self, elements: List[Dict[str, Any]], 
                     filename: str, bucket: str) -> List[ChunkData]:
        """Create research paper optimized chunks - COMPLETELY EXCLUDES REFERENCES"""
        
        # Organize elements by IMRAD structure (references will be excluded)
        structured_content = self._organize_by_imrad(elements)
        
        processed_elements = []
        references_excluded = 0
        
        # Process each IMRAD section with specific strategies - SKIP REFERENCES
        section_processors = {
            "abstract": self._process_abstract_section,
            "methodology": self._process_methodology_section,
            "results": self._process_results_section,
            "discussion": self._process_discussion_section,
            "tables": self._process_table_elements,
            "figures": self._process_figure_elements,
            "other": self._process_other_section
            # NOTE: "references" is NOT included in processors - they will be completely excluded
        }
        
        for section_type, section_elements in structured_content.items():
            if not section_elements:
                continue
            
            # Skip references section completely
            if section_type == "references":
                references_excluded = len(section_elements)
                logger.info(f" EXCLUDING {references_excluded} reference elements from {filename}")
                continue
            
            processor = section_processors.get(section_type, self._process_other_section)
            section_chunks = processor(section_elements, filename)
            
            # Add section-specific metadata
            for chunk in section_chunks:
                chunk["metadata"]["section_type"] = section_type
                chunk["metadata"]["imrad_section"] = self._map_to_imrad(section_type)
                chunk["metadata"]["references_excluded"] = True
            
            processed_elements.extend(section_chunks)
        
        # Convert to ChunkData objects
        chunks = self._finalize_chunks(processed_elements, filename, bucket)
        
        logger.info(f"✅ Research paper chunker completed: {len(chunks)} chunks created for {filename}")
        if references_excluded > 0:
            logger.info(f"🚫 EXCLUDED {references_excluded} reference elements to reduce database noise")
        
        return chunks
    
    def _organize_by_imrad(self, elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize elements by IMRAD structure - identifies references for exclusion"""
        
        structured_content = {
            "abstract": [],
            "methodology": [],
            "results": [],
            "discussion": [],
            "tables": [],
            "figures": [],
            "references": [],  # Will be excluded but identified for logging
            "other": []
        }
        
        current_section = "other"
        
        for element in elements:
            element_type = element.get("type", "")
            text = element.get("text", "").strip()
            
            if not text:
                continue
            
            # Identify sections based on titles/headings
            if element_type == "Title":
                current_section = self._classify_section_by_title(text)
                
                # Log when we encounter references section
                if current_section == "references":
                    logger.info(f"🔍 Found reference section: '{text}' - will be excluded from processing")
            
            # Categorize content based on type and current section
            if element_type == "Table":
                if current_section != "references":  # Don't include reference tables
                    structured_content["tables"].append(element)
            elif element_type == "FigureCaption":
                if current_section != "references":  # Don't include reference figures
                    structured_content["figures"].append(element)
            else:
                structured_content[current_section].append(element)
        
        return structured_content
    
    def _classify_section_by_title(self, title: str) -> str:
        """Classify section type based on title - Enhanced reference detection"""
        title_lower = title.lower()
        
        section_keywords = {
            "abstract": ["abstract", "summary", "overview"],
            "methodology": ["method", "methodology", "approach", "procedure", "experimental", "materials"],
            "results": ["result", "finding", "outcome", "analysis", "data"],
            "discussion": ["discussion", "conclusion", "implication", "interpretation"],
            "references": [
                "reference", "references", "bibliography", "bibliographies", 
                "citation", "citations", "literature cited", "works cited",
                "cited literature", "literature", "sources", "bibliography and references"
            ]
        }
        
        for section_type, keywords in section_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return section_type
        
        return "other"
    
    def _process_abstract_section(self, elements: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """Process abstract section with smaller chunks"""
        config = self.get_config()
        return self._process_text_elements(
            elements, 
            chunk_size=config.get("section_sizes", {}).get("abstract", 300),
            overlap_ratio=0.15
        )
    
    def _process_methodology_section(self, elements: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """Process methodology section with medium chunks"""
        config = self.get_config()
        return self._process_text_elements(
            elements,
            chunk_size=config.get("section_sizes", {}).get("methodology", 600),
            overlap_ratio=0.15
        )
    
    def _process_results_section(self, elements: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """Process results section with optimized chunk size"""
        config = self.get_config()
        return self._process_text_elements(
            elements,
            chunk_size=config.get("section_sizes", {}).get("results", 450),
            overlap_ratio=0.15
        )
    
    def _process_discussion_section(self, elements: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """Process discussion section with larger chunks"""
        config = self.get_config()
        return self._process_text_elements(
            elements,
            chunk_size=config["chunk_size"],
            overlap_ratio=0.15
        )
    
    def _process_other_section(self, elements: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """Process other sections with default settings"""
        config = self.get_config()
        return self._process_text_elements(
            elements,
            chunk_size=config["chunk_size"],
            overlap_ratio=config["overlap_ratio"]
        )
    
    def _map_to_imrad(self, section_type: str) -> str:
        """Map section type to IMRAD structure"""
        imrad_mapping = {
            "abstract": "Abstract",
            "methodology": "Methods",
            "results": "Results",
            "discussion": "Discussion",
            "tables": "Results",
            "figures": "Results",
            "other": "Other"
        }
        return imrad_mapping.get(section_type, "Other")


class PolicyDocumentChunker(BaseChunker):
    """Specialized chunker for policy documents with hierarchical structure preservation"""
    
    def get_config(self) -> Dict[str, Any]:
        """Get policy document specific configuration"""
        return config.get_chunking_config("policy")
    
    def create_chunks(self, elements: List[Dict[str, Any]], 
                     filename: str, bucket: str) -> List[ChunkData]:
        """Create policy document optimized chunks with hierarchical structure preservation"""
        
        # Organize elements by policy structure
        structured_content = self._organize_by_policy_structure(elements)
        
        processed_elements = []
        
        # Section priorities for policy documents
        section_priorities = {
            "preamble": "high",
            "definitions": "high", 
            "main_provisions": "high",
            "enforcement": "medium",
            "amendments": "medium",
            "annexes": "low",
            "schedules": "low"
        }
        
        # Process each section type with appropriate strategy
        for section_type, section_elements in structured_content.items():
            if not section_elements:
                continue
            
            priority = section_priorities.get(section_type, "standard")
            
            if section_type == "tables":
                section_chunks = self._process_table_elements(section_elements, filename)
            else:
                section_chunks = self._process_hierarchical_section(section_elements, section_type)
            
            # Add section-specific metadata
            for chunk in section_chunks:
                chunk["metadata"]["section_type"] = section_type
                chunk["metadata"]["priority"] = priority
                chunk["metadata"]["legal_references"] = self._extract_legal_references(chunk["text"])
            
            processed_elements.extend(section_chunks)
        
        # Convert to ChunkData objects
        chunks = self._finalize_chunks(processed_elements, filename, bucket)
        
        logger.info(f"Policy document chunker completed: {len(chunks)} chunks created for {filename}")
        
        return chunks
    
    def _organize_by_policy_structure(self, elements: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Organize elements by policy document structure"""
        
        structured_content = {
            "preamble": [],
            "definitions": [],
            "main_provisions": [],
            "enforcement": [],
            "amendments": [],
            "annexes": [],
            "schedules": [],
            "tables": [],
            "other": []
        }
        
        current_section = "other"
        
        for element in elements:
            element_type = element.get("type", "")
            text = element.get("text", "").strip()
            
            if not text:
                continue
            
            # Identify sections based on titles/headings
            if element_type == "Title":
                current_section = self._classify_policy_section(text)
            
            # Categorize content based on type and current section
            if element_type == "Table":
                structured_content["tables"].append({
                    **element,
                    "parent_section": current_section
                })
            else:
                structured_content[current_section].append(element)
        
        return structured_content
    
    def _classify_policy_section(self, title: str) -> str:
        """Classify policy section type based on title"""
        title_lower = title.lower()
        
        section_keywords = {
            "preamble": ["preamble", "whereas", "considering"],
            "definitions": ["definition", "interpretation", "meaning"],
            "enforcement": ["enforcement", "compliance", "penalty", "sanction"],
            "amendments": ["amendment", "modification", "revision"],
            "annexes": ["annex", "appendix", "attachment"],
            "schedules": ["schedule", "list", "table"]
        }
        
        for section_type, keywords in section_keywords.items():
            if any(keyword in title_lower for keyword in keywords):
                return section_type
        
        return "main_provisions"
    
    def _process_hierarchical_section(self, elements: List[Dict[str, Any]], 
                                    section_type: str) -> List[Dict[str, Any]]:
        """Process section with hierarchical structure preservation"""
        if not elements:
            return []
        
        # Add hierarchical markers to preserve structure
        structured_text_parts = []
        
        for element in elements:
            text = element["text"]
            hierarchy = self._extract_hierarchical_context(text)
            
            # Add structural markers
            if hierarchy["legal_references"]:
                ref_markers = []
                for ref_type, refs in hierarchy["legal_references"].items():
                    if refs:
                        ref_markers.append(f"[{ref_type.upper()}: {', '.join(refs)}]")
                
                if ref_markers:
                    text = " ".join(ref_markers) + " " + text
            
            structured_text_parts.append(text)
        
        # Combine all text for this section
        combined_text = "\n\n".join(structured_text_parts)
        
        # Create chunks with size limits
        chunks = self._create_size_limited_chunks(combined_text)
        
        processed_chunks = []
        for chunk_text in chunks:
            processed_chunks.append({
                "text": chunk_text,
                "metadata": {
                    "chunk_strategy": "hierarchical_structure_preserving",
                    "overlap_ratio": self.config["overlap_ratio"],
                    "element_type": "policy_content",
                    "hierarchical_level": self._assess_hierarchical_level(chunk_text)
                }
            })
        
        return processed_chunks
    
    def _create_size_limited_chunks(self, text: str) -> List[str]:
        """Create chunks within size limits"""
        config = self.get_config()
        text_splitter = self._create_text_splitter()
        initial_chunks = text_splitter.split_text(text)
        
        final_chunks = []
        min_chunk_size = config.get("min_chunk_size", 100)
        max_chunk_size = config.get("max_chunk_size", 1000)
        
        for chunk in initial_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            
            chunk_length = len(chunk)
            
            # If chunk is too small, try to combine with previous chunk
            if (chunk_length < min_chunk_size and 
                final_chunks and 
                len(final_chunks[-1] + "\n\n" + chunk) <= max_chunk_size):
                final_chunks[-1] = final_chunks[-1] + "\n\n" + chunk
                continue
            
            # If chunk is too large, split it further
            if chunk_length > max_chunk_size:
                smaller_splitter = self._create_text_splitter(
                    chunk_size=max_chunk_size,
                    overlap_ratio=config["overlap_ratio"]
                )
                sub_chunks = smaller_splitter.split_text(chunk)
                final_chunks.extend([sc.strip() for sc in sub_chunks if sc.strip()])
            else:
                final_chunks.append(chunk)
        
        return final_chunks
    
    def _extract_legal_references(self, text: str) -> Dict[str, List[str]]:
        """Extract legal structure references from text"""
        legal_patterns = {
            "article": re.compile(r"(?:article|art\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE),
            "section": re.compile(r"(?:section|sec\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE),
            "chapter": re.compile(r"(?:chapter|ch\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE),
            "subsection": re.compile(r"(?:subsection|sub\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE),
            "paragraph": re.compile(r"(?:paragraph|para\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE),
            "clause": re.compile(r"(?:clause|cl\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE),
            "provision": re.compile(r"(?:provision|prov\.?)\s+(\d+(?:\.\d+)*)", re.IGNORECASE)
        }
        
        references = {}
        for ref_type, pattern in legal_patterns.items():
            matches = pattern.findall(text)
            if matches:
                references[ref_type] = list(set(matches))
        
        return references
    
    def _extract_hierarchical_context(self, text: str) -> Dict[str, Any]:
        """Extract hierarchical context from text"""
        legal_references = self._extract_legal_references(text)
        
        hierarchy = {
            "level": 0,
            "legal_references": legal_references,
            "structural_indicators": []
        }
        
        # Determine hierarchical level based on legal references
        level_mapping = {
            "chapter": 1,
            "article": 2,
            "section": 3,
            "subsection": 4,
            "paragraph": 5,
            "clause": 6
        }
        
        for ref_type, level in level_mapping.items():
            if legal_references.get(ref_type):
                hierarchy["level"] = max(hierarchy["level"], level)
                hierarchy["structural_indicators"].append(f"{ref_type}_level")
        
        return hierarchy
    
    def _assess_hierarchical_level(self, text: str) -> int:
        """Assess hierarchical level of text chunk"""
        hierarchy = self._extract_hierarchical_context(text)
        return hierarchy["level"]


class ScientificDataChunker(BaseChunker):
    """Enhanced chunker for scientific data with size limits and smart splitting"""
    
    def get_config(self) -> Dict[str, Any]:
        """Get scientific data specific configuration"""
        return config.get_chunking_config("scientificdata")
    
    def create_chunks(self, elements: List[Dict[str, Any]], 
                     filename: str, bucket: str) -> List[ChunkData]:
        """Create scientific data optimized chunks with size constraints"""
        
        # Categorize elements
        categorized = self._categorize_elements(elements)
        
        processed_elements = []
        
        # Process tables with special handling for large tables
        if categorized["tables"]:
            table_chunks = self._process_large_tables(categorized["tables"], filename)
            for chunk in table_chunks:
                chunk["metadata"]["section_type"] = "scientific_table"
                chunk["metadata"]["priority"] = "high"
            processed_elements.extend(table_chunks)
        
        # Process text elements with size limits
        if categorized["text"]:
            text_chunks = self._process_text_elements_with_limits(categorized["text"])
            for chunk in text_chunks:
                chunk["metadata"]["section_type"] = "scientific_content"
                chunk["metadata"]["priority"] = "medium"
            processed_elements.extend(text_chunks)
        
        # Process headers with size limits
        if categorized["headers"]:
            header_chunks = self._process_text_elements_with_limits(categorized["headers"], chunk_size=400)
            for chunk in header_chunks:
                chunk["metadata"]["section_type"] = "scientific_header"
                chunk["metadata"]["priority"] = "high"
            processed_elements.extend(header_chunks)
        
        # Convert to ChunkData objects
        chunks = self._finalize_chunks(processed_elements, filename, bucket)
        
        # Final size validation and splitting if needed
        validated_chunks = self._validate_and_split_chunks(chunks)
        
        logger.info(f"Scientific data chunker completed: {len(validated_chunks)} chunks created for {filename}")
        
        return validated_chunks
    
    def _process_large_tables(self, table_elements: List[Dict[str, Any]], filename: str) -> List[Dict[str, Any]]:
        """Process table elements with aggressive splitting for small chunks"""
        processed_tables = []
        
        for table_element in table_elements:
            table_text = table_element.get("text", "")
            table_metadata = table_element.get("metadata", {})
            
            if len(table_text.strip()) < 50:
                continue
            
            # Always split large tables into small chunks for better RAG
            if len(table_text) > 800:  # Split anything over 800 chars
                table_chunks = self._split_large_table(table_text, table_metadata)
                processed_tables.extend(table_chunks)
            else:
                # Process small tables normally
                enhanced_table_text = self._enhance_table_text_small(table_text, table_metadata, filename)
                
                # Final size check
                if len(enhanced_table_text) > 950:
                    enhanced_table_text = enhanced_table_text[:950] + "..."
                
                chunk_metadata = {
                    "element_type": "Table",
                    "original_metadata": table_metadata,
                    "chunk_strategy": "small_table_preserved",
                    "overlap_ratio": 0,
                    "priority": "high",
                    "table_size": "small"
                }
                
                processed_tables.append({
                    "text": enhanced_table_text,
                    "metadata": chunk_metadata
                })
        
        return processed_tables
    
    def _split_large_table(self, table_text: str, table_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split tables into very small chunks for better RAG performance"""
        chunks = []
        
        # Split by rows for small chunks
        lines = table_text.split('\n')
        
        # Find header rows (first 2-3 lines usually)
        header_lines = []
        data_lines = []
        
        for i, line in enumerate(lines):
            if i < 3 and line.strip():  # First 3 lines as headers
                header_lines.append(line)
            elif line.strip():
                data_lines.append(line)
        
        # Create header text (keep it minimal)
        header_text = '\n'.join(header_lines)
        
        # Split data into very small chunks (5-10 rows max)
        chunk_size = 5  # Very small chunks
        current_chunk_lines = []
        chunk_index = 0
        
        for i, line in enumerate(data_lines):
            current_chunk_lines.append(line)
            
            # Create chunk when we reach chunk_size or end of data
            if len(current_chunk_lines) >= chunk_size or i == len(data_lines) - 1:
                chunk_text = header_text + '\n' + '\n'.join(current_chunk_lines)
                
                # Ensure chunk is not too large
                if len(chunk_text) > 950:
                    chunk_text = chunk_text[:950] + "..."
                
                chunk_metadata = {
                    "element_type": "Table",
                    "original_metadata": table_metadata,
                    "chunk_strategy": "small_table_split",
                    "overlap_ratio": 0,
                    "priority": "high",
                    "table_size": "split",
                    "chunk_part": chunk_index + 1,
                    "split_method": "small_row_based",
                    "rows_in_chunk": len(current_chunk_lines)
                }
                
                chunks.append({
                    "text": chunk_text,
                    "metadata": chunk_metadata
                })
                
                # Reset for next chunk
                current_chunk_lines = []
                chunk_index += 1
        
        # If still no chunks (very wide table), do character-based splitting
        if not chunks:
            chunks = self._character_based_table_split(table_text, table_metadata)
        
        return chunks
    
    def _character_based_table_split(self, table_text: str, table_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fallback: split table by character count into small chunks"""
        chunks = []
        chunk_size = 800  # Small chunks
        
        current_pos = 0
        chunk_index = 0
        
        while current_pos < len(table_text):
            end_pos = min(current_pos + chunk_size, len(table_text))
            
            # Try to find a good break point (newline, tab, or space)
            if end_pos < len(table_text):
                for i in range(end_pos, max(current_pos + chunk_size - 200, current_pos), -1):
                    if table_text[i] in ['\n', '\t', ' ']:
                        end_pos = i
                        break
            
            chunk_text = table_text[current_pos:end_pos]
            
            # Ensure chunk is not too large
            if len(chunk_text) > 950:
                chunk_text = chunk_text[:950] + "..."
            
            chunk_metadata = {
                "element_type": "Table",
                "original_metadata": table_metadata,
                "chunk_strategy": "small_table_character_split",
                "overlap_ratio": 0,
                "priority": "high",
                "table_size": "character_split",
                "chunk_part": chunk_index + 1,
                "split_method": "character_based"
            }
            
            chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
            
            current_pos = end_pos
            chunk_index += 1
        
        return chunks
    
    def _process_text_elements_with_limits(self, text_elements: List[Dict[str, Any]], 
                                         chunk_size: int = None, overlap_ratio: float = None) -> List[Dict[str, Any]]:
        """Process text elements with strict small size limits"""
        if not text_elements:
            return []
        
        combined_text = self._combine_elements_text(text_elements)
        
        if not combined_text.strip():
            return []
        
        # Use small chunk size for better RAG performance
        config = self.get_config()
        chunk_size = min(chunk_size or config.get("chunk_size", 800), 900)  # Small chunks
        overlap_ratio = overlap_ratio or config.get("overlap_ratio", 0.15)
        
        # Create text splitter with small limits
        text_splitter = self._create_text_splitter(chunk_size, overlap_ratio)
        
        # Split text into chunks
        text_chunks = text_splitter.split_text(combined_text)
        
        processed_chunks = []
        for i, chunk_text in enumerate(text_chunks):
            # Ensure chunk is not too large
            if len(chunk_text) > 950:
                chunk_text = chunk_text[:950] + "..."
            
            chunk_metadata = {
                "element_type": "text",
                "chunk_strategy": "small_size_text_splitting",
                "overlap_ratio": overlap_ratio,
                "chunk_index_in_section": i,
                "priority": "medium",
                "size_limited": True,
                "chunk_size_target": chunk_size
            }
            
            processed_chunks.append({
                "text": chunk_text,
                "metadata": chunk_metadata
            })
        
        return processed_chunks
    
    def _validate_and_split_chunks(self, chunks: List[ChunkData]) -> List[ChunkData]:
        """Final validation and splitting of chunks that are still too large"""
        validated_chunks = []
        
        for chunk in chunks:
            text_length = len(chunk.chunk_text)
            
            if text_length <= 950:  # Small limit for better RAG
                validated_chunks.append(chunk)
            else:
                # Split oversized chunk
                logger.warning(f"Splitting oversized chunk: {text_length} characters")
                split_chunks = self._emergency_split_chunk(chunk)
                validated_chunks.extend(split_chunks)
        
        return validated_chunks
    
    def _emergency_split_chunk(self, chunk: ChunkData) -> List[ChunkData]:
        """Emergency splitting for chunks that are still too large"""
        split_chunks = []
        text = chunk.chunk_text
        chunk_size = 800  # Small conservative size
        
        # Split the text
        parts = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + chunk_size, len(text))
            
            # Try to find a good break point
            if end_pos < len(text):
                for i in range(end_pos, max(current_pos + chunk_size - 100, current_pos), -1):
                    if text[i] in ['\n', '.', '!', '?', '\t', ' ']:
                        end_pos = i
                        break
            
            part_text = text[current_pos:end_pos].strip()
            if part_text:
                # Final size check
                if len(part_text) > 950:
                    part_text = part_text[:950] + "..."
                parts.append(part_text)
            
            current_pos = end_pos
        
        # Create new chunks
        for i, part_text in enumerate(parts):
            # Update metadata to indicate splitting
            new_metadata = chunk.chunk_metadata.copy() if chunk.chunk_metadata else {}
            new_metadata.update({
                "emergency_split": True,
                "split_part": i + 1,
                "total_parts": len(parts),
                "original_chunk_id": chunk.chunk_id,
                "split_reason": "size_limit_exceeded"
            })
            
            new_chunk = ChunkData(
                chunk_id=str(uuid.uuid4()),
                doc_name=chunk.doc_name,
                bucket_source=chunk.bucket_source,
                chunk_text=part_text,
                chunk_index=f"{chunk.chunk_index}_{i}",
                token_count=len(part_text.split()),
                processing_timestamp=datetime.now().isoformat(),
                chunk_metadata=new_metadata
            )
            
            split_chunks.append(new_chunk)
        
        logger.info(f"Emergency split created {len(split_chunks)} small chunks from 1 oversized chunk")
        return split_chunks
    
    def _enhance_table_text_small(self, table_text: str, table_metadata: Dict[str, Any], filename: str) -> str:
        """Enhanced table text optimized for small chunks"""
        
        enhanced_parts = []
        
        # Add minimal table header
        enhanced_parts.append(f"TABLE: {filename}")
        enhanced_parts.append("")
        
        # Add original table content (most important)
        enhanced_parts.append(table_text)
        
        result = "\n".join(enhanced_parts)
        
        # Ensure we don't exceed limits
        if len(result) > 900:
            # Just use raw table text if enhanced version is too large
            if len(table_text) <= 900:
                result = table_text
            else:
                result = table_text[:900] + "..."
        
        return result


class NewsArticleChunker(BaseChunker):
    """Specialized chunker for news articles - simplified implementation"""
    
    def get_config(self) -> Dict[str, Any]:
        """Get news article specific configuration"""
        return config.get_chunking_config("news")
    
    def create_chunks(self, elements: List[Dict[str, Any]], 
                     filename: str, bucket: str) -> List[ChunkData]:
        """Create news article optimized chunks"""
        
        # Categorize elements
        categorized = self._categorize_elements(elements)
        
        processed_elements = []
        
        # Process text elements with news-specific settings
        all_text_elements = []
        all_text_elements.extend(categorized.get("headers", []))
        all_text_elements.extend(categorized.get("text", []))
        
        if all_text_elements:
            # Use news-specific chunk size
            config_obj = self.get_config()
            text_chunks = self._process_text_elements(
                all_text_elements, 
                chunk_size=config_obj["chunk_size"],
                overlap_ratio=config_obj["overlap_ratio"]
            )
            
            for chunk in text_chunks:
                chunk["metadata"]["section_type"] = "news_content"
                chunk["metadata"]["priority"] = "high"
                chunk["metadata"]["chunk_strategy"] = "news_article_aware"
            
            processed_elements.extend(text_chunks)
        
        # Process tables if any
        if categorized.get("tables"):
            table_chunks = self._process_table_elements(categorized["tables"], filename)
            for chunk in table_chunks:
                chunk["metadata"]["section_type"] = "news_table"
                chunk["metadata"]["priority"] = "medium"
            processed_elements.extend(table_chunks)
        
        # Convert to ChunkData objects
        chunks = self._finalize_chunks(processed_elements, filename, bucket)
        
        logger.info(f"News article chunker completed: {len(chunks)} chunks created for {filename}")
        
        return chunks


# Chunker Factory
class ChunkerFactory:
    """Factory for creating appropriate chunkers based on bucket type"""
    
    _chunkers = {
        "researchpapers": ResearchPaperChunker,
        "policy": PolicyDocumentChunker,
        "scientificdata": ScientificDataChunker,
        "news": NewsArticleChunker
    }
    
    @classmethod
    def get_chunker(cls, bucket: str) -> BaseChunker:
        """Get appropriate chunker for bucket type"""
        chunker_class = cls._chunkers.get(bucket)
        
        if chunker_class:
            return chunker_class()
        else:
            logger.warning(f"No specialized chunker for bucket {bucket}, using default")
            return NewsArticleChunker()  # Use news as default
    
    @classmethod
    def get_available_chunkers(cls) -> List[str]:
        """Get list of available chunker types"""
        return list(cls._chunkers.keys())