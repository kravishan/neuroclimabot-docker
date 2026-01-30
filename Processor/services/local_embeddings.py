"""
Local Embedding Service for Processor
Loads embedding models locally at startup for fast batch processing
Supports both sentence-transformers and native transformers models
"""

import logging
from typing import List, Dict, Any, Optional
import torch
import numpy as np

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """
    Local embedding service that loads models at startup.
    Supports sentence-transformers models and native transformers models (like Qwen3).
    """

    def __init__(
        self,
        model_name: str,
        embedding_dim: int,
        batch_size: int = 32,
        max_seq_length: Optional[int] = None,
        device: Optional[str] = None,
        use_sentence_transformers: Optional[bool] = None
    ):
        """
        Initialize local embedding service.

        Args:
            model_name: HuggingFace model name (e.g., 'Qwen/Qwen3-Embedding-0.6B')
            embedding_dim: Expected embedding dimension
            batch_size: Batch size for encoding
            max_seq_length: Maximum sequence length (None = use model default)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
            use_sentence_transformers: Force sentence-transformers (True) or transformers (False), None=auto-detect
        """
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.batch_size = batch_size
        self.max_seq_length = max_seq_length or 512
        self.model = None
        self.tokenizer = None
        self.device = device or self._get_device()

        # Auto-detect model type if not specified
        if use_sentence_transformers is None:
            # Models known to NOT work with sentence-transformers
            use_sentence_transformers = not any(x in model_name.lower() for x in ['qwen', 'qwen2', 'qwen3'])

        self.use_sentence_transformers = use_sentence_transformers

        logger.info(f"🔧 Initializing LocalEmbeddingService with {model_name}")
        logger.info(f"   Using: {'sentence-transformers' if use_sentence_transformers else 'transformers (native)'}")

    def _get_device(self) -> str:
        """Detect available device (GPU or CPU)"""
        if torch.cuda.is_available():
            return 'cuda'
        else:
            return 'cpu'

    def load_model(self):
        """Load the embedding model into memory"""
        if self.model is not None:
            logger.info(f"✅ Model {self.model_name} already loaded")
            return

        logger.info(f"📥 Loading embedding model: {self.model_name}...")
        logger.info(f"🎯 Target device: {self.device}")

        try:
            if self.use_sentence_transformers:
                # Use sentence-transformers for compatible models
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(self.model_name)
                self.model.max_seq_length = self.max_seq_length

                if self.device == 'cuda':
                    self.model = self.model.to('cuda')
                    logger.info(f"🚀 Model loaded on GPU (CUDA)")
                    logger.info(f"💾 GPU Memory allocated: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")
                else:
                    logger.info(f"💻 Model loaded on CPU")

                # Get actual embedding dimension
                actual_dim = self.model.get_sentence_embedding_dimension()
                if actual_dim != self.embedding_dim:
                    logger.warning(
                        f"⚠️  Model dimension ({actual_dim}) differs from configured dimension ({self.embedding_dim})"
                    )
                    self.embedding_dim = actual_dim

            else:
                # Use native transformers for models like Qwen3
                from transformers import AutoTokenizer, AutoModel

                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
                self.model = AutoModel.from_pretrained(self.model_name, trust_remote_code=True)

                # Move to device
                self.model = self.model.to(self.device)
                self.model.eval()  # Set to evaluation mode

                if self.device == 'cuda':
                    logger.info(f"🚀 Model loaded on GPU (CUDA)")
                    logger.info(f"💾 GPU Memory allocated: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")
                else:
                    logger.info(f"💻 Model loaded on CPU")

            logger.info(f"✅ Model loaded successfully: {self.model_name} ({self.embedding_dim}D)")

        except Exception as e:
            logger.error(f"❌ Failed to load embedding model {self.model_name}: {e}")
            raise

    def _mean_pooling(self, model_output, attention_mask):
        """Mean pooling for transformers models"""
        token_embeddings = model_output[0]  # First element contains token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def encode(self, texts: List[str], show_progress: bool = False) -> List[List[float]]:
        """
        Encode texts into embeddings using batch processing.

        Args:
            texts: List of texts to encode
            show_progress: Whether to show progress bar

        Returns:
            List of embeddings (each embedding is a list of floats)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        if not texts:
            return []

        # Remove empty texts and keep track of original indices
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text.strip())
                valid_indices.append(i)

        if not valid_texts:
            logger.warning("No valid texts to encode")
            return [[0.0] * self.embedding_dim] * len(texts)

        try:
            logger.debug(f"🔄 Encoding {len(valid_texts)} texts in batches of {self.batch_size}")

            if self.use_sentence_transformers:
                # Use sentence-transformers encode method
                embeddings = self.model.encode(
                    valid_texts,
                    batch_size=self.batch_size,
                    show_progress_bar=show_progress,
                    convert_to_tensor=True,
                    normalize_embeddings=False
                )

                # Convert to list
                if isinstance(embeddings, torch.Tensor):
                    embeddings = embeddings.cpu().numpy()
                embeddings_list = embeddings.tolist()

            else:
                # Use native transformers with manual encoding
                embeddings_list = []

                for i in range(0, len(valid_texts), self.batch_size):
                    batch_texts = valid_texts[i:i + self.batch_size]

                    # Tokenize
                    encoded = self.tokenizer(
                        batch_texts,
                        padding=True,
                        truncation=True,
                        max_length=self.max_seq_length,
                        return_tensors='pt'
                    )

                    # Move to device
                    encoded = {k: v.to(self.device) for k, v in encoded.items()}

                    # Generate embeddings
                    with torch.no_grad():
                        model_output = self.model(**encoded)
                        # Use mean pooling
                        batch_embeddings = self._mean_pooling(model_output, encoded['attention_mask'])

                    # Convert to list
                    batch_embeddings = batch_embeddings.cpu().numpy().tolist()
                    embeddings_list.extend(batch_embeddings)

            # Create result array with zero embeddings for invalid texts
            result = [[0.0] * self.embedding_dim] * len(texts)
            for valid_idx, original_idx in enumerate(valid_indices):
                result[original_idx] = embeddings_list[valid_idx]

            return result

        except Exception as e:
            logger.error(f"❌ Encoding failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return zero embeddings as fallback
            return [[0.0] * self.embedding_dim] * len(texts)

    def encode_single(self, text: str) -> List[float]:
        """
        Encode a single text into an embedding.

        Args:
            text: Text to encode

        Returns:
            Embedding as a list of floats
        """
        if not text or not text.strip():
            return [0.0] * self.embedding_dim

        result = self.encode([text], show_progress=False)
        return result[0]

    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension"""
        return self.embedding_dim

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model"""
        if self.model is None:
            return {"loaded": False}

        return {
            "loaded": True,
            "model_name": self.model_name,
            "model_type": "sentence-transformers" if self.use_sentence_transformers else "transformers (native)",
            "embedding_dim": self.embedding_dim,
            "device": self.device,
            "batch_size": self.batch_size,
            "max_seq_length": self.max_seq_length,
        }

    def unload_model(self):
        """Unload model from memory"""
        if self.model is not None:
            logger.info(f"🔄 Unloading model {self.model_name}")
            del self.model
            self.model = None
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
        if self.device == 'cuda':
            torch.cuda.empty_cache()
            logger.info("🧹 CUDA cache cleared")


class EmbeddingModelManager:
    """
    Manages multiple embedding models for different purposes.
    Loads models at startup and provides unified interface.
    """

    def __init__(self):
        self.models: Dict[str, LocalEmbeddingService] = {}
        logger.info("🔧 Initializing EmbeddingModelManager")

    def register_model(
        self,
        name: str,
        model_name: str,
        embedding_dim: int,
        batch_size: int = 32,
        max_seq_length: Optional[int] = None,
        device: Optional[str] = None,
        load_immediately: bool = True
    ):
        """
        Register a new embedding model.

        Args:
            name: Internal name for the model (e.g., 'main', 'stp')
            model_name: HuggingFace model name
            embedding_dim: Expected embedding dimension
            batch_size: Batch size for encoding
            max_seq_length: Maximum sequence length
            device: Device to use
            load_immediately: Whether to load the model immediately
        """
        logger.info(f"📝 Registering model '{name}': {model_name}")

        service = LocalEmbeddingService(
            model_name=model_name,
            embedding_dim=embedding_dim,
            batch_size=batch_size,
            max_seq_length=max_seq_length,
            device=device
        )

        self.models[name] = service

        if load_immediately:
            service.load_model()

    def get_model(self, name: str) -> LocalEmbeddingService:
        """Get a registered model by name"""
        if name not in self.models:
            raise ValueError(f"Model '{name}' not registered. Available: {list(self.models.keys())}")
        return self.models[name]

    def encode(self, name: str, texts: List[str], show_progress: bool = False) -> List[List[float]]:
        """Encode texts using a specific model"""
        model = self.get_model(name)
        return model.encode(texts, show_progress=show_progress)

    def encode_single(self, name: str, text: str) -> List[float]:
        """Encode a single text using a specific model"""
        model = self.get_model(name)
        return model.encode_single(text)

    def get_all_models_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered models"""
        return {name: model.get_model_info() for name, model in self.models.items()}

    def unload_all_models(self):
        """Unload all models from memory"""
        logger.info("🔄 Unloading all models")
        for model in self.models.values():
            model.unload_model()


