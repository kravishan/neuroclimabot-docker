"""
Support API - RAG Search, STP Search, and Translation Services

Provides:
- RAG search (chunks, summaries, hybrid)
- STP (Social Tipping Points) search
- Translation services (in/out)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["support"])

# ============================================================================
# TRANSLATION SERVICES
# ============================================================================

# Language code mapping
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'it': 'Italian',
    'pt': 'Portuguese',
    'el': 'Greek'
}

# Model cache
models_cache = {}
tokenizers_cache = {}
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="translation_worker")


class TranslateInRequest(BaseModel):
    text: str


class TranslateOutRequest(BaseModel):
    target_lang: str
    title: Optional[str] = None
    response: Optional[str] = None
    social_tipping_point: Optional[Dict[str, Any]] = None


def detect_language(text: str) -> str:
    """Detect the language of the input text"""
    try:
        from langdetect import detect
        detected_lang = detect(text)
        logger.info(f"Detected language: {detected_lang}")

        if detected_lang in SUPPORTED_LANGUAGES:
            return detected_lang

        if detected_lang in ['pt-br', 'pt-pt']:
            return 'pt'

        logger.warning(f"Unsupported language detected: {detected_lang}, defaulting to English")
        return 'en'

    except Exception as e:
        logger.warning(f"Language detection failed: {str(e)}, defaulting to English")
        return 'en'


def get_model_name(source_lang: str, target_lang: str) -> str:
    """Get the Opus-MT model name for language pair"""
    model_map = {
        ('it', 'en'): 'Helsinki-NLP/opus-mt-it-en',
        ('pt', 'en'): 'Helsinki-NLP/opus-mt-roa-en',
        ('el', 'en'): 'Helsinki-NLP/opus-mt-grk-en',  # Fixed: Use tc-big model for Greek
        ('en', 'it'): 'Helsinki-NLP/opus-mt-en-it',
        ('en', 'pt'): 'Helsinki-NLP/opus-mt-en-roa',
        ('en', 'el'): 'Helsinki-NLP/opus-mt-en-el'
    }
    return model_map.get((source_lang, target_lang))


def load_translation_model(source_lang: str, target_lang: str):
    """Load translation model and tokenizer with caching"""
    from transformers import MarianMTModel, MarianTokenizer

    key = f"{source_lang}-{target_lang}"

    if key in models_cache:
        return models_cache[key], tokenizers_cache[key]

    model_name = get_model_name(source_lang, target_lang)
    if not model_name:
        raise ValueError(f"Translation from {source_lang} to {target_lang} not supported")

    logger.info(f"Loading model: {model_name}")
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)

    models_cache[key] = model
    tokenizers_cache[key] = tokenizer

    return model, tokenizer


def translate_text_sync(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text from source language to target language - sync"""
    if not text or not text.strip():
        return text

    if source_lang == target_lang:
        return text

    try:
        model, tokenizer = load_translation_model(source_lang, target_lang)

        inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        translated = model.generate(**inputs)
        translated_text = tokenizer.decode(translated[0], skip_special_tokens=True)

        return translated_text
    except Exception as e:
        logger.error(f"Translation error: {str(e)}")
        return text


