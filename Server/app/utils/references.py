import asyncio
from typing import Any, Dict, List
from app.config import get_settings
from app.services.external.minio import get_minio_client
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def process_references_with_shareable_urls_and_count(
    chunks: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]], 
    graph_data: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process and deduplicate references with MinIO public shareable URLs.
    Graph data with document_name is now processed for URL generation.
    """
    
    total_graph_items = len(graph_data) if graph_data else 0
    
    # Filter graph data and separate those with document_name
    relevant_graph_data = []
    graph_documents = []
    
    if graph_data:
        min_score = getattr(settings, 'GRAPH_MIN_RELEVANCE_SCORE', 0.3)
        for item in graph_data:
            if item and item.get('similarity_score', 0.0) >= min_score:
                relevant_graph_data.append(item)
                
                # Check if graph item has document_name for URL processing
                document_name = item.get('document_name') or item.get('metadata', {}).get('document_name')
                if document_name and document_name.lower() not in ['unknown', 'test', '']:
                    graph_documents.append(item)
    
    minio_client = get_minio_client()
    
    # Create tasks for parallel processing
    tasks = []
    
    # Process chunks
    if chunks:
        chunk_task = asyncio.create_task(
            _process_chunks_parallel_with_shareable_urls(chunks, minio_client)
        )
        tasks.append(chunk_task)
    else:
        tasks.append(asyncio.create_task(_get_empty_list()))
    
    # Process summaries
    if summaries:
        summary_task = asyncio.create_task(
            _process_summaries_parallel_with_shareable_urls(summaries, minio_client)
        )
        tasks.append(summary_task)
    else:
        tasks.append(asyncio.create_task(_get_empty_list()))
    
    # Process graph documents with document_name
    if graph_documents:
        graph_docs_task = asyncio.create_task(
            _process_graph_documents_parallel_with_shareable_urls(graph_documents, minio_client)
        )
        tasks.append(graph_docs_task)
    else:
        tasks.append(asyncio.create_task(_get_empty_list()))
    
    # Execute all URL processing tasks in parallel
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error in parallel shareable URL processing: {e}")
        results = [[], [], []]
    
    # Handle results
    chunk_refs = results[0] if not isinstance(results[0], Exception) else []
    summary_refs = results[1] if not isinstance(results[1], Exception) else []
    graph_doc_refs = results[2] if not isinstance(results[2], Exception) else []
    
    # Combine all references
    all_references = chunk_refs + summary_refs + graph_doc_refs
    
    # Filter and deduplicate
    valid_references = _filter_references_with_valid_shareable_urls(all_references)
    deduplicated_refs = _deduplicate_references_with_news(valid_references)
    
    # Calculate total_references including remaining graph data
    graph_items_without_docs = len(relevant_graph_data) - len(graph_documents)
    total_after_deduplication = len(deduplicated_refs) + graph_items_without_docs
    
    # Sort and limit
    sorted_refs = sorted(
        deduplicated_refs,
        key=lambda x: x.get("similarity_score", 0.0),
        reverse=True
    )
    final_refs = sorted_refs[:settings.MAX_REFERENCES]
    
    return {
        "sources": final_refs,
        "total_references": total_after_deduplication
    }


async def _process_chunks_parallel_with_shareable_urls(
    chunks: List[Dict[str, Any]], 
    minio_client
) -> List[Dict[str, Any]]:
    """Process chunks in parallel with MinIO shareable URL generation."""
    
    tasks = []
    for i, chunk in enumerate(chunks):
        task = asyncio.create_task(
            _extract_reference_from_chunk_with_shareable_url(chunk, minio_client, i)
        )
        tasks.append(task)
    
    try:
        semaphore = asyncio.Semaphore(8)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_task(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        chunk_refs = [ref for ref in results if ref and not isinstance(ref, Exception)]
        return chunk_refs
        
    except Exception as e:
        logger.error(f"Error processing chunks with shareable URLs: {e}")
        return []


async def _process_summaries_parallel_with_shareable_urls(
    summaries: List[Dict[str, Any]], 
    minio_client
) -> List[Dict[str, Any]]:
    """Process summaries in parallel with MinIO shareable URL generation."""
    
    tasks = []
    for i, summary in enumerate(summaries):
        task = asyncio.create_task(
            _extract_reference_from_summary_with_shareable_url(summary, minio_client, i)
        )
        tasks.append(task)
    
    try:
        semaphore = asyncio.Semaphore(8)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_task(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        summary_refs = [ref for ref in results if ref and not isinstance(ref, Exception)]
        return summary_refs
        
    except Exception as e:
        logger.error(f"Error processing summaries with shareable URLs: {e}")
        return []


async def _process_graph_documents_parallel_with_shareable_urls(
    graph_documents: List[Dict[str, Any]], 
    minio_client
) -> List[Dict[str, Any]]:
    """Process graph documents with document_name in parallel with MinIO shareable URL generation."""
    
    tasks = []
    for i, graph_doc in enumerate(graph_documents):
        task = asyncio.create_task(
            _extract_reference_from_graph_document_with_shareable_url(graph_doc, minio_client, i)
        )
        tasks.append(task)
    
    try:
        semaphore = asyncio.Semaphore(8)
        
        async def limited_task(task):
            async with semaphore:
                return await task
        
        limited_tasks = [limited_task(task) for task in tasks]
        results = await asyncio.gather(*limited_tasks, return_exceptions=True)
        
        graph_doc_refs = [ref for ref in results if ref and not isinstance(ref, Exception)]
        return graph_doc_refs
        
    except Exception as e:
        logger.error(f"Error processing graph documents with shareable URLs: {e}")
        return []


async def _extract_reference_from_chunk_with_shareable_url(
    chunk: Dict[str, Any],
    minio_client,
    index: int
) -> Dict[str, Any]:
    """Extract clean reference from a document chunk with MinIO shareable URL generation."""

    try:
        doc_name = chunk.get("doc_name", "")
        bucket_source = chunk.get("bucket_source", "").lower()

        # Check if doc_name is a URL (news article) - prioritize URL detection over bucket
        is_url = doc_name.startswith('http://') or doc_name.startswith('https://')
        is_news = is_url or bucket_source == "news" or chunk.get("collection") == "News"

        if is_news or is_url:
            source_url = doc_name or chunk.get("source_url", "")
            doc_name = source_url
            title = _create_title_from_news_url(source_url) or "News Article"
            url = source_url

            if not _is_valid_news_url(url):
                return None
        else:
            doc_name = doc_name or "Unknown Document"
            title = _clean_document_name(doc_name)
            url = await minio_client.generate_shareable_reference_url(doc_name, bucket_source)

            if not _is_valid_shareable_url(url):
                return None

        raw_score = (
            chunk.get("rerank_score") or
            chunk.get("similarity_score") or
            chunk.get("score", 0.0)
        )
        similarity_score = round(float(raw_score) * 100, 1)

        return {
            "title": title,
            "doc_name": doc_name,
            "url": url,
            "similarity_score": similarity_score
        }

    except Exception as e:
        logger.warning(f"Error extracting chunk reference {index}: {e}")
        return None


async def _extract_reference_from_summary_with_shareable_url(
    summary: Dict[str, Any],
    minio_client,
    index: int
) -> Dict[str, Any]:
    """Extract clean reference from a summary document with MinIO shareable URL generation."""

    try:
        doc_name = summary.get("doc_name", "") or summary.get("title", "")
        bucket_source = summary.get("bucket_source", "").lower()

        # Check if doc_name is a URL (news article) - prioritize URL detection over bucket
        is_url = doc_name.startswith('http://') or doc_name.startswith('https://')
        is_news = is_url or bucket_source == "news" or summary.get("collection") == "News"

        if is_news or is_url:
            source_url = doc_name or summary.get("source_url", "")
            doc_name = source_url
            title = _create_title_from_news_url(source_url) or "News Article"
            url = source_url

            if not _is_valid_news_url(url):
                return None
        else:
            doc_name = doc_name or "Unknown Document"
            title = _clean_document_name(doc_name)
            url = await minio_client.generate_shareable_reference_url(doc_name, bucket_source)

            if not _is_valid_shareable_url(url):
                return None

        raw_score = (
            summary.get("rerank_score") or
            summary.get("similarity_score") or
            summary.get("score", 0.0)
        )
        similarity_score = round(float(raw_score) * 100, 1)

        return {
            "title": title,
            "doc_name": doc_name,
            "url": url,
            "similarity_score": similarity_score
        }

    except Exception as e:
        logger.warning(f"Error extracting summary reference {index}: {e}")
        return None


async def _extract_reference_from_graph_document_with_shareable_url(
    graph_doc: Dict[str, Any],
    minio_client,
    index: int
) -> Dict[str, Any]:
    """Extract clean reference from a GraphRAG document with MinIO shareable URL generation."""

    try:
        # Get document name from graph document
        document_name = (
            graph_doc.get("document_name") or
            graph_doc.get("metadata", {}).get("document_name") or
            graph_doc.get("doc_name")
        )

        if not document_name or document_name.lower() in ['unknown', 'test', '']:
            return None

        # IMPORTANT: Check if document_name is a URL first (news articles)
        # This prevents trying to find URLs in MinIO buckets
        is_url = document_name.startswith('http://') or document_name.startswith('https://')

        if is_url:
            # This is a news article URL - use it directly, don't search MinIO
            title = _create_title_from_news_url(document_name) or "News Article"
            url = document_name
            doc_name = document_name

            if not _is_valid_news_url(url):
                return None
        else:
            # This is a regular document (PDF, etc.) - get from MinIO
            bucket_source = (
                graph_doc.get("bucket") or
                graph_doc.get("metadata", {}).get("bucket") or
                graph_doc.get("metadata", {}).get("bucket_source") or
                "researchpapers"  # Default for non-URL documents
            )

            doc_name = document_name
            title = _clean_document_name(document_name)
            url = await minio_client.generate_shareable_reference_url(document_name, bucket_source)

            if not _is_valid_shareable_url(url):
                return None

        raw_score = (
            graph_doc.get("similarity_score") or
            graph_doc.get("score") or
            graph_doc.get("relevance_score", 0.0)
        )
        similarity_score = round(float(raw_score) * 100, 1)

        return {
            "title": title,
            "doc_name": doc_name,
            "url": url,
            "similarity_score": similarity_score
        }

    except Exception as e:
        logger.warning(f"Error extracting graph document reference {index}: {e}")
        return None


def _create_title_from_news_url(source_url: str) -> str:
    """Create a readable title from a news URL."""
    if not source_url:
        return "News Article"
    
    try:
        if "://" in source_url:
            domain_part = source_url.split("://")[1].split("/")[0]
            domain_part = domain_part.replace("www.", "")
            
            if "." in domain_part:
                domain_name = domain_part.split(".")[0].title()
                return f"{domain_name} News Article"
            else:
                return domain_part.title() + " Article"
        else:
            return "News Article"
    except Exception:
        return "News Article"


def _is_valid_news_url(url: str) -> bool:
    """Check if a URL is valid for news items."""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    if not url or len(url) < 10:
        return False
    
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    
    if "//" not in url or url.count("//") > 1:
        return False
    
    try:
        domain_part = url.split("//")[1].split("/")[0]
        if "." not in domain_part and domain_part != "localhost":
            return False
        if not domain_part:
            return False
    except (IndexError, AttributeError):
        return False
    
    return True


def _is_valid_shareable_url(url: str) -> bool:
    """Check if a URL is valid for shareable references."""
    if not url or not isinstance(url, str):
        return False
    
    url = url.strip()
    
    if not url or url.startswith("#") or len(url) < 10:
        return False
    
    placeholder_indicators = ["placeholder", "example.com", "unknown", "not-found", "missing", "fallback"]
    url_lower = url.lower()
    if any(indicator in url_lower for indicator in placeholder_indicators):
        return False
    
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    
    if "//" not in url or url.count("//") > 1:
        return False
    
    try:
        domain_part = url.split("//")[1].split("/")[0]
        if "." not in domain_part and domain_part != "localhost":
            return False
        if not domain_part:
            return False
    except (IndexError, AttributeError):
        return False
    
    return True


def _filter_references_with_valid_shareable_urls(references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter references to only include those with valid shareable URLs."""
    if not references:
        return []
    
    valid_references = []
    
    for ref in references:
        if not ref:
            continue
        
        url = ref.get("url", "")
        is_news = ref.get("bucket_source", "").lower() == "news"
        
        if is_news:
            is_valid = _is_valid_news_url(url)
        else:
            is_valid = _is_valid_shareable_url(url)
        
        if is_valid:
            valid_references.append(ref)
    
    return valid_references


