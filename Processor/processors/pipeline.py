import logging
import uuid
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from config import config
from models import ChunkData, SummaryData, DocumentMetadata
from storage.database import tracker
from storage.milvus import milvus_storage as vector_storage
from processors.extractors import DocumentExtractor
from processors.chunkers import ChunkerFactory
from processors.summarizers import SummarizerFactory
from processors.graphrag_processor import graphrag_processor
from processors.stp_processor import stp_processor

logger = logging.getLogger(__name__)


class AsyncDocumentProcessor:
    """Unified document processing pipeline with GraphRAG, STP integration and auto LanceDB transfer"""
    
    def __init__(self):
        self.extractor = DocumentExtractor()
        self.embedder = AsyncEmbeddingProcessor()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="processor_worker")
        
    async def process_document(self, document_content: bytes, filename: str, bucket: str,
                             include_chunking: bool = True, include_summarization: bool = True,
                             include_graphrag: bool = False, include_stp: bool = False) -> Dict[str, Any]:
        """Main processing pipeline with GraphRAG, STP integration and automatic LanceDB transfer"""
        
        results = {}
        tracking_updates = []
        
        try:
            # Special handling for news Excel files
            if bucket == "news" and filename.lower().endswith(('.xlsx', '.xls')):
                logger.info(f"🗞️ Processing news Excel file: {filename}")
                return await self._process_news_excel(
                    document_content, filename, bucket,
                    include_chunking, include_summarization, include_graphrag, include_stp
                )

            # Special handling for scientific data: only chunks and summaries
            if bucket == "scientificdata":
                if include_stp or include_graphrag:
                    logger.info(f"🔬 Scientific data detected: disabling STP and GraphRAG processing")
                    include_stp = False
                    include_graphrag = False

            # SINGLE EXTRACTION POINT - Extract content once and share with all processors
            logger.info(f"📄 Extracting content from {filename}")
            extracted_elements = await self._run_in_executor(
                self.extractor.extract_content, document_content, filename, "auto"
            )
            
            # Convert elements to structured content format (for summary/graphrag)
            extracted_content = self._elements_to_structured_content(extracted_elements, filename)
            
            # Step 1: Process chunks (if enabled) - uses extracted_elements
            if include_chunking:
                logger.info(f"🔗 Processing chunks for {filename}")
                chunks_result = await self._process_chunks_async(extracted_elements, filename, bucket)
                results["chunks"] = chunks_result
                if chunks_result.get("status") == "success":
                    tracking_updates.append("chunks")
            
            # Step 2: Process summary (if enabled) - uses extracted_content
            if include_summarization:
                logger.info(f"📝 Processing summary for {filename}")
                summary_result = await self._process_summary_async(extracted_content, filename, bucket)
                results["summary"] = summary_result
                if summary_result.get("status") == "success":
                    tracking_updates.append("summary")
            
            # Step 3: Process GraphRAG with automatic LanceDB transfer - uses extracted_content
            if include_graphrag:
                logger.info(f"🕸️ Processing GraphRAG for {filename}")
                full_text = extracted_content.get("full_text", "")
                
                if len(full_text.strip()) > 100:
                    graphrag_result = await graphrag_processor.process_document_graphrag(
                        full_text, filename, bucket
                    )
                    results["graphrag"] = graphrag_result
                    
                    if graphrag_result.get("status") == "success":
                        tracker.mark_done("graphrag", filename, bucket,
                            entities=graphrag_result.get("entities_count", 0),
                            relationships=graphrag_result.get("relationships_count", 0),
                            communities=graphrag_result.get("communities_count", 0))
                        tracking_updates.append("graphrag")
                        
                        lancedb_status = graphrag_result.get("lancedb_transfer", "unknown")
                        logger.info(f"📊 LanceDB transfer status: {lancedb_status}")
                        
                    elif graphrag_result.get("status") == "partial_success":
                        logger.warning(f"⚠️ GraphRAG completed but LanceDB transfer failed for {filename}")
                        tracker.mark_done("graphrag", filename, bucket,
                            entities=graphrag_result.get("entities_count", 0),
                            relationships=graphrag_result.get("relationships_count", 0),
                            communities=graphrag_result.get("communities_count", 0))
                        tracking_updates.append("graphrag")
                else:
                    results["graphrag"] = {
                        "status": "skipped", 
                        "message": "Document too short for GraphRAG processing",
                        "lancedb_transfer": "not_attempted"
                    }
            
            # Step 4: Process STP (if enabled)
            if include_stp:
                logger.info(f"🎯 Processing STP for {filename}")
                
                # Pass extracted_elements to STP processor to avoid re-extraction
                stp_result = await stp_processor.process_document_with_elements(
                    extracted_elements, filename, bucket
                )
                results["stp"] = stp_result
                
                if stp_result.get("status") == "success":
                    tracker.mark_done("stp", filename, bucket,
                        total_chunks=stp_result.get("total_chunks", 0),
                        stp_count=stp_result.get("stp_chunks", 0),
                        non_stp_count=stp_result.get("non_stp_chunks", 0))
                    tracking_updates.append("stp")
                    logger.info(f"✅ STP processing completed: {stp_result.get('stp_chunks', 0)} STP chunks found")
            
            # Determine overall status
            enabled_processes = []
            successful_processes = []
            
            for process_name in ["chunks", "summary", "graphrag", "stp"]:
                process_enabled = locals().get(f"include_{process_name.replace('chunks', 'chunking')}", False)
                if process_enabled:
                    enabled_processes.append(process_name)
                    if results.get(process_name, {}).get("status") == "success":
                        successful_processes.append(process_name)
            
            overall_status = "success" if len(successful_processes) == len(enabled_processes) else "partial_success"
            
            logger.info(f"✅ Processing completed for {filename}: {len(successful_processes)}/{len(enabled_processes)} successful")
            
            return {
                "overall_status": overall_status,
                "message": f"Processing completed: {len(successful_processes)}/{len(enabled_processes)} processes successful",
                "results": results,
                "tracking_updates": tracking_updates,
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"💥 Processing failed for {filename}: {e}")
            return {
                "overall_status": "failed",
                "message": f"Processing failed: {str(e)}",
                "error": str(e),
                "processing_timestamp": datetime.now().isoformat()
            }
    
    async def _run_in_executor(self, func, *args, **kwargs):
        """Run blocking function in executor"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self._executor, func, *args, **kwargs)
    
    async def _process_chunks_async(self, extracted_elements: List[Dict[str, Any]], 
                                   filename: str, bucket: str) -> Dict[str, Any]:
        """Process chunks asynchronously"""
        try:
            chunks = await self._run_in_executor(self._process_chunks_sync, extracted_elements, filename, bucket)
            
            if chunks:
                enriched_chunks = await self.embedder.process_chunks(chunks)
                await vector_storage.insert_chunks(enriched_chunks)
                tracker.mark_done("chunks", filename, bucket, count=len(chunks))

                return {
                    "status": "success",
                    "count": len(chunks),
                    "message": f"Created {len(chunks)} chunks"
                }
            else:
                return {"status": "failed", "message": "No chunks created"}
                
        except Exception as e:
            logger.error(f"❌ Chunks processing failed for {filename}: {e}")
            return {"status": "failed", "message": f"Chunks processing failed: {str(e)}"}
    
    async def _process_summary_async(self, extracted_content: Dict[str, Any], 
                                    filename: str, bucket: str) -> Dict[str, Any]:
        """Process summary asynchronously"""
        try:
            summary_data = await self._run_in_executor(self._process_summary_sync, extracted_content, filename, bucket)
            
            if summary_data:
                enriched_summary = await self.embedder.process_summary(summary_data)
                await vector_storage.insert_summary(enriched_summary)
                tracker.mark_done("summary", filename, bucket)

                return {
                    "status": "success",
                    "message": "Summary created successfully"
                }
            else:
                return {"status": "failed", "message": "Summary creation failed"}
                
        except Exception as e:
            logger.error(f"❌ Summary processing failed for {filename}: {e}")
            return {"status": "failed", "message": f"Summary processing failed: {str(e)}"}
    
    async def _process_news_excel(self, document_content: bytes, filename: str, bucket: str,
                                include_chunking: bool = True, include_summarization: bool = True,
                                include_graphrag: bool = False, include_stp: bool = False) -> Dict[str, Any]:
        """Process news Excel files with row-by-row processing including STP"""
        
        results = {}
        tracking_updates = []
        
        try:
            logger.info(f"📊 Extracting articles from news Excel: {filename}")
            
            articles = await self._run_in_executor(self._extract_articles_from_excel, document_content, filename, bucket)
            
            if not articles:
                return {
                    "overall_status": "failed",
                    "message": "No articles found in Excel file",
                    "results": {},
                    "processing_timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"📰 Found {len(articles)} articles in {filename}")
            
            # Process chunks for each article (if enabled)
            all_chunks = []
            if include_chunking:
                logger.info(f"🔗 Creating chunks for {len(articles)} articles")
                
                batch_size = 10
                for i in range(0, len(articles), batch_size):
                    batch = articles[i:i + batch_size]
                    batch_tasks = []
                    
                    for article in batch:
                        task = self._create_article_chunks_async(article, bucket)
                        batch_tasks.append(task)
                    
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for j, chunks in enumerate(batch_results):
                        if isinstance(chunks, Exception):
                            logger.error(f"  Article {i+j+1}: chunking failed: {chunks}")
                            continue
                        all_chunks.extend(chunks)
                        logger.info(f"  Article {i+j+1}: {len(chunks)} chunks created")
                
                if all_chunks:
                    logger.info(f"🧮 Generating embeddings for {len(all_chunks)} chunks")
                    enriched_chunks = await self.embedder.process_chunks(all_chunks)
                    await vector_storage.insert_chunks(enriched_chunks)

                    tracker.mark_done("chunks", filename, bucket, count=len(all_chunks))
                    tracking_updates.append("chunks")
                    
                    results["chunks"] = {
                        "status": "success",
                        "count": len(all_chunks),
                        "articles_processed": len(articles),
                        "message": f"Created {len(all_chunks)} chunks from {len(articles)} articles"
                    }
                    logger.info(f"✅ Chunks completed: {len(all_chunks)} total chunks")
                else:
                    results["chunks"] = {"status": "failed", "message": "No chunks created from articles"}
            
            # Process summaries for each article (if enabled)
            all_summaries = []
            if include_summarization:
                logger.info(f"📝 Creating summaries for {len(articles)} articles")
                
                batch_size = 5
                for i in range(0, len(articles), batch_size):
                    batch = articles[i:i + batch_size]
                    batch_tasks = []
                    
                    for article in batch:
                        task = self._create_article_summary_async(article, bucket)
                        batch_tasks.append(task)
                    
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for j, summary_data in enumerate(batch_results):
                        if isinstance(summary_data, Exception):
                            logger.error(f"  Article {i+j+1}: summarization failed: {summary_data}")
                            continue
                        if summary_data:
                            all_summaries.append(summary_data)
                            logger.info(f"  Article {i+j+1}: Summary created")
                        else:
                            logger.warning(f"  Article {i+j+1}: Summary creation failed")
                
                if all_summaries:
                    logger.info(f"🧮 Generating embeddings for {len(all_summaries)} summaries")
                    
                    summary_tasks = []
                    for summary_data in all_summaries:
                        task = self._process_single_summary_async(summary_data)
                        summary_tasks.append(task)
                    
                    await asyncio.gather(*summary_tasks, return_exceptions=True)

                    tracker.mark_done("summary", filename, bucket)
                    tracking_updates.append("summary")
                    
                    results["summary"] = {
                        "status": "success",
                        "count": len(all_summaries),
                        "articles_processed": len(articles),
                        "message": f"Created {len(all_summaries)} summaries from {len(articles)} articles"
                    }
                    logger.info(f"✅ Summaries completed: {len(all_summaries)} total summaries")
                else:
                    results["summary"] = {"status": "failed", "message": "No summaries created from articles"}
            
            # GraphRAG processing with automatic LanceDB transfer
            if include_graphrag:
                logger.info(f"🕸️ Processing GraphRAG for {len(articles)} individual articles with auto LanceDB transfer")
                
                graphrag_results = []
                successful_graphrag = 0
                failed_graphrag = 0
                lancedb_transfers_completed = 0
                
                batch_size = 3
                for i in range(0, len(articles), batch_size):
                    batch = articles[i:i + batch_size]
                    batch_tasks = []
                    
                    for article in batch:
                        task = self._process_article_graphrag_async(article, bucket)
                        batch_tasks.append(task)
                    
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for j, graphrag_result in enumerate(batch_results):
                        article_num = i + j + 1
                        if isinstance(graphrag_result, Exception):
                            logger.error(f"  Article {article_num}: GraphRAG failed: {graphrag_result}")
                            failed_graphrag += 1
                            continue
                        
                        if graphrag_result and graphrag_result.get("status") == "success":
                            graphrag_results.append(graphrag_result)
                            successful_graphrag += 1
                            
                            lancedb_status = graphrag_result.get("lancedb_transfer", "unknown")
                            if lancedb_status == "completed":
                                lancedb_transfers_completed += 1
                            
                            logger.info(f"  Article {article_num}: GraphRAG completed - {graphrag_result.get('entities_count', 0)}E, {graphrag_result.get('relationships_count', 0)}R, LanceDB: {lancedb_status}")
                        elif graphrag_result and graphrag_result.get("status") == "partial_success":
                            graphrag_results.append(graphrag_result)
                            successful_graphrag += 1
                            logger.warning(f"  Article {article_num}: GraphRAG completed but LanceDB transfer failed")
                        else:
                            failed_graphrag += 1
                            logger.warning(f"  Article {article_num}: GraphRAG failed")
                
                if successful_graphrag > 0:
                    total_entities = sum(result.get("entities_count", 0) for result in graphrag_results)
                    total_relationships = sum(result.get("relationships_count", 0) for result in graphrag_results)
                    total_communities = sum(result.get("communities_count", 0) for result in graphrag_results)

                    tracker.mark_done("graphrag", filename, bucket,
                                           entities=total_entities,
                                           relationships=total_relationships,
                                           communities=total_communities)
                    tracking_updates.append("graphrag")
                    
                    results["graphrag"] = {
                        "status": "success",
                        "articles_processed": successful_graphrag,
                        "articles_failed": failed_graphrag,
                        "total_entities": total_entities,
                        "total_relationships": total_relationships,
                        "total_communities": total_communities,
                        "lancedb_transfers_completed": lancedb_transfers_completed,
                        "lancedb_transfers_failed": successful_graphrag - lancedb_transfers_completed,
                        "message": f"Processed {successful_graphrag}/{len(articles)} articles for GraphRAG with {lancedb_transfers_completed} successful LanceDB transfers"
                    }
                    logger.info(f"✅ GraphRAG completed: {successful_graphrag}/{len(articles)} articles, {total_entities}E total, {lancedb_transfers_completed} LanceDB transfers")
                else:
                    results["graphrag"] = {
                        "status": "failed", 
                        "message": f"GraphRAG failed for all {len(articles)} articles",
                        "lancedb_transfers_completed": 0
                    }
            
            # STP processing for news articles
            if include_stp:
                logger.info(f"🎯 Processing STP for {len(articles)} individual articles")
                
                stp_results = []
                successful_stp = 0
                failed_stp = 0
                total_stp_chunks = 0
                total_non_stp_chunks = 0
                
                batch_size = 5
                for i in range(0, len(articles), batch_size):
                    batch = articles[i:i + batch_size]
                    batch_tasks = []
                    
                    for article in batch:
                        # Pass article content directly to STP processor
                        task = self._process_article_stp_async(article, bucket)
                        batch_tasks.append(task)
                    
                    batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
                    
                    for j, stp_result in enumerate(batch_results):
                        article_num = i + j + 1
                        if isinstance(stp_result, Exception):
                            logger.error(f"  Article {article_num}: STP failed: {stp_result}")
                            failed_stp += 1
                            continue
                        
                        if stp_result and stp_result.get("status") == "success":
                            stp_results.append(stp_result)
                            successful_stp += 1
                            total_stp_chunks += stp_result.get("stp_chunks", 0)
                            total_non_stp_chunks += stp_result.get("non_stp_chunks", 0)
                            logger.info(f"  Article {article_num}: STP completed - {stp_result.get('stp_chunks', 0)} STP chunks")
                        else:
                            failed_stp += 1
                            logger.warning(f"  Article {article_num}: STP failed")
                
                if successful_stp > 0:
                    tracker.mark_done("stp", filename, bucket,
                                           total_chunks=total_stp_chunks + total_non_stp_chunks,
                                           stp_count=total_stp_chunks,
                                           non_stp_count=total_non_stp_chunks)
                    tracking_updates.append("stp")
                    
                    results["stp"] = {
                        "status": "success",
                        "articles_processed": successful_stp,
                        "articles_failed": failed_stp,
                        "total_stp_chunks": total_stp_chunks,
                        "total_non_stp_chunks": total_non_stp_chunks,
                        "message": f"Processed {successful_stp}/{len(articles)} articles for STP with {total_stp_chunks} STP chunks found"
                    }
                    logger.info(f"✅ STP completed: {successful_stp}/{len(articles)} articles, {total_stp_chunks} STP chunks")
                else:
                    results["stp"] = {
                        "status": "failed",
                        "message": f"STP failed for all {len(articles)} articles"
                    }
            
            # Determine overall status
            enabled_processes = []
            successful_processes = []
            
            for process_name in ["chunks", "summary", "graphrag", "stp"]:
                process_enabled = locals().get(f"include_{process_name.replace('chunks', 'chunking')}", False)
                if process_enabled:
                    enabled_processes.append(process_name)
                    if results.get(process_name, {}).get("status") == "success":
                        successful_processes.append(process_name)
            
            overall_status = "success" if len(successful_processes) == len(enabled_processes) else "partial_success"
            
            return {
                "overall_status": overall_status,
                "message": f"News Excel processing completed: {len(successful_processes)}/{len(enabled_processes)} processes successful",
                "results": results,
                "tracking_updates": tracking_updates,
                "articles_found": len(articles),
                "processing_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"💥 News Excel processing failed for {filename}: {e}")
            return {
                "overall_status": "failed",
                "message": f"News Excel processing failed: {str(e)}",
                "error": str(e),
                "processing_timestamp": datetime.now().isoformat()
            }
    
    async def _create_article_chunks_async(self, article: Dict[str, Any], bucket: str) -> List[ChunkData]:
        """Create chunks for a single news article - async"""
        return await self._run_in_executor(self._create_article_chunks, article, bucket)
    
    async def _create_article_summary_async(self, article: Dict[str, Any], bucket: str) -> Optional[SummaryData]:
        """Create summary for a single news article - async"""
        return await self._run_in_executor(self._create_article_summary, article, bucket)
    
    async def _process_article_graphrag_async(self, article: Dict[str, Any], bucket: str) -> Dict[str, Any]:
        """Process GraphRAG for a single news article with automatic LanceDB transfer - async"""
        try:
            article_content = article["content"]
            article_url = article["source_url"]
            
            if len(article_content.strip()) > 100:
                graphrag_result = await graphrag_processor.process_document_graphrag(
                    article_content, article_url, bucket
                )
                return graphrag_result
            else:
                return {
                    "status": "skipped",
                    "message": "Article content too short for GraphRAG processing",
                    "lancedb_transfer": "not_attempted"
                }
                
        except Exception as e:
            logger.error(f"Failed to process GraphRAG for article {article.get('source_url', 'unknown')}: {e}")
            return {
                "status": "failed",
                "message": f"GraphRAG processing failed: {str(e)}",
                "lancedb_transfer": "failed"
            }
    
    async def _process_article_stp_async(self, article: Dict[str, Any], bucket: str) -> Dict[str, Any]:
        """Process STP for a single news article - async (NO RE-EXTRACTION)"""
        try:
            article_content = article["content"]
            article_url = article["source_url"]
            
            if len(article_content.strip()) > 100:
                stp_result = await stp_processor.process_text_content(
                    article_content, article_url, bucket
                )
                return stp_result
            else:
                return {
                    "status": "skipped",
                    "message": "Article content too short for STP processing",
                    "total_chunks": 0,
                    "stp_chunks": 0,
                    "non_stp_chunks": 0
                }
                
        except Exception as e:
            logger.error(f"Failed to process STP for article {article.get('source_url', 'unknown')}: {e}")
            return {
                "status": "failed",
                "message": f"STP processing failed: {str(e)}",
                "total_chunks": 0,
                "stp_chunks": 0,
                "non_stp_chunks": 0
            }
    
    async def _process_single_summary_async(self, summary_data: SummaryData) -> None:
        """Process single summary with embedding and storage - async"""
        try:
            enriched_summary = await self.embedder.process_summary(summary_data)
            await vector_storage.insert_summary(enriched_summary)
        except Exception as e:
            logger.error(f"Failed to process summary embedding: {e}")
    
    # Synchronous methods that run in executor
    def _process_chunks_sync(self, elements: List[Dict[str, Any]], filename: str, bucket: str) -> List[ChunkData]:
        """Process chunks using specialized chunkers - sync"""
        try:
            chunker = ChunkerFactory.get_chunker(bucket)
            chunks = chunker.create_chunks(elements, filename, bucket)
            logger.info(f"Created {len(chunks)} chunks using {chunker.__class__.__name__}")
            return chunks
            
        except Exception as e:
            logger.error(f"Chunking failed for {filename}: {e}")
            return []
    
    def _process_summary_sync(self, extracted_content: Dict[str, Any], filename: str, bucket: str) -> Optional[SummaryData]:
        """Process summary using specialized summarizers - sync"""
        try:
            summarizer = SummarizerFactory.get_summarizer(bucket)
            summary_data = summarizer.create_summary(extracted_content, filename, bucket)
            
            if summary_data:
                logger.info(f"Created summary using {summarizer.__class__.__name__}")
            else:
                logger.warning(f"No summary created for {filename}")
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Summarization failed for {filename}: {e}")
            return None
    
    def _extract_articles_from_excel(self, document_content: bytes, filename: str, bucket: str) -> List[Dict[str, Any]]:
        """Extract articles from Excel file starting from row 3 (header in row 2) - sync"""
        try:
            import pandas as pd
            import io
        except ImportError:
            logger.error("pandas not available for Excel processing")
            return []
        
        try:
            df = pd.read_excel(io.BytesIO(document_content), engine='openpyxl', header=1)
            
            logger.info(f"📊 Excel file {filename}: {len(df)} data rows found")
            logger.info(f"📋 Headers from row 2: {list(df.columns)}")
            
            articles = []
            
            for index, row in df.iterrows():
                try:
                    actual_row_number = index + 3
                    
                    article_content = None
                    if 'Article' in df.columns:
                        content = row.get('Article')
                        if pd.notna(content) and str(content).strip():
                            article_content = str(content).strip()
                    
                    article_title = None
                    if 'Title' in df.columns:
                        title = row.get('Title')
                        if pd.notna(title) and str(title).strip():
                            article_title = str(title).strip()
                    
                    article_link = None
                    if 'Article Link' in df.columns:
                        link = row.get('Article Link')
                        if pd.notna(link) and str(link).strip():
                            article_link = str(link).strip()
                    
                    source_info = None
                    if 'Source' in df.columns:
                        source = row.get('Source')
                        if pd.notna(source) and str(source).strip():
                            source_info = str(source).strip()
                    else:
                        first_col = df.columns[0]
                        source = row.get(first_col)
                        if pd.notna(source) and str(source).strip():
                            source_info = str(source).strip()
                    
                    if not article_content:
                        logger.warning(f"⚠️ Row {actual_row_number}: No article content found, skipping")
                        continue
                    
                    if len(article_content) < 50:
                        logger.warning(f"⚠️ Row {actual_row_number}: Article content too short ({len(article_content)} chars), skipping")
                        continue
                    
                    source_url = article_link or f"{filename.replace('.xlsx', '')}_row_{actual_row_number}"
                    
                    article = {
                        "content": article_content,
                        "title": article_title or f"Article {actual_row_number}",
                        "source_url": source_url,
                        "article_link": article_link or "",
                        "source_info": source_info or "",
                        "row_index": actual_row_number,
                        "original_file": filename,
                        "bucket_source": bucket
                    }
                    
                    articles.append(article)
                    logger.info(f"✅ Row {actual_row_number}: Successfully processed as article")
                    
                except Exception as e:
                    logger.warning(f"❌ Failed to process row {actual_row_number}: {e}")
                    continue
            
            logger.info(f"🎉 Successfully extracted {len(articles)} articles from {filename}")
            
            if len(articles) == 0:
                raise Exception(f"No valid articles found in Excel file. Expected 'Article' column but found: {list(df.columns)}")
            
            return articles
            
        except Exception as e:
            logger.error(f"💥 Failed to extract articles from {filename}: {e}")
            raise Exception(f"Excel article extraction failed: {e}")
    
    def _create_article_chunks(self, article: Dict[str, Any], bucket: str) -> List[ChunkData]:
        """Create chunks for a single news article - sync"""
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:
            logger.error("langchain not available for text splitting")
            return []
        
        content = article["content"]
        if len(content.strip()) < 50:
            return []
        
        chunk_config = config.get_chunking_config(bucket)
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_config["chunk_size"],
            chunk_overlap=int(chunk_config["chunk_size"] * chunk_config["overlap_ratio"]),
            separators=chunk_config["separators"],
            length_function=len
        )
        
        text_chunks = text_splitter.split_text(content)
        chunks = []
        
        for chunk_index, chunk_text in enumerate(text_chunks):
            chunk_data = ChunkData(
                chunk_id=str(uuid.uuid4()),
                doc_name=article["source_url"],
                bucket_source=bucket,
                chunk_text=chunk_text.strip(),
                chunk_index=chunk_index,
                token_count=len(chunk_text.split()),
                processing_timestamp=datetime.now().isoformat(),
                chunk_metadata={
                    "element_type": "news_article",
                    "article_title": article["title"],
                    "source_url": article["source_url"],
                    "article_link": article["article_link"],
                    "source_info": article["source_info"],
                    "chunk_strategy": "news_excel_article",
                    "total_chunks": len(text_chunks),
                    "row_index": article["row_index"],
                    "original_file": article["original_file"],
                    "specialized_chunker": "NewsExcelProcessor",
                    "priority": "medium"
                }
            )
            chunks.append(chunk_data)
        
        return chunks
    
    def _create_article_summary(self, article: Dict[str, Any], bucket: str) -> Optional[SummaryData]:
        """Create summary for a single news article - sync"""
        try:
            summarizer = SummarizerFactory.get_summarizer(bucket)
            
            extracted_content = {
                "type": "news_article",
                "full_text": article["content"],
                "title": article["title"],
                "source_url": article["source_url"],
                "article_link": article["article_link"],
                "source_info": article["source_info"],
                "file_type": "excel_article"
            }
            
            summary_data = summarizer.create_summary(extracted_content, article["source_url"], bucket)
            
            if summary_data:
                summary_data.document_metadata.update({
                    "source_url": article["source_url"],
                    "article_link": article["article_link"],
                    "source_info": article["source_info"],
                    "row_index": article["row_index"],
                    "original_file": article["original_file"]
                })
            
            return summary_data
            
        except Exception as e:
            logger.error(f"Failed to create summary for article {article.get('source_url', 'unknown')}: {e}")
            return None
    
    def _elements_to_structured_content(self, elements: List[Dict[str, Any]], filename: str) -> Dict[str, Any]:
        """Convert extracted elements to structured content format"""
        
        text_parts = []
        tables = []
        figures = []
        
        for element in elements:
            element_type = element.get("type", "")
            text = element.get("text", "").strip()
            
            if not text:
                continue
            
            if element_type == "Table":
                tables.append({"content": text, "metadata": element.get("metadata", {})})
            elif element_type == "FigureCaption":
                figures.append({"caption": text, "metadata": element.get("metadata", {})})
            elif element_type in ["Title", "NarrativeText", "ListItem"]:
                text_parts.append(text)
        
        return {
            "type": "regular_document",
            "full_text": "\n\n".join(text_parts),
            "tables": tables,
            "figures": figures,
            "elements_count": len(elements),
            "file_type": self._detect_file_type(filename)
        }
    
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
        else:
            return "unknown"
    
    async def cleanup(self):
        """Cleanup resources"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
        if hasattr(self, 'embedder'):
            await self.embedder.cleanup()


