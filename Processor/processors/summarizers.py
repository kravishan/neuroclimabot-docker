"""
Consolidated Document Summarizers - Updated for News Articles

"""

import requests
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from models import SummaryData
from config import config

logger = logging.getLogger(__name__)


class BaseSummarizer(ABC):
    """Base class for document summarizers"""
    
    def __init__(self):
        self.ollama_config = config.get('ollama')
        self.api_url = self.ollama_config["api_url"]
        self.model = self.ollama_config["model"]
        self.timeout = self.ollama_config["timeout"]
        self.headers = self.ollama_config["headers"]
        
        logger.info(f"Initialized {self.__class__.__name__} with model: {self.model}")
    
    @abstractmethod
    def get_bucket_type(self) -> str:
        """Get the bucket type this summarizer handles"""
        pass
    
    @abstractmethod
    def prepare_content(self, extracted_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Prepare content for summarization"""
        pass
    
    def create_summary(self, extracted_content: Dict[str, Any], filename: str, bucket: str) -> Optional[SummaryData]:
        """Generate summary for the document"""
        try:
            # Prepare content using bucket-specific logic
            prepared_content = self.prepare_content(extracted_content, filename)
            
            # Get file type
            file_type = extracted_content.get("file_type", "unknown")
            
            # Different minimum lengths based on file type and processing
            if file_type == "pdf":
                min_length = 50
            elif file_type in ["excel", "csv", "excel_article"]:
                min_length = 30
            else:
                min_length = 100
            
            prepared_text_length = len(prepared_content["prepared_text"])
            
            if prepared_text_length < min_length:
                logger.warning(f"Document {filename} too short for meaningful summarization ({prepared_text_length} chars, min: {min_length})")
                
                # For very short content, try to create a basic summary anyway
                if prepared_text_length >= 20:
                    logger.info(f"Attempting minimal summary for {filename}")
                    summary_text = self._create_minimal_summary(prepared_content["prepared_text"], filename, file_type)
                else:
                    return None
            else:
                # Generate full summary
                summary_text = self._generate_llm_summary(prepared_content["prepared_text"], bucket, filename)
                
                # Fallback if LLM summary is too short
                if len(summary_text.strip()) < 50:
                    logger.warning(f"LLM summary too short for {filename}, creating minimal summary")
                    summary_text = self._create_minimal_summary(prepared_content["prepared_text"], filename, file_type)
            
            # Extract metadata
            metadata = self._extract_document_metadata(extracted_content, prepared_content, filename)
            
            # Create SummaryData object
            return SummaryData(
                doc_name=filename,
                bucket_source=bucket,
                document_type=self._get_document_type(),
                abstractive_summary=summary_text,
                document_metadata=metadata,
                processing_info={
                    "model_used": self.model,
                    "summarization_method": self._get_summarization_method(),
                    "summary_length": len(summary_text),
                    "text_length_processed": prepared_text_length,
                    "specialized_summarizer": self.__class__.__name__,
                    "file_type": file_type
                },
                processing_timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"❌ Summarization error for {filename}: {e}")
            return None
    
    def _create_minimal_summary(self, text: str, filename: str, file_type: str) -> str:
        """Create minimal summary for very short content"""
        text = text.strip()
        
        if len(text) < 20:
            return f"Document '{filename}' contains minimal content ({len(text)} characters)."
        
        # Extract first meaningful sentence or portion
        sentences = text.split('.')
        if len(sentences) > 1 and sentences[0].strip():
            summary = sentences[0].strip() + "."
        else:
            # Take first 200 characters
            summary = text[:200].strip()
            if not summary.endswith('.'):
                summary += "."
        
        # Add context
        context_prefix = f"This {file_type} document"
        if filename:
            context_prefix = f"The document '{filename}'"
        
        return f"{context_prefix} contains: {summary}"
    
    def _generate_llm_summary(self, text: str, bucket: str, filename: str = "") -> str:
        """Generate summary using Ollama API"""
        
        # Get summarization config for bucket
        summary_config = config.get_summarization_config(bucket)
        
        # Create prompt using template
        template = summary_config.get('template', config.get('summarization.default.template'))
        prompt = template.format(content=text)
        
        # Build payload
        payload = config.get_ollama_payload(prompt, bucket)
        
        try:
            logger.info(f"🤖 Generating LLM summary for {filename}")

            response = requests.post(
                self.api_url,
                json=payload,
                timeout=float(self.timeout),
                headers=self.headers
            )
            
            if response.status_code == 200:
                result = response.json()
                summary = result.get("response", "").strip()
                
                if not summary:
                    raise Exception("Empty response from Ollama")
                
                cleaned_summary = self._clean_summary(summary)
                logger.info(f"✅ LLM summary generated: {len(cleaned_summary)} characters")
                return cleaned_summary
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Ollama summarization error: {e}")
            logger.info(f"🔄 Falling back to extractive summary for {filename}")
            return self._create_fallback_summary(text, filename)
    
    def _clean_summary(self, summary: str) -> str:
        """Clean generated summary"""
        # Remove common prefixes
        prefixes = ["Summary:", "Document summary:", "The document", "This document", "This research", "This policy", "This article", "This news"]
        for prefix in prefixes:
            if summary.lower().startswith(prefix.lower()):
                summary = summary[len(prefix):].strip()
                if summary.startswith(':'):
                    summary = summary[1:].strip()
                break
        
        # Ensure proper capitalization
        if summary and not summary[0].isupper():
            summary = summary[0].upper() + summary[1:]
        
        # Ensure proper ending
        if summary and not summary.endswith(('.', '!', '?')):
            summary += "."
        
        return summary
    
    def _create_fallback_summary(self, text: str, filename: str = "") -> str:
        """Create fallback summary when API fails"""
        logger.info(f"📝 Creating fallback extractive summary for {filename}")
        
        # Simple extractive summary - take first few sentences
        sentences = text.split('.')
        meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        if meaningful_sentences:
            # Take first 3-4 sentences or up to 300 characters
            summary_parts = []
            char_count = 0
            
            for sentence in meaningful_sentences[:4]:
                if char_count + len(sentence) > 300:
                    break
                summary_parts.append(sentence)
                char_count += len(sentence)
            
            if summary_parts:
                fallback_summary = ". ".join(summary_parts) + "."
                logger.info(f"✅ Fallback summary created: {len(fallback_summary)} characters")
                return fallback_summary
        
        # Last resort - truncated text
        truncated = text[:200].strip()
        if not truncated.endswith('.'):
            truncated += "..."
        
        return f"Document summary: {truncated}"
    
    def _extract_document_metadata(self, extracted_content: Dict[str, Any], prepared_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Extract document metadata"""
        
        full_text = extracted_content.get("full_text", "")
        
        metadata = {
            "title": extracted_content.get("title") or filename,
            "file_type": extracted_content.get("file_type", "unknown"),
            "word_count": len(full_text.split()) if full_text else 0,
            "page_count": 1,
            "section_count": len(extracted_content.get("tables", [])) + len(extracted_content.get("figures", [])),
            "tables_count": len(extracted_content.get("tables", [])),
            "figures_count": len(extracted_content.get("figures", [])),
            "elements_count": extracted_content.get("elements_count", 0)
        }
        
        # Add source_url for news articles
        if extracted_content.get("source_url"):
            metadata["source_url"] = extracted_content["source_url"]
        
        # Add additional news-specific metadata
        if extracted_content.get("type") == "news_article":
            metadata.update({
                "article_link": extracted_content.get("article_link", ""),
                "source_info": extracted_content.get("source_info", ""),
                "row_index": extracted_content.get("row_index", 0),
                "original_file": extracted_content.get("original_file", "")
            })
        
        return metadata
    
    @abstractmethod
    def _get_document_type(self) -> str:
        """Get document type"""
        pass
    
    @abstractmethod
    def _get_summarization_method(self) -> str:
        """Get summarization method description"""
        pass


class NewsArticleSummarizer(BaseSummarizer):
    """Enhanced summarizer for news articles with support for individual Excel articles"""
    
    def get_bucket_type(self) -> str:
        """Get the bucket type this summarizer handles"""
        return "news"
    
    def prepare_content(self, extracted_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Prepare news article content for summarization"""
        
        # Handle individual news articles from Excel
        if extracted_content.get("type") == "news_article":
            return self._prepare_individual_article(extracted_content, filename)
        
        # Handle regular news content (Excel collections, PDFs, etc.)
        full_text = extracted_content.get("full_text", "")
        sections = extracted_content.get("sections", [])
        tables = extracted_content.get("tables", [])
        
        content_parts = []
        
        # Add title with context
        if filename:
            content_parts.append(f"News Content: {filename}")
        
        # Add file type context
        file_type = extracted_content.get("file_type", "unknown")
        if file_type == "excel":
            content_parts.append("Content Type: Excel file containing multiple news articles")
        elif file_type == "csv":
            content_parts.append("Content Type: CSV file with news article data")
        
        # Process tables (likely containing article data)
        if tables:
            content_parts.append(f"Article Structure: {len(tables)} data table(s) containing news articles and metadata")
            
            # Include sample content
            for i, table in enumerate(tables[:2], 1):
                table_content = table.get("content", "")
                if table_content:
                    if len(table_content) > 400:
                        table_content = table_content[:400] + "..."
                    content_parts.append(f"News Data {i}: {table_content}")
        
        # Add sections
        for section in sections[:4]:
            section_content = " ".join(section.get("content", []))
            if len(section_content) > 100:
                content_parts.append(f"{section.get('title', 'Section')}: {section_content}")
        
        # Add main text
        if full_text and len(full_text.strip()) > 100:
            content_parts.append(f"Content: {full_text}")
        
        # Combine all content
        prepared_text = "\n\n".join(content_parts)
        
        # Optimize length
        prepared_text = self._truncate_text(prepared_text, max_words=4000)
        
        # Analyze news characteristics
        news_analysis = self._analyze_news_content(full_text)
        
        return {
            "prepared_text": prepared_text,
            "title": filename,
            "word_count": len(prepared_text.split()),
            "news_analysis": news_analysis,
            "article_count": len(tables),
            "coverage_topics": self._identify_coverage_topics(full_text)
        }
    
    def _prepare_individual_article(self, extracted_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Prepare content for individual news article from Excel"""
        
        article_content = extracted_content.get("full_text", "")
        title = extracted_content.get("title", "")
        source_url = extracted_content.get("source_url", "")
        source_info = extracted_content.get("source_info", "")
        
        # Create focused content for individual article summarization
        content_parts = []
        
        # Add title if available
        if title:
            content_parts.append(f"Article Title: {title}")
        
        # Add source context if available
        if source_info:
            content_parts.append(f"Source: {source_info}")
        
        # Add main article content
        if article_content:
            content_parts.append(f"Article Content: {article_content}")
        
        # Combine content
        prepared_text = "\n\n".join(content_parts)
        
        # Limit length for LLM processing
        prepared_text = self._truncate_text(prepared_text, max_words=3000)
        
        return {
            "prepared_text": prepared_text,
            "title": title or filename,
            "word_count": len(prepared_text.split()),
            "is_individual_article": True,
            "source_url": source_url,
            "source_info": source_info,
            "article_analysis": self._analyze_article_content(article_content)
        }
    
    def _analyze_news_content(self, text: str) -> Dict[str, Any]:
        """Analyze news content characteristics"""
        text_lower = text.lower()
        
        return {
            "has_dates": bool(any(term in text_lower for term in ["2023", "2024", "2025", "january", "february", "march"])),
            "has_locations": bool(any(term in text_lower for term in ["country", "city", "region", "state"])),
            "has_sources": bool(any(term in text_lower for term in ["source", "publication", "outlet", "news"])),
            "has_agriculture_content": bool(any(term in text_lower for term in ["agriculture", "farming", "crop", "food"]))
        }
    
    def _analyze_article_content(self, content: str) -> Dict[str, Any]:
        """Analyze individual article content"""
        if not content:
            return {}
        
        content_lower = content.lower()
        
        # Detect article themes
        themes = []
        theme_keywords = {
            "agriculture": ["agriculture", "farming", "crop", "food", "agricultural", "harvest"],
            "politics": ["election", "government", "policy", "parliament", "minister", "political"],
            "economy": ["economy", "market", "finance", "trade", "business", "economic"],
            "environment": ["climate", "environment", "pollution", "sustainability", "environmental"],
            "technology": ["technology", "digital", "innovation", "tech", "technological"],
            "health": ["health", "medical", "hospital", "disease", "healthcare"],
            "international": ["international", "global", "world", "foreign", "countries"]
        }
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                themes.append(theme)
        
        return {
            "themes": themes[:3],  # Top 3 themes
            "word_count": len(content.split()),
            "estimated_reading_time": f"{len(content.split()) // 200 + 1} minutes",
            "has_quotes": '"' in content or "'" in content,
            "has_numbers": any(char.isdigit() for char in content)
        }
    
    def _identify_coverage_topics(self, text: str) -> List[str]:
        """Identify main topics covered in news articles"""
        text_lower = text.lower()
        
        topics = []
        
        topic_keywords = {
            "agriculture": ["agriculture", "farming", "crop", "food", "agricultural"],
            "politics": ["election", "government", "policy", "parliament", "minister"],
            "economy": ["economy", "market", "finance", "trade", "business"],
            "environment": ["climate", "environment", "pollution", "sustainability"],
            "technology": ["technology", "digital", "innovation", "tech"],
            "health": ["health", "medical", "hospital", "disease"],
            "international": ["international", "global", "world", "foreign"]
        }
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return topics[:5]  # Return top 5 topics
    
    def _truncate_text(self, text: str, max_words: int) -> str:
        """Truncate text to maximum word count"""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
    
    def _get_document_type(self) -> str:
        """Get document type"""
        return "news_article"
    
    def _get_summarization_method(self) -> str:
        """Get summarization method description"""
        return "news_article_focused_summarization"

class ResearchPaperSummarizer(BaseSummarizer):
    """Specialized summarizer for research papers"""
    
    def get_bucket_type(self) -> str:
        return "researchpapers"
    
    def prepare_content(self, extracted_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        # Implementation same as before
        full_text = extracted_content.get("full_text", "")
        prepared_text = self._truncate_text(full_text, max_words=4000)
        
        return {
            "prepared_text": prepared_text,
            "title": filename,
            "word_count": len(prepared_text.split())
        }
    
    def _truncate_text(self, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
    
    def _get_document_type(self) -> str:
        return "research_paper"
    
    def _get_summarization_method(self) -> str:
        return "research_paper_focused_summarization"


class PolicyDocumentSummarizer(BaseSummarizer):
    """Specialized summarizer for policy documents"""
    
    def get_bucket_type(self) -> str:
        return "policy"
    
    def prepare_content(self, extracted_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        full_text = extracted_content.get("full_text", "")
        prepared_text = self._truncate_text(full_text, max_words=4500)
        
        return {
            "prepared_text": prepared_text,
            "title": filename,
            "word_count": len(prepared_text.split())
        }
    
    def _truncate_text(self, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
    
    def _get_document_type(self) -> str:
        return "policy_document"
    
    def _get_summarization_method(self) -> str:
        return "policy_focused_summarization"


class ScientificDataSummarizer(BaseSummarizer):
    """Specialized summarizer for scientific data documents"""
    
    def get_bucket_type(self) -> str:
        return "scientificdata"
    
    def prepare_content(self, extracted_content: Dict[str, Any], filename: str) -> Dict[str, Any]:
        full_text = extracted_content.get("full_text", "")
        prepared_text = self._truncate_text(full_text, max_words=4500)
        
        return {
            "prepared_text": prepared_text,
            "title": filename,
            "word_count": len(prepared_text.split())
        }
    
    def _truncate_text(self, text: str, max_words: int) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
    
    def _get_document_type(self) -> str:
        return "scientific_data"
    
    def _get_summarization_method(self) -> str:
        return "scientific_data_focused_summarization"


# Summarizer Factory
class SummarizerFactory:
    """Factory for creating appropriate summarizers based on bucket type"""
    
    _summarizers = {
        "researchpapers": ResearchPaperSummarizer,
        "policy": PolicyDocumentSummarizer,
        "scientificdata": ScientificDataSummarizer,
        "news": NewsArticleSummarizer
    }
    
    @classmethod
    def get_summarizer(cls, bucket: str) -> BaseSummarizer:
        """Get appropriate summarizer for bucket type"""
        summarizer_class = cls._summarizers.get(bucket)
        
        if summarizer_class:
            return summarizer_class()
        else:
            logger.warning(f"No specialized summarizer for bucket {bucket}, using news as default")
            return NewsArticleSummarizer()
    
    @classmethod
    def get_available_summarizers(cls) -> List[str]:
        """Get list of available summarizer types"""
        return list(cls._summarizers.keys())