def _deduplicate_references_with_news(references: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deduplicate references by doc_name, keeping highest scoring one."""
    
    if not references:
        return []
    
    doc_groups = {}
    
    for ref in references:
        if not ref:
            continue
            
        doc_name = ref.get("doc_name", "").lower()
        if not doc_name:
            continue
        
        if doc_name not in doc_groups:
            doc_groups[doc_name] = []
        doc_groups[doc_name].append(ref)
    
    deduplicated = []
    
    for doc_name, refs in doc_groups.items():
        if not refs:
            continue
        
        best_ref = max(refs, key=lambda x: x.get("similarity_score", 0.0))
        deduplicated.append(best_ref)
    
    return deduplicated


def _clean_document_name(doc_name: str) -> str:
    """Clean and standardize document names for display title."""
    if not doc_name or doc_name.lower() in ["unknown", "unknown document"]:
        return "Climate Document"
    
    # Remove file extensions
    if "." in doc_name:
        name_parts = doc_name.split(".")
        if len(name_parts) > 1 and len(name_parts[-1]) <= 5:
            doc_name = ".".join(name_parts[:-1])
    
    # Clean up patterns
    doc_name = doc_name.replace("_", " ").replace("-", " ")
    
    # Capitalize
    words = doc_name.split()
    cleaned_words = []
    for word in words:
        if len(word) > 3:
            cleaned_words.append(word.capitalize())
        else:
            cleaned_words.append(word.upper() if word.isupper() else word.lower())
    
    cleaned_name = " ".join(cleaned_words)
    
    # Limit length
    if len(cleaned_name) > 80:
        cleaned_name = cleaned_name[:77] + "..."
    
    return cleaned_name


async def _get_empty_list() -> List:
    """Return empty list for parallel processing."""
    return []


# Main function
async def process_references_with_urls_and_count(
    chunks: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]], 
    graph_data: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main function - processes references with MinIO public shareable URLs and GraphRAG support.
    """
    return await process_references_with_shareable_urls_and_count(chunks, summaries, graph_data)


# Legacy compatibility
async def process_references_with_urls(
    chunks: List[Dict[str, Any]],
    summaries: List[Dict[str, Any]], 
    graph_data: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Legacy function - returns only URL-based sources."""
    result = await process_references_with_shareable_urls_and_count(chunks, summaries, graph_data)
    return result["sources"]