class AsyncEmbeddingProcessor:
    """Async embedding generation with concurrent processing"""

    def __init__(self):
        self.embedding_url = config.get('ollama.embedding_url')
        self.model = config.get('ollama.embedding_model')
        # Chunk-specific embedding model (Qwen3-Embedding-0.6B)
        self.chunk_model = config.get('ollama.chunk_embedding_model')
        self.chunk_embedding_dim = config.get('ollama.chunk_embedding_dim')
        self.timeout = config.get('ollama.timeout')
        self.headers = config.get('ollama.headers')
        self._session = None

        logger.info(f"📊 Embedding config - Chunks: {self.chunk_model} ({self.chunk_embedding_dim}D), Summaries: {self.model}")
    
    async def _get_session(self):
        """Get or create aiohttp session"""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self._session
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using default model (for summaries) - async"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        cleaned_text = text.strip()[:4000]

        payload = {"model": self.model, "prompt": cleaned_text}

        try:
            session = await self._get_session()

            async with session.post(self.embedding_url, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Embedding API error: {response.status}")

                result = await response.json()
                embedding = result.get("embedding", [])

                if not embedding:
                    raise Exception("Empty embedding returned")

                return embedding

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 768

    async def generate_chunk_embedding(self, text: str) -> List[float]:
        """Generate embedding for chunk text using Qwen3-Embedding model - async"""
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        cleaned_text = text.strip()[:4000]

        payload = {"model": self.chunk_model, "prompt": cleaned_text}

        try:
            session = await self._get_session()

            async with session.post(self.embedding_url, json=payload) as response:
                if response.status != 200:
                    raise Exception(f"Chunk embedding API error: {response.status}")

                result = await response.json()
                embedding = result.get("embedding", [])

                if not embedding:
                    raise Exception("Empty chunk embedding returned")

                return embedding

        except Exception as e:
            logger.error(f"Chunk embedding generation failed: {e}")
            return [0.0] * self.chunk_embedding_dim
    
    async def process_chunks(self, chunks: List[ChunkData]) -> List[Dict[str, Any]]:
        """Process chunks with embeddings - async with concurrency"""
        enriched_chunks = []
        
        batch_size = 10
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            batch_tasks = []
            
            for chunk in batch:
                task = self._process_single_chunk(chunk)
                batch_tasks.append(task)
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for chunk, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to generate embedding for chunk {chunk.chunk_id}: {result}")
                    fallback_chunk = self._create_fallback_chunk(chunk)
                    enriched_chunks.append(fallback_chunk)
                else:
                    enriched_chunks.append(result)
        
        logger.info(f"Generated embeddings for {len(enriched_chunks)}/{len(chunks)} chunks")
        return enriched_chunks
    
    async def _process_single_chunk(self, chunk: ChunkData) -> Dict[str, Any]:
        """Process single chunk with embedding using Qwen3-Embedding model"""
        embedding = await self.generate_chunk_embedding(chunk.chunk_text)

        enriched_chunk = {
            "chunk_id": chunk.chunk_id,
            "bucket_source": chunk.bucket_source,
            "chunk_text": chunk.chunk_text,
            "chunk_index": chunk.chunk_index,
            "token_count": chunk.token_count,
            "processing_timestamp": chunk.processing_timestamp,
            "embedding": embedding
        }

        if chunk.bucket_source == "news":
            source_url = chunk.chunk_metadata.get("source_url") if chunk.chunk_metadata else chunk.doc_name
            enriched_chunk["source_url"] = source_url
        else:
            enriched_chunk["doc_name"] = chunk.doc_name

        return enriched_chunk
    
    def _create_fallback_chunk(self, chunk: ChunkData) -> Dict[str, Any]:
        """Create fallback chunk with zero embedding using chunk embedding dimension"""
        fallback_chunk = {
            "chunk_id": chunk.chunk_id,
            "bucket_source": chunk.bucket_source,
            "chunk_text": chunk.chunk_text,
            "chunk_index": chunk.chunk_index,
            "token_count": chunk.token_count,
            "processing_timestamp": chunk.processing_timestamp,
            "embedding": [0.0] * self.chunk_embedding_dim
        }

        if chunk.bucket_source == "news":
            source_url = chunk.chunk_metadata.get("source_url") if chunk.chunk_metadata else chunk.doc_name
            fallback_chunk["source_url"] = source_url
        else:
            fallback_chunk["doc_name"] = chunk.doc_name

        return fallback_chunk
    
    async def process_summary(self, summary_data: SummaryData) -> Dict[str, Any]:
        """Process summary with embedding - async"""
        try:
            embedding = await self.generate_embedding(summary_data.abstractive_summary)
            
            enriched_summary = {
                "summary_id": str(uuid.uuid4()),
                "bucket_source": summary_data.bucket_source,
                "document_type": summary_data.document_type,
                "abstractive_summary": summary_data.abstractive_summary,
                "title": summary_data.document_metadata.get("title", summary_data.doc_name),
                "processing_timestamp": summary_data.processing_timestamp or datetime.now().isoformat(),
                "embedding": embedding
            }
            
            if summary_data.bucket_source == "news":
                source_url = summary_data.document_metadata.get("source_url", summary_data.doc_name)
                enriched_summary["source_url"] = source_url
            else:
                enriched_summary["doc_name"] = summary_data.doc_name
            
            logger.info(f"Generated embedding for summary")
            return enriched_summary
            
        except Exception as e:
            logger.error(f"Failed to generate embedding for summary: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup aiohttp session"""
        if self._session:
            await self._session.close()


# Create the processor instance and export it properly
processor = AsyncDocumentProcessor()

# For backward compatibility
embedder = processor.embedder