async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """Translate text asynchronously"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, translate_text_sync, text, source_lang, target_lang)


@router.get("/translate/health")
async def translation_health():
    """Translation health check"""
    return {
        "status": "healthy",
        "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        "features": {
            "automatic_language_detection": True,
            "skip_translation_for_english": True
        },
        "timestamp": datetime.now().isoformat()
    }


@router.post("/translate/in")
async def translate_in(request: TranslateInRequest):
    """Translate incoming user query from any language to English"""
    try:
        text = request.text

        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        detected_lang = await asyncio.get_event_loop().run_in_executor(
            _executor, detect_language, text
        )

        if detected_lang == 'en':
            logger.info(f"Text is already in English, no translation needed")
            return {
                'translated_text': text,
                'detected_language': 'en',
                'is_english': True,
                'message': 'No translation needed, text is already in English'
            }

        translated_text = await translate_text(text, detected_lang, 'en')

        logger.info(f"Translated IN: {detected_lang} -> en")

        return {
            'translated_text': translated_text,
            'detected_language': detected_lang,
            'is_english': False,
            'original_text': text
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /translate/in: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/translate/out")
async def translate_out(request: TranslateOutRequest):
    """Translate outgoing response from English to target language - PARALLEL VERSION"""
    try:
        target_lang = request.target_lang.lower()

        if target_lang not in ['en', 'it', 'pt', 'el']:
            raise HTTPException(
                status_code=400,
                detail=f'Unsupported language: {target_lang}'
            )

        # Skip translation if target language is English
        if target_lang == 'en':
            translated_response = {'target_lang': target_lang}
            if request.title:
                translated_response['title'] = request.title
            if request.response:
                translated_response['response'] = request.response
            if request.social_tipping_point:
                translated_response['social_tipping_point'] = request.social_tipping_point
            return translated_response

        # Collect all translation tasks to execute in parallel
        translation_tasks = []
        field_mapping = []

        if request.title:
            translation_tasks.append(translate_text(request.title, 'en', target_lang))
            field_mapping.append(('title', None))

        if request.response:
            translation_tasks.append(translate_text(request.response, 'en', target_lang))
            field_mapping.append(('response', None))

        if request.social_tipping_point and isinstance(request.social_tipping_point, dict):
            if 'text' in request.social_tipping_point:
                translation_tasks.append(translate_text(request.social_tipping_point['text'], 'en', target_lang))
                field_mapping.append(('stp_text', None))

            if 'qualifying_factors' in request.social_tipping_point:
                factors = request.social_tipping_point['qualifying_factors']
                if isinstance(factors, list):
                    for i, factor in enumerate(factors):
                        translation_tasks.append(translate_text(factor, 'en', target_lang))
                        field_mapping.append(('qualifying_factor', i))

        # Execute all translations in parallel
        if translation_tasks:
            translated_results = await asyncio.gather(*translation_tasks)
        else:
            translated_results = []

        # Build response from parallel results
        translated_response = {'target_lang': target_lang}

        for i, (field_type, index) in enumerate(field_mapping):
            if field_type == 'title':
                translated_response['title'] = translated_results[i]
            elif field_type == 'response':
                translated_response['response'] = translated_results[i]
            elif field_type == 'stp_text':
                if 'social_tipping_point' not in translated_response:
                    translated_response['social_tipping_point'] = {}
                translated_response['social_tipping_point']['text'] = translated_results[i]
            elif field_type == 'qualifying_factor':
                if 'social_tipping_point' not in translated_response:
                    translated_response['social_tipping_point'] = {}
                if 'qualifying_factors' not in translated_response['social_tipping_point']:
                    translated_response['social_tipping_point']['qualifying_factors'] = []
                translated_response['social_tipping_point']['qualifying_factors'].append(translated_results[i])

        logger.info(f"Translated OUT: en -> {target_lang} (parallel: {len(translation_tasks)} fields)")

        return translated_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /translate/out: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# STP SEARCH SERVICES
# ============================================================================

class STPSearchRequest(BaseModel):
    text: str
    top_k: int = Field(default=5, ge=1, le=100)
    include_metadata: bool = True
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score (0.0 to 1.0)")


class STPSearchService:
    """STP (Social Tipping Points) Search Service"""

    def __init__(self):
        from config import config
        stp_milvus_config = config.get_stp_milvus_config()
        self.db_name = stp_milvus_config['database']
        self.collection_name = stp_milvus_config['collection']
        self.embedding_dim = 384
        self.connection = None
        self.collection = None
        self._pymilvus_available = False
        self._connect()

    def _connect(self):
        """Connect to Milvus STP database"""
        try:
            from pymilvus import connections, Collection, utility
            from config import config

            self._pymilvus_available = True

            milvus_config = config.get('milvus')

            logger.info(f"🔌 Connecting to Milvus for STP service at {milvus_config['host']}:{milvus_config['port']}")

            if milvus_config.get('user') and milvus_config.get('password'):
                connections.connect(
                    alias="stp_connection",
                    host=milvus_config['host'],
                    port=milvus_config['port'],
                    user=milvus_config['user'],
                    password=milvus_config['password']
                )
            else:
                connections.connect(
                    alias="stp_connection",
                    host=milvus_config['host'],
                    port=milvus_config['port']
                )

            # Switch to STP database
            from pymilvus import db
            db.using_database(self.db_name, using="stp_connection")
            logger.info(f"📂 Using STP database: {self.db_name}")

            # Check if collection exists
            if utility.has_collection(self.collection_name, using="stp_connection"):
                self.collection = Collection(self.collection_name, using="stp_connection")
                self.collection.load()
                self.connection = True
                logger.info(f"✅ STP collection loaded: {self.collection_name}")
            else:
                logger.error(f"❌ STP collection not found: {self.collection_name}")
                self.connection = False

        except ImportError:
            logger.warning("⚠️ pymilvus not installed - STP service will not be available")
            self._pymilvus_available = False
            self.connection = False
        except Exception as e:
            logger.error(f"❌ STP Milvus connection failed: {e}")
            self.connection = False
            self._pymilvus_available = False

    def health_check(self) -> bool:
        """Check STP service health"""
        if not self._pymilvus_available or not self.connection or not self.collection:
            return False
        try:
            _ = self.collection.num_entities
            return True
        except Exception:
            return False

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for search query using local Ollama (separate from GraphRAG)"""
        import requests
        import os
        from config import config

        try:
            ollama_config = config.get('ollama')

            # STP uses LOCAL Ollama with sentence-transformers/all-MiniLM-L6-v2
            # This is SEPARATE from GraphRAG which uses remote API endpoints
            # Use STP-specific config if set, otherwise default to local Ollama
            stp_api_base = os.getenv('STP_EMBEDDING_API_BASE', 'http://localhost:11434')
            # STP_EMBEDDING_MODEL from .env (use Ollama model name format: all-minilm:l6-v2)
            stp_model = os.getenv('STP_EMBEDDING_MODEL', 'all-minilm:l6-v2')

            # Use Ollama native API format for local embeddings
            embedding_url = f"{stp_api_base.rstrip('/')}/api/embeddings"

            logger.info(f"🔗 [STP] Calling local embedding API: {embedding_url}")
            logger.info(f"📦 [STP] Using model: {stp_model}")

            response = requests.post(
                embedding_url,
                json={
                    "model": stp_model,
                    "prompt": text[:4000]
                },
                timeout=float(ollama_config.get('timeout', 120))
            )

            if response.status_code == 200:
                result = response.json()

                # Handle both OpenAI-compatible format and Ollama native format
                if "data" in result and len(result["data"]) > 0:
                    # OpenAI-compatible format: {"data": [{"embedding": [...]}]}
                    embedding = result["data"][0].get("embedding", [])
                else:
                    # Ollama native format: {"embedding": [...]}
                    embedding = result.get("embedding", [])

                if not embedding:
                    logger.error("❌ [STP] No embedding returned from API")
                    return [0.0] * self.embedding_dim

                # Handle embedding dimension mismatch dynamically
                if len(embedding) != self.embedding_dim:
                    logger.info(f"📊 [STP] Embedding dimension: {len(embedding)} (expected {self.embedding_dim})")
                    # Update expected dimension if this is first successful embedding
                    self.embedding_dim = len(embedding)

                return embedding
            else:
                logger.error(f"❌ [STP] Embedding API error: {response.status_code}")
                logger.error(f"❌ [STP] Response: {response.text[:500]}")
                return [0.0] * self.embedding_dim

        except Exception as e:
            logger.error(f"❌ [STP] Embedding generation failed: {e}")
            return [0.0] * self.embedding_dim

    async def search(self, query_text: str, top_k: int = 5, include_metadata: bool = True,
                    min_similarity: float = 0.0) -> Dict[str, Any]:
        """Search STP documents with minimum similarity filtering"""
        if not self.connection or not self.collection:
            raise Exception("STP service not available")

        try:
            query_embedding = await self.generate_embedding(query_text)

            output_fields = [
                "doc_name",
                "stp_confidence",
                "rephrased_content",
                "chunk_id",
                "tokens"
            ]

            if include_metadata:
                output_fields.extend([
                    "original_content",
                    "qualifying_factors"
                ])

            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }

            logger.info(f"🔍 Searching STP documents with query: {query_text[:100]}...")
            logger.info(f"📊 Min similarity threshold: {min_similarity}")

            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=output_fields
            )

            formatted_results = []
            filtered_count = 0

            for hits in results:
                for hit in hits:
                    similarity_score = float(1 - hit.distance)

                    if similarity_score < min_similarity:
                        filtered_count += 1
                        logger.debug(f"⏭️ Filtered out result with similarity {similarity_score:.4f} < {min_similarity}")
                        continue

                    result_dict = {
                        "id": hit.id,
                        "doc_name": hit.entity.get("doc_name", ""),
                        "stp_confidence": float(hit.entity.get("stp_confidence", 0.0)),
                        "rephrased_content": hit.entity.get("rephrased_content", ""),
                        "chunk_id": hit.entity.get("chunk_id", ""),
                        "tokens": int(hit.entity.get("tokens", 0)),
                        "similarity_score": similarity_score
                    }

                    if include_metadata:
                        result_dict["original_content"] = hit.entity.get("original_content", "")
                        result_dict["qualifying_factors"] = hit.entity.get("qualifying_factors", "")

                    formatted_results.append(result_dict)

            if not formatted_results:
                logger.info(f"⚠️ No results found with similarity >= {min_similarity} (filtered {filtered_count} results)")
                return {
                    "status": "success",
                    "query": query_text,
                    "total_results": 0,
                    "top_k": top_k,
                    "min_similarity": min_similarity,
                    "results": [],
                    "message": f"No results found with similarity score >= {min_similarity}",
                    "filtered_count": filtered_count,
                    "timestamp": datetime.now().isoformat()
                }

            logger.info(f"✅ Found {len(formatted_results)} STP results (filtered {filtered_count} below threshold)")

            return {
                "status": "success",
                "query": query_text,
                "total_results": len(formatted_results),
                "top_k": top_k,
                "min_similarity": min_similarity,
                "results": formatted_results,
                "filtered_count": filtered_count,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"❌ STP search failed: {e}")
            raise Exception(f"STP search failed: {str(e)}")


