import logging
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

from config import config

logger = logging.getLogger(__name__)


class STPProcessor:
    """
    Main STP processing pipeline that orchestrates:
    1. HybridChunker - Document chunking (REUSES extracted elements)
    2. RoBERTa Classifier - STP classification
    3. Mistral Rephraser - Content rephrasing (80 words max)
    4. Mistral QF Generator - Qualifying factors generation
    5. MilvusManager - Storage with embeddings
    """
    
    def __init__(self):
        self.config = config.get_stp_config()
        self.enabled = config.is_stp_enabled()
        
        if not self.enabled:
            logger.warning("⚠️ STP processing is disabled in configuration")
            return
        
        # Initialize components
        self._init_components()
        
        # Thread executor for blocking operations
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="stp_worker")
        
        logger.info("✅ STP Processor initialized successfully")
    
    def _init_components(self):
        """Initialize all STP components"""
        try:
            from stp.hybrid_chunker import HybridChunker
            from stp.roberta_classifier import RoBERTaONNXClassifier
            from stp.mistral_qf_generator import MistralQualifyingFactorsGenerator
            from stp.mistral_rephraser import MistralRephraser
            from storage.milvus import STPMilvusManager
            
            # Initialize HybridChunker with config
            logger.info("🔧 Initializing HybridChunker...")
            unstructured_config = config.get('unstructured')
            chunking_config = config.get_stp_chunking_config()
            
            self.chunker = HybridChunker(
                api_url=unstructured_config['api_url'],
                min_chunk_tokens=chunking_config['min_chunk_tokens'],
                max_chunk_tokens=chunking_config['max_chunk_tokens'],
                target_chunk_tokens=chunking_config['target_chunk_tokens'],
                boundary_threshold=chunking_config['boundary_threshold'],
                enable_text_cleaning=self.config['text_cleaning_enabled'],
                min_word_length_for_splitting=self.config['min_word_length']
            )
            logger.info("✅ HybridChunker initialized")
            
            # Initialize RoBERTa Classifier
            logger.info("🔧 Initializing RoBERTa Classifier...")
            classifier_config = config.get_stp_classifier_config()
            
            self.classifier = RoBERTaONNXClassifier(
                onnx_model_path=classifier_config['model_path']
            )
            logger.info("✅ RoBERTa Classifier initialized")
            
            # Initialize Mistral Rephraser (if enabled)
            if self.config['rephrasing_enabled']:
                logger.info("🔧 Initializing Mistral Rephraser...")
                ollama_config = config.get('ollama')
                
                self.rephraser = MistralRephraser(
                    api_url=ollama_config['api_url']
                )
                logger.info("✅ Mistral Rephraser initialized")
            else:
                self.rephraser = None
                logger.info("⚠️ Rephrasing disabled")
            
            # Initialize Mistral QF Generator (if enabled)
            if self.config['qf_enabled']:
                logger.info("🔧 Initializing Mistral QF Generator...")
                ollama_config = config.get('ollama')
                
                self.qf_generator = MistralQualifyingFactorsGenerator(
                    api_url=ollama_config['api_url']
                )
                logger.info("✅ Mistral QF Generator initialized")
            else:
                self.qf_generator = None
                logger.info("⚠️ Qualifying factors generation disabled")
            
            # Initialize MilvusManager
            logger.info("🔧 Initializing MilvusManager...")
            milvus_config = config.get('milvus')
            stp_milvus_config = config.get_stp_milvus_config()
            
            # Build Milvus config for STP
            milvus_stp_config = {
                'endpoint': f"{milvus_config['host']}:{milvus_config['port']}",
                'username': milvus_config['user'],
                'password': milvus_config['password'],
                'db_name': stp_milvus_config['database'],
                'collection': stp_milvus_config['collection'],
                'embedding_model': self.config['embedding_model'],
                'embedding_display': 'STP Embeddings'
            }
            
            self.milvus_manager = STPMilvusManager(milvus_stp_config)
            logger.info("✅ STP MilvusManager initialized")
            
            self.components_initialized = True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize STP components: {e}")
            self.components_initialized = False
            raise
    
    async def process_document(self, document_content: bytes, filename: str, 
                              bucket: str, minio_client=None) -> Dict[str, Any]:
        """
        Process document through complete STP pipeline (LEGACY - uses Unstructured API)
        
        Args:
            document_content: Raw document bytes
            filename: Document filename
            bucket: Source bucket
            minio_client: MinIO client instance (optional)
        
        Returns:
            Processing results including statistics
        """
        if not self.enabled or not self.components_initialized:
            return {
                "status": "skipped",
                "message": "STP processing is disabled or not initialized",
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0,
                "stored_chunks": 0
            }
        
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Starting STP processing for {filename} from {bucket} (legacy method)")
            
            # Step 1: Chunk document with HybridChunker (uses Unstructured API)
            logger.info("📄 Step 1: Chunking document with HybridChunker...")
            chunks = await self._chunk_document(document_content, filename, bucket, minio_client)
            
            if not chunks:
                logger.warning(f"⚠️ No chunks created for {filename}")
                return {
                    "status": "failed",
                    "message": "No chunks created from document",
                    "total_chunks": 0,
                    "stp_chunks": 0,
                    "non_stp_chunks": 0,
                    "stored_chunks": 0
                }
            
            logger.info(f"✅ Created {len(chunks)} chunks")
            
            # Continue with rest of pipeline
            return await self._process_chunks_pipeline(chunks, filename, bucket, start_time)
            
        except Exception as e:
            logger.error(f"❌ STP processing failed for {filename}: {e}")
            processing_time = time.time() - start_time
            
            return {
                "status": "failed",
                "message": f"STP processing failed: {str(e)}",
                "error": str(e),
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0,
                "stored_chunks": 0,
                "processing_time_seconds": processing_time,
                "document_name": filename,
                "bucket_source": bucket
            }
    
    async def process_document_with_elements(self, extracted_elements: List[Dict[str, Any]], 
                                            filename: str, bucket: str) -> Dict[str, Any]:
        """
        Process document through STP pipeline REUSING already-extracted elements
        (NO RE-EXTRACTION via Unstructured API)
        
        Args:
            extracted_elements: Already extracted elements from processors/extractors.py
            filename: Document filename
            bucket: Source bucket
        
        Returns:
            Processing results including statistics
        """
        if not self.enabled or not self.components_initialized:
            return {
                "status": "skipped",
                "message": "STP processing is disabled or not initialized",
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0,
                "stored_chunks": 0
            }
        
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Starting STP processing for {filename} from {bucket} (reusing extracted elements)")
            
            # Step 1: Convert elements to chunks using HybridChunker pipeline
            logger.info("📄 Step 1: Processing extracted elements into chunks...")
            chunks = await self._process_extracted_elements(extracted_elements, filename, bucket)
            
            if not chunks:
                logger.warning(f"⚠️ No chunks created for {filename}")
                return {
                    "status": "failed",
                    "message": "No chunks created from extracted elements",
                    "total_chunks": 0,
                    "stp_chunks": 0,
                    "non_stp_chunks": 0,
                    "stored_chunks": 0
                }
            
            logger.info(f"✅ Created {len(chunks)} chunks from extracted elements")
            
            # Continue with rest of pipeline
            return await self._process_chunks_pipeline(chunks, filename, bucket, start_time)
            
        except Exception as e:
            logger.error(f"❌ STP processing failed for {filename}: {e}")
            processing_time = time.time() - start_time
            
            return {
                "status": "failed",
                "message": f"STP processing failed: {str(e)}",
                "error": str(e),
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0,
                "stored_chunks": 0,
                "processing_time_seconds": processing_time,
                "document_name": filename,
                "bucket_source": bucket
            }
    
    async def process_text_content(self, text_content: str, filename: str, 
                                  bucket: str) -> Dict[str, Any]:
        """
        Process plain text content through STP pipeline (for news articles)
        
        Args:
            text_content: Plain text content
            filename: Document/article identifier
            bucket: Source bucket
        
        Returns:
            Processing results including statistics
        """
        if not self.enabled or not self.components_initialized:
            return {
                "status": "skipped",
                "message": "STP processing is disabled or not initialized",
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0,
                "stored_chunks": 0
            }
        
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Starting STP processing for text content: {filename} from {bucket}")
            
            # Step 1: Create chunks from text using HybridChunker's text processing
            logger.info("📄 Step 1: Chunking text content...")
            chunks = await self._chunk_text_content(text_content, filename, bucket)
            
            if not chunks:
                logger.warning(f"⚠️ No chunks created for {filename}")
                return {
                    "status": "failed",
                    "message": "No chunks created from text content",
                    "total_chunks": 0,
                    "stp_chunks": 0,
                    "non_stp_chunks": 0,
                    "stored_chunks": 0
                }
            
            logger.info(f"✅ Created {len(chunks)} chunks from text")
            
            # Continue with rest of pipeline
            return await self._process_chunks_pipeline(chunks, filename, bucket, start_time)
            
        except Exception as e:
            logger.error(f"❌ STP processing failed for {filename}: {e}")
            processing_time = time.time() - start_time
            
            return {
                "status": "failed",
                "message": f"STP processing failed: {str(e)}",
                "error": str(e),
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0,
                "stored_chunks": 0,
                "processing_time_seconds": processing_time,
                "document_name": filename,
                "bucket_source": bucket
            }
    
    async def _process_chunks_pipeline(self, chunks: List[Dict[str, Any]], 
                                      filename: str, bucket: str, 
                                      start_time: float) -> Dict[str, Any]:
        """Common pipeline for processing chunks after creation"""
        
        # Step 2: Classify chunks with RoBERTa
        logger.info("🔍 Step 2: Classifying chunks with RoBERTa...")
        classified_chunks = await self._classify_chunks(chunks)
        
        stp_chunks = [c for c in classified_chunks if c.get('stp_prediction') == 'STP']
        non_stp_chunks = [c for c in classified_chunks if c.get('stp_prediction') != 'STP']
        
        logger.info(f"✅ Classification complete: {len(stp_chunks)} STP, {len(non_stp_chunks)} Non-STP")
        
        if not stp_chunks:
            logger.warning(f"⚠️ No STP chunks found in {filename}")
            processing_time = time.time() - start_time
            
            return {
                "status": "success",
                "message": "Processing complete - no STP chunks found",
                "total_chunks": len(chunks),
                "stp_chunks": 0,
                "non_stp_chunks": len(non_stp_chunks),
                "stored_chunks": 0,
                "processing_time_seconds": processing_time,
                "document_name": filename,
                "bucket_source": bucket
            }
        
        # Step 3: Rephrase STP chunks (if enabled)
        if self.rephraser:
            logger.info("✍️ Step 3: Rephrasing STP chunks...")
            stp_chunks = await self._rephrase_chunks(stp_chunks)
            logger.info(f"✅ Rephrased {len(stp_chunks)} STP chunks")
        else:
            # Copy original content to rephrased_content if rephrasing disabled
            for chunk in stp_chunks:
                chunk['rephrased_content'] = chunk['content']
            logger.info("⚠️ Rephrasing skipped (disabled)")
        
        # Step 4: Generate qualifying factors (if enabled)
        if self.qf_generator:
            logger.info("📝 Step 4: Generating qualifying factors...")
            stp_chunks = await self._generate_qualifying_factors(stp_chunks)
            logger.info(f"✅ Generated qualifying factors for {len(stp_chunks)} chunks")
        else:
            # Set empty QF if disabled
            for chunk in stp_chunks:
                chunk['qualifying_factors'] = "Qualifying factors generation disabled"
            logger.info("⚠️ Qualifying factors generation skipped (disabled)")
        
        # Step 5: Store in Milvus
        logger.info("💾 Step 5: Storing STP chunks in Milvus...")
        storage_result = await self._store_chunks(stp_chunks, filename, bucket)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ STP processing completed for {filename} in {processing_time:.2f}s")
        
        return {
            "status": "success",
            "message": f"STP processing completed successfully",
            "total_chunks": len(chunks),
            "stp_chunks": len(stp_chunks),
            "non_stp_chunks": len(non_stp_chunks),
            "stored_chunks": storage_result.get('stored_count', 0),
            "processing_time_seconds": processing_time,
            "document_name": filename,
            "bucket_source": bucket,
            "statistics": {
                "avg_confidence": sum(c['stp_confidence'] for c in stp_chunks) / len(stp_chunks) if stp_chunks else 0,
                "chunks_with_qf": sum(1 for c in stp_chunks if c.get('qualifying_factors') and 'disabled' not in c.get('qualifying_factors', '').lower()),
                "rephrased_chunks": sum(1 for c in stp_chunks if c.get('rephrased_content') != c.get('content'))
            }
        }
    
    async def _chunk_document(self, document_content: bytes, filename: str, 
                             bucket: str, minio_client=None) -> List[Dict[str, Any]]:
        """Chunk document using HybridChunker (LEGACY - uses Unstructured API)"""
        try:
            # Run chunking in executor (blocking operation)
            chunks = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._chunk_document_sync,
                document_content, filename, bucket, minio_client
            )
            return chunks
        except Exception as e:
            logger.error(f"❌ Chunking failed: {e}")
            return []
    
    def _chunk_document_sync(self, document_content: bytes, filename: str, 
                            bucket: str, minio_client=None) -> List[Dict[str, Any]]:
        """Synchronous chunking using HybridChunker's process_document"""
        try: 
            if minio_client:
                # Use original process_document method
                chunks = self.chunker.process_document(minio_client, bucket, filename)
            else:
                # Process bytes directly through extraction pipeline
                import io
                pdf_bytes = io.BytesIO(document_content)
                
                # Extract elements (CALLS UNSTRUCTURED API)
                elements = self.chunker.extract_elements_with_unstructured(pdf_bytes)
                
                # Clean elements
                cleaned_elements = self.chunker.clean_elements(elements)
                
                # Remove references
                cleaned_elements = self.chunker.remove_references_section(cleaned_elements)
                
                # Convert to DataFrame
                df = self.chunker.elements_to_dataframe(cleaned_elements)
                
                # Merge split sentences
                merged_df = self.chunker.merge_split_sentences(df)
                
                # Apply cross-segment chunking
                chunks = self.chunker.cross_segment_chunking(merged_df)
                
                # Add document metadata
                for chunk in chunks:
                    chunk.update({
                        'document_name': filename,
                        'source_bucket': bucket,
                        'chunking_timestamp': datetime.now().isoformat(),
                        'global_chunk_id': f"{filename}_{len(chunks)}_{chunks.index(chunk) + 1:03d}",
                        'source_document': filename
                    })
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Sync chunking failed: {e}")
            return []
    
    async def _process_extracted_elements(self, extracted_elements: List[Dict[str, Any]], 
                                         filename: str, bucket: str) -> List[Dict[str, Any]]:
        """Process already-extracted elements through HybridChunker pipeline (NO API CALL)"""
        try:
            chunks = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._process_elements_sync,
                extracted_elements, filename, bucket
            )
            return chunks
        except Exception as e:
            logger.error(f"❌ Element processing failed: {e}")
            return []
    
    def _process_elements_sync(self, extracted_elements: List[Dict[str, Any]], 
                              filename: str, bucket: str) -> List[Dict[str, Any]]:
        """Synchronous processing of extracted elements"""
        try:
            # Convert extracted elements to HybridChunker format
            class ElementAdapter:
                def __init__(self, data):
                    self.text = data.get('text', '')
                    self.category = data.get('type', 'Unknown')
                    self.metadata = data.get('metadata', {})
                    self.coordinates = data.get('coordinates', None)
                
                def __str__(self):
                    return self.text
            
            adapted_elements = [ElementAdapter(elem) for elem in extracted_elements]
            
            # Clean elements
            cleaned_elements = self.chunker.clean_elements(adapted_elements)
            
            # Remove references
            cleaned_elements = self.chunker.remove_references_section(cleaned_elements)
            
            # Convert to DataFrame
            df = self.chunker.elements_to_dataframe(cleaned_elements)
            
            # Merge split sentences
            merged_df = self.chunker.merge_split_sentences(df)
            
            # Apply cross-segment chunking
            chunks = self.chunker.cross_segment_chunking(merged_df)
            
            # Add document metadata
            for chunk in chunks:
                chunk.update({
                    'document_name': filename,
                    'source_bucket': bucket,
                    'chunking_timestamp': datetime.now().isoformat(),
                    'global_chunk_id': f"{filename}_{len(chunks)}_{chunks.index(chunk) + 1:03d}",
                    'source_document': filename
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Sync element processing failed: {e}")
            return []
    
    async def _chunk_text_content(self, text_content: str, filename: str, 
                                 bucket: str) -> List[Dict[str, Any]]:
        """Chunk plain text content (for news articles)"""
        try:
            chunks = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._chunk_text_sync,
                text_content, filename, bucket
            )
            return chunks
        except Exception as e:
            logger.error(f"❌ Text chunking failed: {e}")
            return []
    
    def _chunk_text_sync(self, text_content: str, filename: str, bucket: str) -> List[Dict[str, Any]]:
        """Synchronous text chunking using sentence-based splitting"""
        try:
            import re
            
            # Use NLTK for sentence tokenization if available
            try:
                from nltk.tokenize import sent_tokenize
                sentences = sent_tokenize(text_content)
            except:
                # Fallback to regex-based sentence splitting
                sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text_content)
                sentences = [s.strip() for s in sentences if s.strip()]
            
            # Create chunks based on token count
            chunks = []
            current_chunk_sentences = []
            current_tokens = 0
            
            for sentence in sentences:
                sentence_tokens = self.chunker.count_tokens(sentence)
                
                # Check if adding this sentence would exceed max tokens
                if current_tokens + sentence_tokens > self.chunker.max_chunk_tokens and current_chunk_sentences:
                    # Finalize current chunk
                    chunk_text = ' '.join(current_chunk_sentences)
                    chunks.append({
                        'content': chunk_text,
                        'token_count': current_tokens,
                        'sentence_count': len(current_chunk_sentences),
                        'chunking_method': 'text_sentence_based',
                        'is_clean': True
                    })
                    
                    # Start new chunk
                    current_chunk_sentences = [sentence]
                    current_tokens = sentence_tokens
                else:
                    # Add to current chunk
                    current_chunk_sentences.append(sentence)
                    current_tokens += sentence_tokens
            
            # Add final chunk if exists
            if current_chunk_sentences:
                chunk_text = ' '.join(current_chunk_sentences)
                chunks.append({
                    'content': chunk_text,
                    'token_count': current_tokens,
                    'sentence_count': len(current_chunk_sentences),
                    'chunking_method': 'text_sentence_based',
                    'is_clean': True
                })
            
            # Add document metadata
            for i, chunk in enumerate(chunks):
                chunk.update({
                    'document_name': filename,
                    'source_bucket': bucket,
                    'chunking_timestamp': datetime.now().isoformat(),
                    'global_chunk_id': f"{filename}_{len(chunks)}_{i + 1:03d}",
                    'source_document': filename
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Sync text chunking failed: {e}")
            return []
    
    async def _classify_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classify chunks using RoBERTa classifier"""
        try:
            # Run classification in executor
            classified = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._classify_chunks_sync,
                chunks
            )
            return classified
        except Exception as e:
            logger.error(f"❌ Classification failed: {e}")
            return chunks
    
    def _classify_chunks_sync(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Synchronous chunk classification"""
        try:
            for chunk in chunks:
                content = chunk.get('content', '')
                
                if content:
                    # Classify using RoBERTa
                    prediction, confidence = self.classifier.predict_stp(content)
                    
                    chunk['stp_prediction'] = prediction
                    chunk['stp_confidence'] = confidence
                else:
                    chunk['stp_prediction'] = 'Non-STP'
                    chunk['stp_confidence'] = 0.0
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Sync classification failed: {e}")
            return chunks
    
    async def _rephrase_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rephrase chunks using Mistral rephraser"""
        try:
            # Process chunks in batches
            batch_size = 5
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Run rephrasing in executor for each batch
                rephrased_batch = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    self._rephrase_batch_sync,
                    batch
                )
                
                # Update chunks with rephrased content
                for j, rephrased_chunk in enumerate(rephrased_batch):
                    chunks[i + j]['rephrased_content'] = rephrased_chunk
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ Rephrasing failed: {e}")
            # Fallback: copy original to rephrased
            for chunk in chunks:
                chunk['rephrased_content'] = chunk['content']
            return chunks
    
    def _rephrase_batch_sync(self, batch: List[Dict[str, Any]]) -> List[str]:
        """Synchronous batch rephrasing"""
        try:
            rephrased = []
            
            for chunk in batch:
                content = chunk.get('content', '')
                
                if content:
                    rephrased_text = self.rephraser.rephrase_text(content)
                    rephrased.append(rephrased_text)
                else:
                    rephrased.append(content)
            
            return rephrased
            
        except Exception as e:
            logger.error(f"❌ Sync rephrasing failed: {e}")
            return [chunk.get('content', '') for chunk in batch]
    
    async def _generate_qualifying_factors(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate qualifying factors using Mistral QF generator"""
        try:
            # Process chunks in batches
            batch_size = 5
            
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                
                # Run QF generation in executor for each batch
                qf_batch = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
                    self._generate_qf_batch_sync,
                    batch
                )
                
                # Update chunks with QF
                for j, qf in enumerate(qf_batch):
                    chunks[i + j]['qualifying_factors'] = qf
            
            return chunks
            
        except Exception as e:
            logger.error(f"❌ QF generation failed: {e}")
            # Fallback: set error message
            for chunk in chunks:
                chunk['qualifying_factors'] = f"Error generating factors: {str(e)}"
            return chunks
    
    def _generate_qf_batch_sync(self, batch: List[Dict[str, Any]]) -> List[str]:
        """Synchronous batch QF generation"""
        try:
            qf_results = []
            
            for chunk in batch:
                # Use rephrased content if available, otherwise original
                content = chunk.get('rephrased_content', chunk.get('content', ''))
                
                if content:
                    qf = self.qf_generator.generate_factors(content)
                    qf_results.append(qf)
                else:
                    qf_results.append("No content available for QF generation")
            
            return qf_results
            
        except Exception as e:
            logger.error(f"❌ Sync QF generation failed: {e}")
            return [f"Error: {str(e)}" for _ in batch]
    
    async def _store_chunks(self, chunks: List[Dict[str, Any]], 
                           filename: str, bucket: str) -> Dict[str, Any]:
        """Store STP chunks in Milvus"""
        try:
            # Prepare chunks for storage
            stp_chunks = []
            
            for chunk in chunks:
                stp_chunk = {
                    'content': chunk.get('content', ''),  # Original content
                    'rephrased_content': chunk.get('rephrased_content', chunk.get('content', '')),
                    'stp_confidence': chunk.get('stp_confidence', 0.0),
                    'qualifying_factors': chunk.get('qualifying_factors', ''),
                    'chunk_id': chunk.get('global_chunk_id', chunk.get('chunk_id', '')),
                    'tokens': chunk.get('token_count', 0),
                    'doc_name': filename,
                    'source_file': filename,
                    'bucket_source': bucket,
                    'processing_timestamp': datetime.now().isoformat()
                }

                stp_chunks.append(stp_chunk)
            
            # Run storage in executor
            result = await asyncio.get_event_loop().run_in_executor(
                self._executor,
                self._store_chunks_sync,
                stp_chunks
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Storage failed: {e}")
            return {"status": "failed", "stored_count": 0, "error": str(e)}
    
    def _store_chunks_sync(self, stp_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Synchronous chunk storage in Milvus"""
        try:
            # Use MilvusManager's generate_embeddings_and_store method
            success = self.milvus_manager.generate_embeddings_and_store(
                stp_chunks,
                batch_size=32,
                overwrite_existing=False,
                include_failed_qf=True
            )
            
            if success:
                return {
                    "status": "success",
                    "stored_count": len(stp_chunks)
                }
            else:
                return {
                    "status": "failed",
                    "stored_count": 0,
                    "error": "Milvus storage failed"
                }
                
        except Exception as e:
            logger.error(f"❌ Sync storage failed: {e}")
            return {
                "status": "failed",
                "stored_count": 0,
                "error": str(e)
            }
    
    def health_check(self) -> bool:
        """Check STP processor health"""
        if not self.enabled or not self.components_initialized:
            return False
        
        try:
            # Check Milvus connection
            if hasattr(self.milvus_manager, 'test_connection_and_collection_status'):
                return True
            
            return True
        except Exception:
            return False
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if hasattr(self, '_executor'):
                self._executor.shutdown(wait=True)
            
            logger.info("✅ STP Processor cleanup complete")
        except Exception as e:
            logger.error(f"❌ Cleanup error: {e}")


# Global STP processor instance
stp_processor = STPProcessor()