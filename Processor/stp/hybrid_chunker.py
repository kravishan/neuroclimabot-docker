"""
HybridChunker - API-only semantic document chunker
Combines Unstructured API extraction with cross-segment boundary classification
"""

import io
import re
import requests
import pandas as pd
import numpy as np
import tiktoken
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from config import config

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
except ImportError:
    pass


class HybridChunker:
    """
    API-only hybrid document chunker that combines:
    1. Unstructured API extraction
    2. Reference removal
    3. Sentence merging
    4. Cross-segment boundary classification with DistilBERT
    5. Text cleaning with ftfy + wordninja
    """
    
    def __init__(self, 
                 api_url: str = "http://localhost:8000",
                 min_chunk_tokens: int = 200,
                 max_chunk_tokens: int = 1500,
                 target_chunk_tokens: int = 800,
                 strategy: str = "hi_res",
                 pdf_infer_table_structure: bool = True,
                 boundary_threshold: float = 0.6,
                 enable_text_cleaning: bool = True,
                 min_word_length_for_splitting: int = 6,
                 cross_segment_model: str = "BlueOrangeDigital/distilbert-cross-segment-document-chunking"):
        
        self.api_url = api_url
        self.min_chunk_tokens = min_chunk_tokens
        self.max_chunk_tokens = max_chunk_tokens
        self.target_chunk_tokens = target_chunk_tokens
        self.boundary_threshold = boundary_threshold
        self.cross_segment_model = cross_segment_model
        
        # Unstructured API parameters
        self.api_params = {
            'strategy': strategy,
            'pdf_infer_table_structure': pdf_infer_table_structure,
            'coordinates': True,
            'multipage_sections': True,
            'include_page_breaks': True,
            'encoding': 'utf-8'
        }
        
        # Initialize tokenizer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Initialize cross-segment boundary classifier
        self._load_cross_segment_model()
        
        # Initialize text cleaner
        self.enable_text_cleaning = enable_text_cleaning
        if self.enable_text_cleaning:
            from stp.text_fixer import ProductionTextCleaner
            self.text_cleaner = ProductionTextCleaner(
                min_word_length=min_word_length_for_splitting,
                verbose=False
            )
        else:
            self.text_cleaner = None
        
        print(f"✓ HybridChunker initialized (API-only mode)")
        print(f"  API URL: {api_url}")
        print(f"  Target chunk tokens: {target_chunk_tokens}")
        print(f"  Text cleaning: {enable_text_cleaning}")
    
    def _load_cross_segment_model(self):
        """Load the DistilBERT cross-segment boundary classification model"""
        if not TRANSFORMERS_AVAILABLE:
            print("⚠️ Transformers not available, using token-based chunking only")
            self.cross_segment_classifier = None
            return
        
        try:
            print(f"Loading {self.cross_segment_model}...")
            
            # Setup local cache directory
            project_dir = Path(__file__).parent.parent
            models_dir = project_dir / "models"
            models_dir.mkdir(exist_ok=True)
            
            # Load tokenizer and model with local caching
            self.boundary_tokenizer = AutoTokenizer.from_pretrained(
                self.cross_segment_model,
                cache_dir=models_dir
            )
            
            self.boundary_model = AutoModelForSequenceClassification.from_pretrained(
                self.cross_segment_model,
                cache_dir=models_dir
            )
            
            # Create classification pipeline
            # Auto-detect GPU: device=0 for CUDA, device=-1 for CPU
            device = 0 if config.is_gpu_available() else -1
            self.cross_segment_classifier = pipeline(
                "text-classification",
                model=self.boundary_model,
                tokenizer=self.boundary_tokenizer,
                device=device,
                top_k=None  # Returns all scores (replaces deprecated return_all_scores=True)
            )
            
            print(f"✓ Cross-segment boundary classifier loaded")
            
        except Exception as e:
            print(f"❌ Failed to load cross-segment model: {e}")
            self.cross_segment_classifier = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.tokenizer.encode(text))
    
    def extract_elements_with_unstructured(self, pdf_bytes: io.BytesIO) -> List:
        """Extract elements from PDF using Unstructured API"""
        print("🔄 Extracting elements with Unstructured API...")
        
        url = f"{self.api_url}/general/v0/general"
        
        files = {
            'files': ('document.pdf', pdf_bytes.getvalue(), 'application/pdf')
        }
        
        # Use configured parameters, filtering out None values
        data = {k: v for k, v in self.api_params.items() if v is not None}
        
        # Convert boolean values to strings for API
        for key, value in data.items():
            if isinstance(value, bool):
                data[key] = str(value).lower()
        
        try:
            response = requests.post(url, files=files, data=data)
            response.raise_for_status()
            
            elements_data = response.json()
            
            # Create element-like objects from the response
            class Element:
                def __init__(self, data):
                    self.text = data.get('text', '')
                    self.category = data.get('type', 'Unknown')
                    self.metadata = data.get('metadata', {})
                    self.coordinates = data.get('coordinates', None)
                
                def __str__(self):
                    return self.text
            
            elements = [Element(elem) for elem in elements_data]
            print(f"✓ Extracted {len(elements)} elements")
            
            return elements
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            raise
    
    def clean_elements(self, elements: List) -> List:
        """Clean text content in extracted elements"""
        if not self.enable_text_cleaning or not self.text_cleaner:
            return elements
        
        print("🧹 Cleaning text in extracted elements...")
        
        cleaned_elements = []
        for element in elements:
            original_text = str(element).strip()
            
            if not original_text:
                cleaned_elements.append(element)
                continue
            
            # Clean the text
            cleaned_text = self.text_cleaner.clean_text(original_text)
            
            # Create new element with cleaned text
            class CleanedElement:
                def __init__(self, original_element, cleaned_text):
                    self.text = cleaned_text
                    self.category = getattr(original_element, 'category', 'Unknown')
                    self.metadata = getattr(original_element, 'metadata', {})
                    self.coordinates = getattr(original_element, 'coordinates', None)
                
                def __str__(self):
                    return self.text
            
            cleaned_elements.append(CleanedElement(element, cleaned_text))
        
        print(f"✅ Element text cleaning complete")
        return cleaned_elements
    
    def remove_references_section(self, elements: List) -> List:
        """Enhanced reference section removal with multiple detection strategies"""
        print("🔄 Removing references section...")
        
        references_start_idx = None
        
        # Try multiple strategies
        strategies = [
            self._find_reference_title,
            self._find_copyright_section,
            self._find_numbered_references,
            self._find_url_heavy_section,
        ]
        
        for strategy in strategies:
            references_start_idx = strategy(elements)
            if references_start_idx is not None:
                break
        
        # Apply filtering
        if references_start_idx is None:
            print("⚠️ No references section found")
            return elements
        else:
            cleaned_elements = elements[:references_start_idx]
            removed_count = len(elements) - references_start_idx
            print(f"✂️ Removed {removed_count} elements from references section")
            return cleaned_elements
    
    def _find_reference_title(self, elements: List) -> Optional[int]:
        """Strategy: Look for explicit reference titles"""
        reference_titles = ['references', 'bibliography', 'works cited']
        start_search_idx = len(elements) // 3
        
        for idx, element in enumerate(elements):
            if idx < start_search_idx:
                continue
            
            element_type = getattr(element, 'category', '')
            text = str(element).strip().lower()
            
            if element_type == 'Title' and any(title in text for title in reference_titles):
                return idx
        
        return None
    
    def _find_copyright_section(self, elements: List) -> Optional[int]:
        """Strategy: Look for copyright notices"""
        copyright_patterns = [
            r'©\s*\d{4}',
            r'copyright\s*©?\s*\d{4}',
            r'all rights reserved'
        ]
        
        start_search_idx = len(elements) // 3
        
        for idx, element in enumerate(elements):
            if idx < start_search_idx:
                continue
            
            text = str(element).strip().lower()
            
            if any(re.search(pattern, text, re.IGNORECASE) for pattern in copyright_patterns):
                return idx
        
        return None
    
    def _find_numbered_references(self, elements: List) -> Optional[int]:
        """Strategy: Look for numbered reference patterns"""
        reference_patterns = [
            r'^\s*\d+\s+[A-Z][a-z]+\s+[A-Z]{2,}.*\d{4}',
            r'^\s*\[\d+\]\s*[A-Z]',
        ]
        
        start_search_idx = len(elements) // 3
        consecutive_refs = 0
        potential_start = None
        
        for idx, element in enumerate(elements):
            if idx < start_search_idx:
                continue
            
            text = str(element).strip()
            is_reference = any(re.match(pattern, text, re.IGNORECASE) for pattern in reference_patterns)
            
            if is_reference:
                if potential_start is None:
                    potential_start = idx
                consecutive_refs += 1
            else:
                if consecutive_refs >= 2:
                    return potential_start
                consecutive_refs = 0
                potential_start = None
        
        if consecutive_refs >= 2 and potential_start is not None:
            return potential_start
        
        return None
    
    def _find_url_heavy_section(self, elements: List) -> Optional[int]:
        """Strategy: Look for URL-heavy sections"""
        url_pattern = r'https?://|www\.|doi:'
        start_search_idx = len(elements) // 3
        
        for idx in range(start_search_idx, len(elements) - 2):
            url_count = 0
            for j in range(3):
                if idx + j < len(elements):
                    text = str(elements[idx + j]).strip()
                    if re.search(url_pattern, text, re.IGNORECASE):
                        url_count += 1
            
            if url_count >= 2:
                return idx
        
        return None
    
    def elements_to_dataframe(self, elements: List) -> pd.DataFrame:
        """Convert elements to DataFrame and clean"""
        print("🔄 Converting elements to DataFrame...")
        
        extracted_data = []
        
        for idx, element in enumerate(elements):
            element_type = getattr(element, 'category', '')
            element_text = str(element).strip()
            
            # Skip certain element types
            if element_type in ['PageBreak', 'Image', 'Header', 'Footer']:
                continue
            
            if not element_text:
                continue
            
            # Extract metadata
            metadata = getattr(element, 'metadata', {})
            page_number = metadata.get('page_number', '') if isinstance(metadata, dict) else ''
            
            extracted_data.append({
                'element_index': idx,
                'type': element_type,
                'text': element_text,
                'text_length': len(element_text),
                'page_number': page_number,
                'is_clean': True
            })
        
        df = pd.DataFrame(extracted_data)
        print(f"✓ Created DataFrame with {len(df)} elements")
        return df
    
    def merge_split_sentences(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge elements where sentences are cut in the middle"""
        print("🔄 Merging split sentences...")
        
        if len(df) == 0:
            return df
        
        merged_data = []
        i = 0
        merge_count = 0
        
        while i < len(df):
            current_row = df.iloc[i].copy()
            current_text = current_row['text'].strip()
            
            # Check if current text needs merging with next element(s)
            merge_indices = [i]
            j = i + 1
            
            while j < len(df) and self._should_merge_with_next(current_text, df.iloc[j]['text'].strip()):
                merge_indices.append(j)
                current_text = current_text + " " + df.iloc[j]['text'].strip()
                j += 1
            
            # If we found elements to merge
            if len(merge_indices) > 1:
                merged_row = self._merge_text_elements(df.iloc[merge_indices])
                merged_data.append(merged_row)
                merge_count += len(merge_indices) - 1
                i = j
            else:
                merged_data.append(current_row)
                i += 1
        
        merged_df = pd.DataFrame(merged_data).reset_index(drop=True)
        print(f"✅ Merged {merge_count} split elements")
        return merged_df
    
    def _should_merge_with_next(self, current_text: str, next_text: str) -> bool:
        """Determine if current text should be merged with next text"""
        if not current_text or not next_text:
            return False
        
        current_text = current_text.strip()
        next_text = next_text.strip()
        
        # Current text ends with a hyphen (word break)
        if current_text.endswith('-'):
            return True
        
        # Current text ends with incomplete sentence patterns
        incomplete_endings = [',', ';', ':', 'and', 'or', 'but', 'the', 'of']
        
        for pattern in incomplete_endings:
            if current_text.lower().endswith(pattern):
                return True
        
        # Current text doesn't end with sentence terminators
        sentence_endings = ['.', '!', '?']
        if not any(current_text.endswith(ending) for ending in sentence_endings):
            words = current_text.split()
            if len(words) <= 3 or not current_text[0].isupper():
                return True
        
        # Next text starts with lowercase (continuation)
        if next_text and next_text[0].islower():
            return True
        
        return False
    
    def _merge_text_elements(self, elements_group):
        """Merge a group of text elements into a single element"""
        if len(elements_group) == 1:
            return elements_group.iloc[0]
        
        merged = elements_group.iloc[0].copy()
        merged_text = merged['text'].strip()
        
        for i in range(1, len(elements_group)):
            next_text = elements_group.iloc[i]['text'].strip()
            
            if merged_text.endswith('-'):
                merged_text = merged_text[:-1] + next_text
            else:
                merged_text = merged_text + " " + next_text
        
        merged['text'] = merged_text
        merged['text_length'] = len(merged_text)
        
        return merged
    
    def cross_segment_chunking(self, df: pd.DataFrame) -> List[Dict]:
        """Apply cross-segment boundary classification to create chunks"""
        print("🔄 Applying cross-segment boundary classification...")
        
        # Extract sentences from DataFrame elements
        sentences_data = self._extract_sentences_from_dataframe(df)
        
        if len(sentences_data) == 0:
            print("❌ No sentences extracted")
            return []
        
        print(f"📝 Extracted {len(sentences_data)} sentences")
        
        # Classify boundaries between sentences
        boundary_scores = self._classify_segment_boundaries(sentences_data)
        
        # Create chunks based on boundary classifications
        chunks = self._create_chunks_from_boundaries(sentences_data, boundary_scores, df)
        
        print(f"✅ Created {len(chunks)} chunks")
        
        return chunks
    
    def _extract_sentences_from_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """Extract sentences from DataFrame elements"""
        sentences_data = []
        
        for idx, row in df.iterrows():
            text = row['text']
            
            try:
                sentences = sent_tokenize(text)
            except:
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
                sentences = [s.strip() for s in sentences if s.strip()]
            
            for sent_idx, sentence in enumerate(sentences):
                sentence = sentence.strip()
                
                if len(sentence) > 15 and len(sentence.split()) > 2:
                    sentence_data = {
                        'original_element_idx': idx,
                        'sentence_idx': sent_idx,
                        'sentence': sentence,
                        'element_type': row['type'],
                        'page_number': row['page_number'],
                    }
                    sentences_data.append(sentence_data)
        
        return sentences_data
    
    def _classify_segment_boundaries(self, sentences_data: List[Dict]) -> List[float]:
        """Classify potential boundaries between sentences"""
        if not self.cross_segment_classifier:
            # Return neutral scores if classifier unavailable
            return [0.5] * max(0, len(sentences_data) - 1)
        
        boundary_scores = []
        
        for i in range(len(sentences_data) - 1):
            current_sentence = sentences_data[i]['sentence'][:200]
            next_sentence = sentences_data[i + 1]['sentence'][:200]
            
            segment_pair = f"{current_sentence} [SEP] {next_sentence}"
            
            try:
                result = self.cross_segment_classifier(segment_pair)
                
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], list):
                        boundary_score = max([score['score'] for score in result[0] 
                                            if 'boundary' in score['label'].lower() or 
                                               score['label'] == 'LABEL_1'])
                    else:
                        boundary_score = result[0]['score'] if result[0]['label'] == 'LABEL_1' else 1 - result[0]['score']
                else:
                    boundary_score = 0.5
                    
                boundary_scores.append(boundary_score)
                
            except Exception:
                boundary_scores.append(0.5)
        
        return boundary_scores
    
    def _create_chunks_from_boundaries(self, sentences_data: List[Dict], 
                                       boundary_scores: List[float], df: pd.DataFrame) -> List[Dict]:
        """Create chunks based on boundary classification scores"""
        chunks = []
        current_chunk_sentences = []
        current_tokens = 0
        
        for i, sentence_data in enumerate(sentences_data):
            sentence = sentence_data['sentence']
            sentence_tokens = self.count_tokens(sentence)
            
            current_chunk_sentences.append(i)
            current_tokens += sentence_tokens
            
            should_split = False
            
            if i < len(boundary_scores):
                boundary_score = boundary_scores[i]
                
                if (boundary_score > self.boundary_threshold and 
                    current_tokens >= self.min_chunk_tokens):
                    should_split = True
                elif current_tokens >= self.max_chunk_tokens:
                    should_split = True
            elif i == len(sentences_data) - 1:
                should_split = True
            
            if should_split and current_chunk_sentences:
                if current_tokens >= self.min_chunk_tokens:
                    chunk = self._finalize_chunk(current_chunk_sentences, sentences_data, df)
                    chunks.append(chunk)
                    current_chunk_sentences = []
                    current_tokens = 0
                elif i == len(sentences_data) - 1 and chunks:
                    chunks[-1]['sentence_indices'].extend(current_chunk_sentences)
                    chunks[-1] = self._finalize_chunk(chunks[-1]['sentence_indices'], sentences_data, df)
        
        return chunks
    
    def _finalize_chunk(self, sentence_indices: List[int], 
                       sentences_data: List[Dict], df: pd.DataFrame) -> Dict:
        """Finalize a chunk from sentence indices"""
        chunk_sentences = [sentences_data[i]['sentence'] for i in sentence_indices]
        chunk_text = ' '.join(chunk_sentences)
        
        element_indices = list(set(sentences_data[i]['original_element_idx'] for i in sentence_indices))
        element_indices.sort()
        
        chunk_elements = df.iloc[element_indices]
        
        chunk = {
            'content': chunk_text,
            'token_count': self.count_tokens(chunk_text),
            'sentence_count': len(sentence_indices),
            'element_count': len(element_indices),
            'sentence_indices': sentence_indices,
            'element_indices': element_indices,
            'page_range': f"{chunk_elements['page_number'].min()}-{chunk_elements['page_number'].max()}" if not chunk_elements['page_number'].isna().all() else "unknown",
            'element_types': chunk_elements['type'].value_counts().to_dict(),
            'chunking_method': 'hybrid_cross_segment_api',
            'is_clean': True
        }
        
        return chunk
    
    def process_document(self, minio_client, bucket_name: str, object_name: str) -> List[Dict]:
        """Process a document through the complete hybrid pipeline"""
        print(f"🚀 Processing document: {object_name}")
        
        # Fetch document from MinIO
        response = minio_client.get_object(bucket_name, object_name)
        pdf_bytes = io.BytesIO(response.read())
        
        # Step 1: Extract elements
        elements = self.extract_elements_with_unstructured(pdf_bytes)
        
        # Step 2: Clean elements
        cleaned_elements = self.clean_elements(elements)
        
        # Step 3: Remove references
        cleaned_elements = self.remove_references_section(cleaned_elements)
        
        # Step 4: Convert to DataFrame
        df = self.elements_to_dataframe(cleaned_elements)
        
        # Step 5: Merge split sentences
        merged_df = self.merge_split_sentences(df)
        
        # Step 6: Apply cross-segment chunking
        chunks = self.cross_segment_chunking(merged_df)
        
        # Add document metadata
        for chunk in chunks:
            chunk.update({
                'document_name': object_name,
                'source_bucket': bucket_name,
                'chunking_timestamp': datetime.now().isoformat(),
                'global_chunk_id': f"{object_name}_{len(chunks)}_{chunks.index(chunk) + 1:03d}",
                'source_document': object_name
            })
        
        print(f"✅ Pipeline completed: {len(chunks)} chunks created")
        return chunks