# Global STP service instance
stp_service = STPSearchService()


@router.get("/stp/health")
async def stp_health():
    """STP service health check"""
    try:
        is_healthy = stp_service.health_check()
        return {"status": "healthy" if is_healthy else "unhealthy"}
    except Exception:
        return {"status": "unhealthy"}


@router.post("/stp/search")
async def stp_search(request: STPSearchRequest):
    """
    Search Social Tipping Points (STP) documents

    - **text**: Search query text
    - **top_k**: Number of results to return (default: 5, max: 100)
    - **include_metadata**: Include original_content and qualifying_factors (default: true)
    - **min_similarity**: Minimum similarity score threshold (0.0 to 1.0, default: 0.0)
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Search text cannot be empty")

        if request.top_k < 1 or request.top_k > 100:
            raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")

        if request.min_similarity < 0.0 or request.min_similarity > 1.0:
            raise HTTPException(status_code=400, detail="min_similarity must be between 0.0 and 1.0")

        results = await stp_service.search(
            query_text=request.text,
            top_k=request.top_k,
            include_metadata=request.include_metadata,
            min_similarity=request.min_similarity
        )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ STP search endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RAG SEARCH SERVICES
# ============================================================================

class SearchRequest(BaseModel):
    query: str
    bucket: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=100)


def setup_search_routes(app, get_services_func):
    """Setup RAG search routes - called from main.py"""
    from api.framework import APIResponse, api_response

    @app.post("/search/chunks")
    @api_response
    async def search_chunks(request: SearchRequest):
        """Search for similar chunks using external Ollama for query embedding"""

        try:
            services = get_services_func()

            # Use query embedding service (external Ollama) for retrieval
            from services.query_embeddings import get_query_embedding_service
            query_service = get_query_embedding_service()
            embedding = await query_service.generate_embedding(request.query)

            results = await services.vector_storage.search("chunks", embedding, request.bucket, request.limit)

            return APIResponse.success({
                "query": request.query,
                "bucket_filter": request.bucket,
                "results": results,
                "count": len(results)
            })

        except Exception as e:
            APIResponse.error(f"Search failed: {str(e)}", 500)

    @app.post("/search/summaries")
    @api_response
    async def search_summaries(request: SearchRequest):
        """Search for similar summaries using external Ollama for query embedding"""

        try:
            services = get_services_func()

            # Use query embedding service (external Ollama) for retrieval
            from services.query_embeddings import get_query_embedding_service
            query_service = get_query_embedding_service()
            embedding = await query_service.generate_embedding(request.query)

            results = await services.vector_storage.search("summaries", embedding, request.bucket, request.limit)

            return APIResponse.success({
                "query": request.query,
                "bucket_filter": request.bucket,
                "results": results,
                "count": len(results)
            })

        except Exception as e:
            APIResponse.error(f"Search failed: {str(e)}", 500)

    @app.post("/search/hybrid")
    @api_response
    async def hybrid_search(query: str, bucket: Optional[str] = None,
                           chunk_limit: int = 5, summary_limit: int = 3):
        """Perform hybrid search across chunks and summaries using external Ollama"""

        try:
            services = get_services_func()

            # Use query embedding service (external Ollama) for retrieval
            from services.query_embeddings import get_query_embedding_service
            query_service = get_query_embedding_service()
            embedding = await query_service.generate_embedding(query)

            chunk_results = await services.vector_storage.search("chunks", embedding, bucket, chunk_limit)
            summary_results = await services.vector_storage.search("summaries", embedding, bucket, summary_limit)

            all_results = []

            for chunk in chunk_results:
                chunk["type"] = "chunk"
                all_results.append(chunk)

            for summary in summary_results:
                summary["type"] = "summary"
                all_results.append(summary)

            all_results.sort(key=lambda x: x["similarity_score"], reverse=True)

            return APIResponse.success({
                "query": query,
                "bucket_filter": bucket,
                "total_results": len(all_results),
                "chunks_found": len(chunk_results),
                "summaries_found": len(summary_results),
                "ranked_results": all_results
            })

        except Exception as e:
            APIResponse.error(f"Hybrid search failed: {str(e)}", 500)
