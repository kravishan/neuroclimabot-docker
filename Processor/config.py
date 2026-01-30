from dotenv import load_dotenv
import os
from typing import Dict, Any, List
from pathlib import Path
from prompts import (
    RESEARCH_PAPER_SUMMARY_PROMPT,
    POLICY_DOCUMENT_SUMMARY_PROMPT,
    SCIENTIFIC_DATA_SUMMARY_PROMPT,
    NEWS_SUMMARY_PROMPT,
    NEWS_INDIVIDUAL_ARTICLE_PROMPT,
    NEWS_COLLECTION_SUMMARY_PROMPT,
    DEFAULT_SUMMARY_PROMPT,
    GENERAL_IMAGE_DESCRIPTION_PROMPT,
    CHART_GRAPH_DESCRIPTION_PROMPT,
    DIAGRAM_ILLUSTRATION_DESCRIPTION_PROMPT,
    PHOTO_IMAGE_DESCRIPTION_PROMPT,
    TABLE_DATA_DESCRIPTION_PROMPT,
    CLIMATEGPT_SYSTEM_PROMPT,
    CLIMATEGPT_GENERATION_CONFIG
)

# Load environment variables from .env file
load_dotenv()

# GPU Detection Utility (module-level)
def _is_gpu_available() -> bool:
    """Check if CUDA GPU is available"""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False

def _get_auto_device() -> str:
    """Get automatically detected device (cuda if available, else cpu)"""
    return 'cuda' if _is_gpu_available() else 'cpu'