# Global model manager instance
_model_manager: Optional[EmbeddingModelManager] = None


def get_model_manager() -> EmbeddingModelManager:
    """Get or create the global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = EmbeddingModelManager()
    return _model_manager


def initialize_embedding_models(config: Dict[str, Any]):
    """
    Initialize all embedding models at startup.

    Args:
        config: Configuration dictionary containing model settings
    """
    manager = get_model_manager()

    # Load main document embedding model (Qwen3-Embedding-0.6B)
    if 'main_embedding' in config:
        main_config = config['main_embedding']
        manager.register_model(
            name='main',
            model_name=main_config['model_name'],
            embedding_dim=main_config['embedding_dim'],
            batch_size=main_config.get('batch_size', 32),
            max_seq_length=main_config.get('max_seq_length'),
            device=main_config.get('device'),
            load_immediately=True
        )

    # Load STP embedding model (all-MiniLM-L6-v2) if enabled
    if 'stp_embedding' in config:
        stp_config = config['stp_embedding']
        manager.register_model(
            name='stp',
            model_name=stp_config['model_name'],
            embedding_dim=stp_config['embedding_dim'],
            batch_size=stp_config.get('batch_size', 32),
            max_seq_length=stp_config.get('max_seq_length'),
            device=stp_config.get('device'),
            load_immediately=True
        )

    logger.info("✅ All embedding models initialized successfully")