class Config:
    """Unified configuration management for all services with full GraphRAG and STP support"""
    
    def __init__(self):
        self._cache = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configurations once"""
        self._cache = {
            'app': self._load_app(),
            'ollama': self._load_ollama(),
            'local_embeddings': self._load_local_embeddings(),
            'minio': self._load_minio(),
            'milvus': self._load_milvus(),
            'mongodb': self._load_mongodb(),
            'lancedb': self._load_lancedb(),
            'unstructured': self._load_unstructured(),
            'processing': self._load_processing(),
            'chunking': self._load_chunking(),
            'summarization': self._load_summarization(),
            'climategpt': self._load_climategpt(),
            'graphrag': self._load_graphrag(),
            'stp': self._load_stp(),
            'vision': self._load_vision()
        }
    
    def get(self, path: str, default=None):
        """Get config value using dot notation: config.get('ollama.model')"""
        keys = path.split('.')
        value = self._cache
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    # Application Configuration
    def _load_app(self) -> Dict[str, Any]:
        return {
            'name': os.getenv('APP_NAME', 'NeuroClima Bot Document Processor'),
            'version': os.getenv('APP_VERSION', '7.0.0'),  # Updated version
            'debug': os.getenv('DEBUG', 'False').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'access_log': os.getenv('ACCESS_LOG', 'True').lower() == 'true',
            'host': os.getenv('HOST', '0.0.0.0'),
            'port': int(os.getenv('PORT', '5000')),
            'cors_origins': [
                "http://localhost:3000", 
                "http://localhost:8080", 
                "https://your-frontend-domain.com"
            ],
            'max_concurrent_tasks': int(os.getenv('MAX_CONCURRENT_TASKS', '3'))
        }
    
    # Service Configurations
    def _load_ollama(self) -> Dict[str, Any]:
        base_url = os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
        # Timeout is in MINUTES in .env, convert to seconds
        timeout_minutes = int(os.getenv('OLLAMA_TIMEOUT', '2'))
        timeout_seconds = timeout_minutes * 60
        return {
            'base_url': base_url,
            'api_url': f"{base_url}/api/generate",
            'embedding_url': f"{base_url}/api/embeddings",
            'openai_url': f"{base_url}/v1",
            'model': os.getenv('OLLAMA_MODEL', 'mistral:7b'),
            # Embedding model (Qwen3-Embedding-0.6B: 1024 dimensions)
            'embedding_model': os.getenv('OLLAMA_EMBEDDING_MODEL', 'qwen3-embedding:0.6b'),
            'embedding_dim': int(os.getenv('OLLAMA_EMBEDDING_DIM', '1024')),
            'embedding_batch_size': int(os.getenv('OLLAMA_EMBEDDING_BATCH_SIZE', '32')),
            'timeout': timeout_seconds,
            'max_retries': 3,
            'headers': {"Content-Type": "application/json"}
        }

    def _load_local_embeddings(self) -> Dict[str, Any]:
        """Configuration for local embedding models loaded at startup"""
        mode = os.getenv('PROCESSOR_EMBEDDING_MODE', 'external').lower()

        return {
            'mode': mode,  # 'local' or 'external'
            'enabled': mode == 'local',  # Only load local models if mode is 'local'
            'main_embedding': {
                'model_name': os.getenv('LOCAL_EMBEDDING_MODEL', 'Qwen/Qwen3-Embedding-0.6B'),
                'embedding_dim': int(os.getenv('LOCAL_EMBEDDING_DIM', '1024')),
                'batch_size': int(os.getenv('LOCAL_EMBEDDING_BATCH_SIZE', '32')),
                'max_seq_length': int(os.getenv('LOCAL_EMBEDDING_MAX_SEQ_LENGTH', '512')),
                'device': os.getenv('LOCAL_EMBEDDING_DEVICE', None),  # None = auto-detect
            },
            'stp_embedding': {
                'model_name': os.getenv('STP_LOCAL_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
                'embedding_dim': int(os.getenv('STP_EMBEDDING_DIM', '384')),
                'batch_size': int(os.getenv('STP_EMBEDDING_BATCH_SIZE', '32')),
                'max_seq_length': int(os.getenv('STP_EMBEDDING_MAX_SEQ_LENGTH', '256')),
                'device': os.getenv('STP_EMBEDDING_DEVICE', None),  # None = auto-detect
            }
        }

    def _load_minio(self) -> Dict[str, Any]:
        return {
            'endpoint': os.getenv('MINIO_ENDPOINT', 'localhost:9000'),
            'access_key': os.getenv('ACCESS_KEY', 'minioadmin'),
            'secret_key': os.getenv('SECRET_KEY', 'minioadmin'),
            'secure': os.getenv('SECURE', 'False').lower() == 'true',
            'processable_buckets': ["researchpapers", "policy", "news", "scientificdata"]
        }
    
    def _load_milvus(self) -> Dict[str, Any]:
        return {
            'host': os.getenv('MILVUS_HOST', 'localhost'),
            'port': int(os.getenv('MILVUS_PORT', '19530')),
            'user': os.getenv('MILVUS_USER', ''),
            'password': os.getenv('MILVUS_PASSWORD', ''),
            'chunks_database': os.getenv('MILVUS_CHUNK_DATABASE', 'chunk_test5'),
            'summaries_database': os.getenv('MILVUS_SUMMARY_DATABASE', 'summary_test5'),
            'collections': {
                'chunks': {
                    'news': 'News',
                    'scientificdata': 'Scientific_Data',
                    'policy': 'Policy',
                    'researchpapers': 'Research_Papers'
                },
                'summaries': {
                    'news': 'News',
                    'scientificdata': 'Scientific_Data',
                    'policy': 'Policy',
                    'researchpapers': 'Research_Papers'
                }
            }
        }

    def _load_mongodb(self) -> Dict[str, Any]:
        """Load MongoDB configuration for document tracking (replaces SQLite)"""
        host = os.getenv('MONGODB_HOST', 'localhost')
        port = int(os.getenv('MONGODB_PORT', '27017'))
        database = os.getenv('MONGODB_DATABASE', 'neuroclimabot')
        username = os.getenv('MONGODB_USERNAME', '')
        password = os.getenv('MONGODB_PASSWORD', '')

        # Build connection URI
        if username and password:
            # Authenticated connection (production/Kubernetes)
            connection_uri = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource=admin"
        else:
            # No authentication (local development)
            connection_uri = f"mongodb://{host}:{port}"

        return {
            'host': host,
            'port': port,
            'database': database,
            'username': username,
            'password': password,
            'connection_uri': connection_uri,
            'collections': {
                'document_status': 'document_status',
                'news_articles_status': 'news_articles_status'
            },
            # Connection pool settings for multi-replica support
            'max_pool_size': int(os.getenv('MONGODB_MAX_POOL_SIZE', '100')),
            'min_pool_size': int(os.getenv('MONGODB_MIN_POOL_SIZE', '10')),
            'server_selection_timeout_ms': int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT', '5000')),
            'connect_timeout_ms': int(os.getenv('MONGODB_CONNECT_TIMEOUT', '10000')),
        }

    def _load_lancedb(self) -> Dict[str, Any]:
        return {
            'db_path': os.getenv('LANCEDB_PATH', './lancedb_graphrag'),
            'enabled': os.getenv('ENABLE_LANCEDB_GRAPHRAG', 'True').lower() == 'true'
        }
    
    def _load_unstructured(self) -> Dict[str, Any]:
        # Timeout is in MINUTES in .env, convert to seconds
        timeout_minutes = int(os.getenv('UNSTRUCTURED_TIMEOUT', '5'))
        timeout_seconds = timeout_minutes * 60
        return {
            'api_url': os.getenv('UNSTRUCTURED_API_URL', 'http://localhost:8000'),
            'timeout': timeout_seconds,
            'max_retries': 2
        }
    
    def _load_processing(self) -> Dict[str, Any]:
        # GraphRAG timeout is in MINUTES in .env, convert to seconds
        graphrag_timeout_minutes = int(os.getenv('GRAPHRAG_TIMEOUT', '60'))
        graphrag_timeout_seconds = graphrag_timeout_minutes * 60
        return {
            'max_file_size_mb': int(os.getenv('MAX_FILE_SIZE_MB', '100')),
            'enable_graphrag': os.getenv('ENABLE_GRAPHRAG', 'True').lower() == 'true',
            'enable_rag_storage': os.getenv('ENABLE_RAG_STORAGE', 'True').lower() == 'true',
            'enable_cache': os.getenv('ENABLE_UNSTRUCTURED_CACHE', 'True').lower() == 'true',
            'graphrag_timeout': graphrag_timeout_seconds,
            'max_concurrent_tasks': int(os.getenv('MAX_CONCURRENT_TASKS', '3')),
            'enable_stp': os.getenv('ENABLE_STP', 'True').lower() == 'true'  # NEW: STP enabled flag
        }
    
    # STP Configuration from Environment Variables
    def _load_stp(self) -> Dict[str, Any]:
        """Load STP processing configuration from environment"""
        # STP timeout is in MINUTES in .env, convert to seconds
        stp_timeout_minutes = int(os.getenv('STP_TIMEOUT', '5'))
        stp_timeout_seconds = stp_timeout_minutes * 60
        return {
            # Main Configuration
            'enabled': os.getenv('ENABLE_STP', 'True').lower() == 'true',

            # STP Milvus Configuration
            'milvus_database': os.getenv('STP_MILVUS_DATABASE', 'mvp_stp_chunks_short'),
            'milvus_collection': os.getenv('STP_MILVUS_COLLECTION', 'stp_documents_test'),

            # STP Classification
            'classifier_model': os.getenv('STP_CLASSIFIER_MODEL', 'models/onnx_exports/roBERTa_stp0.5.onnx'),
            'min_confidence_threshold': float(os.getenv('STP_MIN_CONFIDENCE', '0.5')),

            # STP Text Cleaning
            'text_cleaning_enabled': os.getenv('STP_TEXT_CLEANING_ENABLED', 'True').lower() == 'true',
            'min_word_length': int(os.getenv('STP_MIN_WORD_LENGTH', '6')),

            # STP Rephrasing (80 words max)
            'rephrasing_enabled': os.getenv('STP_REPHRASING_ENABLED', 'True').lower() == 'true',
            'rephrase_max_words': int(os.getenv('STP_REPHRASE_MAX_WORDS', '80')),
            'rephrase_temperature': float(os.getenv('STP_REPHRASE_TEMPERATURE', '0.3')),
            'rephrase_max_tokens': int(os.getenv('STP_REPHRASE_MAX_TOKENS', '150')),

            # STP Qualifying Factors (5 factors)
            'qf_enabled': os.getenv('STP_QF_ENABLED', 'True').lower() == 'true',
            'qf_temperature': float(os.getenv('STP_QF_TEMPERATURE', '0.3')),
            'qf_max_tokens': int(os.getenv('STP_QF_MAX_TOKENS', '600')),

            # Chunking Configuration (from your friend's HybridChunker defaults)
            'min_chunk_tokens': int(os.getenv('STP_MIN_CHUNK_TOKENS', '200')),
            'max_chunk_tokens': int(os.getenv('STP_MAX_CHUNK_TOKENS', '1500')),
            'target_chunk_tokens': int(os.getenv('STP_TARGET_CHUNK_TOKENS', '800')),
            'boundary_threshold': float(os.getenv('STP_BOUNDARY_THRESHOLD', '0.6')),

            # Embedding Configuration
            'embedding_model': os.getenv('STP_EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
            'embedding_dim': int(os.getenv('STP_EMBEDDING_DIM', '384')),

            # Processing Options
            'batch_size': int(os.getenv('STP_BATCH_SIZE', '32')),
            'timeout': stp_timeout_seconds
        }
    
    # GraphRAG Configuration
    def _load_graphrag(self) -> Dict[str, Any]:
        # GraphRAG timeouts are in MINUTES in .env, convert to seconds
        graphrag_timeout_minutes = int(os.getenv('GRAPHRAG_TIMEOUT', '60'))
        graphrag_timeout_seconds = graphrag_timeout_minutes * 60

        llm_timeout_minutes = int(os.getenv('GRAPHRAG_LLM_TIMEOUT', '3'))
        llm_timeout_seconds = float(llm_timeout_minutes * 60)

        return {
            # Main Configuration
            'enabled': os.getenv('ENABLE_MICROSOFT_GRAPHRAG', 'True').lower() == 'true',
            'base_dir': os.getenv('GRAPHRAG_BASE_DIR', './graphrag_workspace'),
            'temp_dir': os.getenv('GRAPHRAG_TEMP_DIR', './graphrag_temp'),
            'cleanup_temp': os.getenv('GRAPHRAG_CLEANUP_TEMP', 'True').lower() == 'true',
            'auto_lancedb_transfer': os.getenv('GRAPHRAG_AUTO_LANCEDB_TRANSFER', 'True').lower() == 'true',
            'cleanup_after_transfer': os.getenv('GRAPHRAG_CLEANUP_AFTER_TRANSFER', 'True').lower() == 'true',
            'max_text_length': int(os.getenv('GRAPHRAG_MAX_TEXT_LENGTH', '50000')),
            'chunk_size': int(os.getenv('GRAPHRAG_CHUNK_SIZE', '1200')),
            'chunk_overlap': int(os.getenv('GRAPHRAG_CHUNK_OVERLAP', '100')),
            'timeout': graphrag_timeout_seconds,

            # LLM Configuration for GraphRAG
            'llm': {
                'api_key': os.getenv('GRAPHRAG_API_KEY', os.getenv('OPENAI_API_KEY', 'not-needed')),
                'type': os.getenv('GRAPHRAG_LLM_TYPE', 'openai_chat'),
                'model': os.getenv('GRAPHRAG_LLM_MODEL', 'mistral:7b'),
                'api_base': os.getenv('GRAPHRAG_LLM_API_BASE', 'http://localhost:11434/v1'),
                'temperature': float(os.getenv('GRAPHRAG_LLM_TEMPERATURE', '0.1')),
                'max_tokens': int(os.getenv('GRAPHRAG_LLM_MAX_TOKENS', '4000')),
                'request_timeout': llm_timeout_seconds
            },
            
            # Embedding Configuration for GraphRAG
            'embeddings': {
                'api_key': os.getenv('GRAPHRAG_EMBEDDING_API_KEY', os.getenv('OPENAI_API_KEY', 'not-needed')),
                'type': os.getenv('GRAPHRAG_EMBEDDING_TYPE', 'openai_embedding'),
                'model': os.getenv('GRAPHRAG_EMBEDDING_MODEL', 'nomic-embed-text:latest'),
                'api_base': os.getenv('GRAPHRAG_EMBEDDING_API_BASE', 'http://localhost:11434/v1'),
            },
            
            # Entity types for different buckets
            'entity_types': {
                'researchpapers': ['ORGANIZATION', 'PERSON', 'LOCATION', 'RESEARCH_TOPIC', 'METHODOLOGY', 'DATASET'],
                'policy': ['ORGANIZATION', 'PERSON', 'LOCATION', 'POLICY', 'REGULATION', 'LEGAL_ENTITY'],
                'scientificdata': ['ORGANIZATION', 'PERSON', 'LOCATION', 'DATASET', 'MEASUREMENT', 'VARIABLE'],
                'news': ['ORGANIZATION', 'PERSON', 'LOCATION', 'EVENT', 'TOPIC']
            },
            
            # Processing settings
            'processing': {
                'max_gleanings': int(os.getenv('GRAPHRAG_MAX_GLEANINGS', '1')),
                'max_entities': int(os.getenv('GRAPHRAG_MAX_ENTITIES', '100')),
                'max_relationships': int(os.getenv('GRAPHRAG_MAX_RELATIONSHIPS', '200')),
                'max_communities': int(os.getenv('GRAPHRAG_MAX_COMMUNITIES', '50')),
                'community_max_length': int(os.getenv('GRAPHRAG_COMMUNITY_MAX_LENGTH', '2000')),
                'enable_community_reports': os.getenv('GRAPHRAG_ENABLE_COMMUNITY_REPORTS', 'True').lower() == 'true',
                'enable_claims': os.getenv('GRAPHRAG_ENABLE_CLAIMS', 'True').lower() == 'true'
            },

            # Advanced GraphRAG Features
            'prompt_tuning': {
                'enabled': os.getenv('GRAPHRAG_ENABLE_PROMPT_TUNING', 'False').lower() == 'true',
                'input_dir': os.getenv('GRAPHRAG_PROMPT_TUNING_INPUT_DIR', './graphrag_prompt_tuning_input'),
                'output_dir': os.getenv('GRAPHRAG_PROMPT_TUNING_OUTPUT_DIR', './graphrag_prompt_tuning_output')
            },

            'claims': {
                'enabled': os.getenv('GRAPHRAG_ENABLE_CLAIMS', 'True').lower() == 'true',
                'extraction_enabled': os.getenv('GRAPHRAG_CLAIM_EXTRACTION_ENABLED', 'True').lower() == 'true',
                'max_per_chunk': int(os.getenv('GRAPHRAG_MAX_CLAIMS_PER_CHUNK', '10'))
            },

            'covariates': {
                'enabled': os.getenv('GRAPHRAG_ENABLE_COVARIATES', 'True').lower() == 'true',
                'extraction_enabled': os.getenv('GRAPHRAG_COVARIATE_EXTRACTION_ENABLED', 'True').lower() == 'true'
            },

            'text_units': {
                'enabled': os.getenv('GRAPHRAG_ENABLE_TEXT_UNITS', 'True').lower() == 'true',
                'size': int(os.getenv('GRAPHRAG_TEXT_UNIT_SIZE', '300')),
                'overlap': int(os.getenv('GRAPHRAG_TEXT_UNIT_OVERLAP', '100'))
            },

            'embeddings': {
                'entity_embeddings_enabled': os.getenv('GRAPHRAG_ENABLE_ENTITY_EMBEDDINGS', 'True').lower() == 'true',
                'relationship_embeddings_enabled': os.getenv('GRAPHRAG_ENABLE_RELATIONSHIP_EMBEDDINGS', 'False').lower() == 'true'
            },

            'vector_search': {
                'enabled': os.getenv('GRAPHRAG_VECTOR_SEARCH_ENABLED', 'True').lower() == 'true',
                'similarity_threshold': float(os.getenv('GRAPHRAG_VECTOR_SIMILARITY_THRESHOLD', '0.7')),
                'top_k': int(os.getenv('GRAPHRAG_VECTOR_TOP_K', '20'))
            },

            'community_detection': {
                'algorithm': os.getenv('GRAPHRAG_COMMUNITY_ALGORITHM', 'leiden'),
                'max_level': int(os.getenv('GRAPHRAG_COMMUNITY_MAX_LEVEL', '3')),
                'hierarchical_enabled': os.getenv('GRAPHRAG_ENABLE_HIERARCHICAL_COMMUNITIES', 'True').lower() == 'true'
            }
        }
    
    # Processing Configurations
    def _load_chunking(self) -> Dict[str, Any]:
        return {
            'researchpapers': {
                'chunk_size': 512,
                'overlap_ratio': 0.15,
                'separators': ["\n\n", "\n", ".", " ", ""],
                'section_sizes': {
                    'abstract': 300,
                    'methodology': 600,
                    'results': 450
                },
                'technical_overlap': 0.15,
                'literature_overlap': 0.20,
                'default_chunk_size': 512,
                'abstract_chunk_size': 300,
                'methodology_chunk_size': 600,
                'results_chunk_size': 450,
                'discussion_chunk_size': 672
            },
            'policy': {
                'chunk_size': 672,
                'overlap_ratio': 0.125,
                'separators': ["\n\n\n", "\n\n", "\n", ". ", " ", ""],
                'min_chunk_size': 100,
                'max_chunk_size': 1000,
                'hierarchical_processing': True,
                'preserve_legal_structure': True
            },
            'scientificdata': {
                'chunk_size': 800,
                'overlap_ratio': 0.10,
                'separators': ["\n\n\n", "\n\n", "\n", " | ", ", ", " ", ""],
                'max_chunk_size': 950,
                'small_chunk_target': 800,
                'table_split_threshold': 800,
                'aggressive_splitting': True
            },
            'news': {
                'chunk_size': 600,
                'overlap_ratio': 0.15,
                'separators': ["\n\n\n", "\n\n", "\n", ". ", "! ", "? ", " ", ""],
                'article_aware': True,
                'preserve_article_structure': True,
                'excel_article_chunk_size': 500,
                'excel_article_overlap': 0.20
            },
            'default': {
                'chunk_size': 600,
                'overlap_ratio': 0.15,
                'separators': ["\n\n", "\n", ". ", " ", ""]
            }
        }
    
    def _load_summarization(self) -> Dict[str, Any]:
        # Base parameters for all summarization
        base_params = {
            'temperature': 0.3,
            'top_p': 0.9,
            'max_tokens': 400,  # ~300 words for 1-2 paragraphs
            'stream': False,
            'timeout': 90
        }

        return {
            'common': base_params,
            'researchpapers': {
                **base_params,
                'target_length': '200-300 words',
                'template': RESEARCH_PAPER_SUMMARY_PROMPT,
                'focus_areas': ['problem', 'methodology', 'findings', 'significance'],
                'style': 'scholarly'
            },
            'policy': {
                **base_params,
                'target_length': '200-300 words',
                'template': POLICY_DOCUMENT_SUMMARY_PROMPT,
                'focus_areas': ['problem', 'objectives', 'provisions', 'impact'],
                'style': 'professional'
            },
            'scientificdata': {
                **base_params,
                'target_length': '200-300 words',
                'template': SCIENTIFIC_DATA_SUMMARY_PROMPT,
                'focus_areas': ['context', 'data', 'methods', 'applications'],
                'style': 'scientific'
            },
            'news': {
                **base_params,
                'target_length': '200-300 words',
                'template': NEWS_SUMMARY_PROMPT,
                'individual_article_template': NEWS_INDIVIDUAL_ARTICLE_PROMPT,
                'collection_template': NEWS_COLLECTION_SUMMARY_PROMPT,
                'focus_areas': ['events', 'context', 'impact', 'significance'],
                'style': 'journalistic'
            },
            'default': {
                **base_params,
                'target_length': '200-300 words',
                'template': DEFAULT_SUMMARY_PROMPT,
                'style': 'general'
            }
        }

    # Vision/Image Processing Configuration
    def _load_vision(self) -> Dict[str, Any]:
        """Load vision and image processing configuration"""
        return {
            # Vision Model Configuration
            'enabled': os.getenv('ENABLE_IMAGE_EXTRACTION', 'True').lower() == 'true',
            'provider': os.getenv('VISION_MODEL_PROVIDER', 'ollama'),  # 'ollama' or 'openai'
            'ollama_model': os.getenv('OLLAMA_VISION_MODEL', 'llava:13b'),
            'openai_model': os.getenv('OPENAI_VISION_MODEL', 'gpt-4-vision-preview'),

            # Image Extraction Settings
            'extract_from_pdf': os.getenv('EXTRACT_IMAGES_FROM_PDF', 'True').lower() == 'true',
            'extract_from_docx': os.getenv('EXTRACT_IMAGES_FROM_DOCX', 'True').lower() == 'true',
            'min_width': int(os.getenv('IMAGE_MIN_WIDTH', '100')),
            'min_height': int(os.getenv('IMAGE_MIN_HEIGHT', '100')),
            'max_size_mb': int(os.getenv('IMAGE_MAX_SIZE_MB', '10')),

            # Image Processing
            'resize_for_vision': os.getenv('RESIZE_IMAGES_FOR_VISION', 'True').lower() == 'true',
            'max_dimension': int(os.getenv('MAX_IMAGE_DIMENSION', '1024')),
            'replace_with_descriptions': os.getenv('REPLACE_IMAGES_WITH_DESCRIPTIONS', 'True').lower() == 'true',

            # Image Description Prompts (imported from prompts.py)
            'description_prompt': GENERAL_IMAGE_DESCRIPTION_PROMPT,
            'chart_graph_prompt': CHART_GRAPH_DESCRIPTION_PROMPT,
            'diagram_illustration_prompt': DIAGRAM_ILLUSTRATION_DESCRIPTION_PROMPT,
            'photo_image_prompt': PHOTO_IMAGE_DESCRIPTION_PROMPT,
            'table_data_prompt': TABLE_DATA_DESCRIPTION_PROMPT
        }

    # ClimateGPT-7B Configuration
    def _load_climategpt(self) -> Dict[str, Any]:
        """Load ClimateGPT-7B model configuration for summarization"""
        # Auto-detect device if not specified, otherwise use env variable
        device_env = os.getenv('CLIMATEGPT_DEVICE', '').lower()
        if device_env == 'auto' or device_env == '':
            device = _get_auto_device()
        else:
            device = device_env

        return {
            'enabled': os.getenv('USE_CLIMATEGPT', 'False').lower() == 'true',
            'model_name': 'eci-io/climategpt-7b',
            'model_url': 'https://huggingface.co/eci-io/climategpt-7b',
            'system_prompt': CLIMATEGPT_SYSTEM_PROMPT,
            'generation_config': CLIMATEGPT_GENERATION_CONFIG,
            'use_for_summaries': True,
            'device': device,  # Auto-detected or from env
            'load_in_8bit': os.getenv('CLIMATEGPT_8BIT', 'False').lower() == 'true',
            'load_in_4bit': os.getenv('CLIMATEGPT_4BIT', 'False').lower() == 'true'
        }

    # Utility Methods
    def get_chunking_config(self, bucket: str) -> Dict[str, Any]:
        """Get chunking configuration for bucket"""
        return self.get(f'chunking.{bucket}', self.get('chunking.default'))

    def get_summarization_config(self, bucket: str) -> Dict[str, Any]:
        """Get summarization configuration for bucket"""
        return self.get(f'summarization.{bucket}', self.get('summarization.default'))

    def get_mongodb_config(self) -> Dict[str, Any]:
        """Get MongoDB configuration for document tracking"""
        return self.get('mongodb', {})

    def get_graphrag_config(self) -> Dict[str, Any]:
        """Get Microsoft GraphRAG configuration"""
        return self.get('graphrag', {})

    def get_graphrag_limits(self) -> Dict[str, Any]:
        """Get GraphRAG API limits configuration"""
        return {
            # Local search limits
            'max_entities': self.get('graphrag.max_entities', 999999),  # Unlimited by default
            'max_relationships': self.get('graphrag.max_relationships', 999999),  # Unlimited by default
            'max_communities': self.get('graphrag.max_communities', 999999),  # Unlimited by default
            'context_depth': self.get('graphrag.context_depth', 2),
            'min_relevance_score': self.get('graphrag.min_relevance_score', 0.1),

            # Visualization limits
            'max_viz_nodes': self.get('graphrag.max_viz_nodes', 999999),  # Unlimited by default
            'max_viz_edges': self.get('graphrag.max_viz_edges', 999999),  # Unlimited by default
        }

    def get_climategpt_config(self) -> Dict[str, Any]:
        """Get ClimateGPT-7B configuration"""
        return self.get('climategpt', {})

    # NEW: STP Utility Methods
    def get_stp_config(self) -> Dict[str, Any]:
        """Get STP processing configuration"""
        return self.get('stp', {})

    def is_stp_enabled(self) -> bool:
        """Check if STP processing is enabled"""
        return self.get('stp.enabled', True) and self.get('processing.enable_stp', True)

    def get_stp_milvus_config(self) -> Dict[str, Any]:
        """Get STP Milvus configuration"""
        return {
            'database': self.get('stp.milvus_database', 'mvp_stp_chunks_short'),
            'collection': self.get('stp.milvus_collection', 'stp_documents_test'),
            'embedding_dim': self.get('stp.embedding_dim', 384)
        }

    # Vision/Image Processing Utility Methods
    def get_vision_config(self) -> Dict[str, Any]:
        """Get vision/image processing configuration"""
        return self.get('vision', {})

    def is_vision_enabled(self) -> bool:
        """Check if vision/image processing is enabled"""
        return self.get('vision.enabled', True)

    def get_vision_prompt(self, image_type: str = 'default') -> str:
        """
        Get vision description prompt for specific image type

        Args:
            image_type: Type of image ('default', 'chart', 'diagram', 'photo', 'table')

        Returns:
            Appropriate prompt template for the image type
        """
        prompt_mapping = {
            'default': 'description_prompt',
            'chart': 'chart_graph_prompt',
            'graph': 'chart_graph_prompt',
            'diagram': 'diagram_illustration_prompt',
            'illustration': 'diagram_illustration_prompt',
            'photo': 'photo_image_prompt',
            'image': 'photo_image_prompt',
            'table': 'table_data_prompt'
        }

        prompt_key = prompt_mapping.get(image_type.lower(), 'description_prompt')
        return self.get(f'vision.{prompt_key}', self.get('vision.description_prompt', ''))

    def get_stp_classifier_config(self) -> Dict[str, Any]:
        """Get STP classifier configuration"""
        return {
            'model_path': self.get('stp.classifier_model', 'models/onnx_exports/roBERTa_stp0.5.onnx'),
            'min_confidence': self.get('stp.min_confidence_threshold', 0.5)
        }

    def get_stp_rephrasing_config(self) -> Dict[str, Any]:
        """Get STP rephrasing configuration"""
        return {
            'enabled': self.get('stp.rephrasing_enabled', True),
            'max_words': self.get('stp.rephrase_max_words', 80),
            'temperature': self.get('stp.rephrase_temperature', 0.3),
            'max_tokens': self.get('stp.rephrase_max_tokens', 150)
        }

    def get_stp_qf_config(self) -> Dict[str, Any]:
        """Get STP qualifying factors configuration"""
        return {
            'enabled': self.get('stp.qf_enabled', True),
            'temperature': self.get('stp.qf_temperature', 0.3),
            'max_tokens': self.get('stp.qf_max_tokens', 600)
        }

    def get_stp_chunking_config(self) -> Dict[str, Any]:
        """Get STP chunking configuration"""
        return {
            'min_chunk_tokens': self.get('stp.min_chunk_tokens', 200),
            'max_chunk_tokens': self.get('stp.max_chunk_tokens', 1500),
            'target_chunk_tokens': self.get('stp.target_chunk_tokens', 800),
            'boundary_threshold': self.get('stp.boundary_threshold', 0.6)
        }

    def get_graphrag_entity_types(self, bucket: str) -> List[str]:
        """Get entity types for GraphRAG processing by bucket"""
        return self.get(f'graphrag.entity_types.{bucket}', ['ORGANIZATION', 'PERSON', 'LOCATION'])

    def get_ollama_payload(self, prompt: str, bucket: str = 'default') -> Dict[str, Any]:
        """Build Ollama API payload"""
        config_data = self.get_summarization_config(bucket)
        return {
            'model': self.get('ollama.model'),
            'prompt': prompt,
            'stream': config_data['stream'],
            'options': {
                'temperature': config_data['temperature'],
                'top_p': config_data['top_p'],
                'max_tokens': config_data['max_tokens']
            }
        }

    def get_news_summarization_template(self, template_type: str = 'default') -> str:
        """Get news-specific summarization template"""
        news_config = self.get('summarization.news', {})

        if template_type == 'individual_article':
            return news_config.get('individual_article_template', news_config.get('template', ''))
        elif template_type == 'collection':
            return news_config.get('collection_template', news_config.get('template', ''))
        else:
            return news_config.get('template', '')

    def create_news_prompt(self, content: str, article_title: str = "", source_info: str = "",
                          article_link: str = "", template_type: str = 'individual_article') -> str:
        """Create news-specific prompt for summarization"""
        template = self.get_news_summarization_template(template_type)

        if template_type == 'individual_article':
            return template.format(
                title=article_title,
                source_info=source_info,
                content=content
            )
        else:
            return template.format(content=content)

    def is_bucket_processable(self, bucket: str) -> bool:
        """Check if bucket is processable"""
        return bucket in self.get('minio.processable_buckets', [])

    def get_bucket_chunker_class(self, bucket: str) -> str:
        """Get chunker class name for bucket"""
        chunker_mapping = {
            'researchpapers': 'ResearchPaperChunker',
            'policy': 'PolicyDocumentChunker',
            'scientificdata': 'ScientificDataChunker',
            'news': 'NewsArticleChunker'
        }
        return chunker_mapping.get(bucket, 'NewsArticleChunker')

    def get_bucket_summarizer_class(self, bucket: str) -> str:
        """Get summarizer class name for bucket"""
        summarizer_mapping = {
            'researchpapers': 'ResearchPaperSummarizer',
            'policy': 'PolicyDocumentSummarizer',
            'scientificdata': 'ScientificDataSummarizer',
            'news': 'NewsArticleSummarizer'
        }
        return summarizer_mapping.get(bucket, 'NewsArticleSummarizer')

    def get_processing_enabled_defaults(self) -> Dict[str, bool]:
        """Get default processing options"""
        return {
            'include_chunking': True,
            'include_summarization': True,
            'include_graphrag': self.get('processing.enable_graphrag', True) and self.get('graphrag.enabled', True),
            'include_stp': self.is_stp_enabled()  # NEW: STP default
        }

    def get_file_type_extensions(self) -> List[str]:
        """Get supported file extensions"""
        return ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.csv', '.txt']

    def get_cache_settings(self) -> Dict[str, Any]:
        """Get caching configuration"""
        return {
            'enable_cache': self.get('processing.enable_cache', True),
            'cache_dir': './cache',
            'extraction_cache_dir': './cache/extractions',
            'max_cache_size_gb': 5
        }

    # GPU Detection Utility
    def is_gpu_available(self) -> bool:
        """Check if CUDA GPU is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def get_device(self, prefer_gpu: bool = True) -> str:
        """
        Get the appropriate device (cuda or cpu)

        Args:
            prefer_gpu: If True, use GPU when available

        Returns:
            'cuda' if GPU is available and preferred, else 'cpu'
        """
        if prefer_gpu and self.is_gpu_available():
            return 'cuda'
        return 'cpu'

    # STP Validation Methods
    def validate_stp_config(self) -> Dict[str, Any]:
        """
        Validate STP configuration

        Returns:
            Dictionary with validation results including 'valid', 'errors', 'warnings' keys
        """
        errors = []
        warnings = []

        # Check if STP is enabled
        if not self.is_stp_enabled():
            warnings.append("STP processing is disabled")

        # Check Milvus configuration
        milvus_config = self.get_stp_milvus_config()
        if not milvus_config.get('database'):
            errors.append("STP Milvus database not configured")
        if not milvus_config.get('collection'):
            errors.append("STP Milvus collection not configured")

        # Check classifier model path
        classifier_config = self.get_stp_classifier_config()
        model_path = classifier_config.get('model_path')
        if model_path:
            from pathlib import Path
            if not Path(model_path).exists():
                warnings.append(f"STP classifier model not found at {model_path}")
        else:
            errors.append("STP classifier model path not configured")

        # Check Ollama configuration (STP uses main Ollama config)
        ollama_config = self.get('ollama', {})
        if not ollama_config.get('embedding_url'):
            warnings.append("Ollama embedding URL not configured (used by STP)")
        if not ollama_config.get('api_url'):
            warnings.append("Ollama API URL not configured (used by STP)")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def check_stp_dependencies(self) -> Dict[str, Any]:
        """
        Check STP dependencies availability

        Returns:
            Dictionary with dependency status including 'dependencies', 'all_available',
            'missing', 'critical_missing' keys
        """
        dependencies = {
            'torch': {'available': False, 'critical': True},
            'transformers': {'available': False, 'critical': True},
            'onnxruntime': {'available': False, 'critical': True},
            'pymilvus': {'available': False, 'critical': True},
            'sentence_transformers': {'available': False, 'critical': False}
        }

        # Check each dependency
        for dep_name in dependencies.keys():
            try:
                __import__(dep_name)
                dependencies[dep_name]['available'] = True
            except ImportError:
                dependencies[dep_name]['available'] = False

        # Determine missing dependencies
        missing = [name for name, info in dependencies.items() if not info['available']]
        critical_missing = [name for name, info in dependencies.items()
                          if not info['available'] and info['critical']]
        all_available = len(missing) == 0

        return {
            'dependencies': dependencies,
            'all_available': all_available,
            'missing': missing,
            'critical_missing': critical_missing
        }

    def get_stp_environment_info(self) -> Dict[str, Any]:
        """
        Get STP environment information

        Returns:
            Dictionary with environment details including GPU availability
        """
        import sys
        import platform

        env_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'gpu_available': self.is_gpu_available(),
            'device': self.get_device(prefer_gpu=True)
        }

        # Add GPU details if available
        if self.is_gpu_available():
            try:
                import torch
                env_info['gpu_count'] = torch.cuda.device_count()
                env_info['gpu_name'] = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else None
                env_info['cuda_version'] = torch.version.cuda
            except Exception as e:
                env_info['gpu_error'] = str(e)

        return env_info

    def reload(self):
        """Reload configuration from environment"""
        load_dotenv()
        self._load_all_configs()


# Global configuration instance
config = Config()
