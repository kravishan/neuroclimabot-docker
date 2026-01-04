import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import List, Tuple, Dict, Optional
from tqdm import tqdm
import os

# ONNX and ML libraries
import onnxruntime as ort
from transformers import AutoTokenizer

class RoBERTaONNXClassifier:
    def __init__(self, onnx_model_path: str = None, tokenizer_path: str = None, models_folder: str = None):
        """
        Initialize RoBERTa/DeBERTa ONNX classifier.
        
        Args:
            onnx_model_path: Path to a specific ONNX model (optional if models_folder is provided)
            tokenizer_path: Path to the tokenizer directory (optional, auto-detected)
            models_folder: Path to folder containing ONNX models for selection (optional)
        """
        self.tokenizer_path = tokenizer_path
        self.models_folder = models_folder
        self.available_models = []
        self.current_model_name = None
        self.model_type = None  # Will be auto-detected
        
        # If models_folder is provided, discover available models
        if models_folder:
            self.available_models = self._discover_onnx_models(models_folder)
            if not onnx_model_path and self.available_models:
                # Use the first available model as default
                onnx_model_path = self.available_models[0]['path']
                print(f"Auto-selected first available model: {self.available_models[0]['name']}")
        
        if not onnx_model_path:
            raise ValueError("Either onnx_model_path or models_folder with available models must be provided")
            
        self.onnx_model_path = onnx_model_path
        self.current_model_name = Path(onnx_model_path).stem
        
        # Auto-detect model type from filename
        self.model_type = self._detect_model_type(self.current_model_name)
        
        # Load components
        self._load_components()
        
        print(f"✓ RoBERTa ONNX Classifier initialized")
        print(f"  ONNX model: {onnx_model_path}")
        print(f"  Current model: {self.current_model_name}")
        print(f"  Model type: {self.model_type}")
        print(f"  Tokenizer: {self.tokenizer_path}")
        if self.available_models:
            print(f"  Available models: {len(self.available_models)}")
    
    def _detect_model_type(self, model_name: str) -> str:
        """Auto-detect if this is RoBERTa or DeBERTa model from filename."""
        model_name_lower = model_name.lower()
        if 'deberta' in model_name_lower or 'deb' in model_name_lower:
            return 'deberta'
        else:
            return 'roberta'  # Default to roberta
    
    def _discover_onnx_models(self, models_folder: str) -> List[Dict]:
        """
        Discover ONNX models in the specified folder.
        
        Args:
            models_folder: Path to folder containing ONNX models
            
        Returns:
            List of dictionaries with model information
        """
        models_path = Path(models_folder)
        if not models_path.exists():
            print(f"Warning: Models folder not found: {models_folder}")
            return []
        
        models = []
        for file_path in models_path.glob("*.onnx"):
            model_type = self._detect_model_type(file_path.stem)
            model_info = {
                'name': file_path.stem,
                'filename': file_path.name,
                'path': str(file_path),
                'type': model_type,
                'size_mb': file_path.stat().st_size / (1024 * 1024)
            }
            models.append(model_info)
        
        models.sort(key=lambda x: x['name'])  # Sort alphabetically
        print(f"Found {len(models)} ONNX models in {models_folder}")
        return models
    
    def list_available_models(self) -> None:
        """Display all available ONNX models."""
        if not self.available_models:
            print("No models folder specified or no models found.")
            print(f"Current model: {self.current_model_name} ({self.model_type})")
            return
        
        print(f"\nAvailable ONNX Models ({len(self.available_models)}):")
        print("-" * 60)
        for i, model in enumerate(self.available_models):
            current_marker = " (CURRENT)" if model['name'] == self.current_model_name else ""
            print(f"{i+1:2d}. {model['name']}{current_marker}")
            print(f"     Type: {model['type']}")
            print(f"     File: {model['filename']}")
            print(f"     Size: {model['size_mb']:.1f} MB")
            print()
    
    def select_model_by_index(self, index: int) -> bool:
        """
        Select and load a model by its index in the available models list.
        
        Args:
            index: 1-based index of the model to select
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available_models:
            print("No models available for selection.")
            return False
        
        if index < 1 or index > len(self.available_models):
            print(f"Invalid index. Please choose between 1 and {len(self.available_models)}")
            return False
        
        selected_model = self.available_models[index - 1]
        return self._switch_model(selected_model['path'], selected_model['name'])
    
    def select_model_by_name(self, model_name: str) -> bool:
        """
        Select and load a model by its name.
        
        Args:
            model_name: Name of the model to select (partial matching supported)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.available_models:
            print("No models available for selection.")
            return False
        
        # Find matching models (case-insensitive partial match)
        matches = [m for m in self.available_models if model_name.lower() in m['name'].lower()]
        
        if not matches:
            print(f"No models found matching '{model_name}'")
            print("Available models:")
            for model in self.available_models:
                print(f"  - {model['name']} ({model['type']})")
            return False
        
        if len(matches) > 1:
            print(f"Multiple models match '{model_name}':")
            for i, model in enumerate(matches):
                print(f"  {i+1}. {model['name']} ({model['type']})")
            print("Please be more specific.")
            return False
        
        selected_model = matches[0]
        return self._switch_model(selected_model['path'], selected_model['name'])
    
    def _switch_model(self, model_path: str, model_name: str) -> bool:
        """
        Switch to a different ONNX model.
        
        Args:
            model_path: Path to the new model
            model_name: Name of the new model
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"Switching from '{self.current_model_name}' to '{model_name}'...")
            old_path = self.onnx_model_path
            old_name = self.current_model_name
            old_type = self.model_type
            
            # Update paths
            self.onnx_model_path = model_path
            self.current_model_name = model_name
            self.model_type = self._detect_model_type(model_name)
            
            # Reload components
            self._load_components()
            
            print(f"✓ Successfully switched to model: {model_name}")
            print(f"  Type: {self.model_type}")
            print(f"  Path: {model_path}")
            return True
            
        except Exception as e:
            # Restore previous model on failure
            self.onnx_model_path = old_path
            self.current_model_name = old_name
            self.model_type = old_type
            print(f"✗ Error switching model: {e}")
            print(f"  Restored previous model: {self.current_model_name}")
            return False
    
    def _load_components(self):
        """Load ONNX model and tokenizer."""
        print(f"Loading {self.model_type.upper()} ONNX model components...")
        
        # Load ONNX session
        self.ort_session = ort.InferenceSession(str(self.onnx_model_path))
        print(f"✓ ONNX model loaded: {self.onnx_model_path}")
        
        # Load appropriate tokenizer based on model type
        try:
            # Try to load from local tokenizer directory if it exists
            tokenizer_dir = Path(self.onnx_model_path).parent / "tokenizer"
            if tokenizer_dir.exists():
                self.tokenizer = AutoTokenizer.from_pretrained(str(tokenizer_dir))
                self.tokenizer_path = str(tokenizer_dir)
                print(f"✓ Local tokenizer loaded: {tokenizer_dir}")
            elif self.tokenizer_path:
                # Use user-specified tokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(self.tokenizer_path)
                print(f"✓ User-specified tokenizer loaded: {self.tokenizer_path}")
            else:
                # Use appropriate default based on model type
                if self.model_type == 'deberta':
                    self.tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-base")
                    self.tokenizer_path = "microsoft/deberta-v3-base"
                    print(f"✓ DeBERTa tokenizer loaded")
                else:
                    self.tokenizer = AutoTokenizer.from_pretrained("roberta-base")
                    self.tokenizer_path = "roberta-base"
                    print(f"✓ RoBERTa tokenizer loaded")
                    
        except Exception as e:
            print(f"Warning: Could not load tokenizer: {e}")
            # Fallback to roberta-base
            self.tokenizer = AutoTokenizer.from_pretrained("roberta-base")
            self.tokenizer_path = "roberta-base"
            print(f"✓ Fallback RoBERTa tokenizer loaded")
        
        # Set default parameters
        self.max_length = 512  # Standard for both RoBERTa and DeBERTa
        
        # Define class labels (assuming binary classification)
        self.class_labels = {0: "Non-STP", 1: "STP"}
        
        print(f"✓ {self.model_type.upper()} classifier initialized")
        print(f"  Max sequence length: {self.max_length}")
    
    def predict_stp(self, text: str) -> Tuple[str, float]:
        """
        Predict Social Tipping Point classification for a single text.
        
        Args:
            text: Input text to classify
            
        Returns:
            Tuple of (prediction_label, confidence_score)
        """
        try:
            # Tokenize input
            inputs = self.tokenizer(
                text,
                return_tensors="np",
                padding="max_length",
                truncation=True,
                max_length=self.max_length
            )
            
            # Ensure correct data types for ONNX
            ort_inputs = {
                "input_ids": inputs["input_ids"].astype(np.int64),
                "attention_mask": inputs["attention_mask"].astype(np.int64)
            }
            
            # Run ONNX inference
            ort_outputs = self.ort_session.run(None, ort_inputs)
            
            # Get logits (assuming the model outputs logits directly)
            logits = ort_outputs[0]
            
            # Apply softmax to get probabilities
            probabilities = self._softmax(logits[0])
            
            # Get prediction and confidence
            prediction_idx = np.argmax(probabilities)
            confidence = probabilities[prediction_idx]
            
            # Convert to label
            label = self.class_labels[prediction_idx]
            
            return label, float(confidence)
            
        except Exception as e:
            print(f"Error classifying text: {str(e)[:100]}...")
            return "Error", 0.0
    
    def _softmax(self, x):
        """Apply softmax to convert logits to probabilities"""
        exp_x = np.exp(x - np.max(x))  # Subtract max for numerical stability
        return exp_x / np.sum(exp_x)
    
    def predict_batch(self, texts: List[str], batch_size: int = 32) -> List[Tuple[str, float]]:
        """
        Predict STP classification for multiple texts in batches.
        
        Args:
            texts: List of texts to classify
            batch_size: Number of texts to process at once
            
        Returns:
            List of (prediction_label, confidence_score) tuples
        """
        results = []
        
        print(f"Processing {len(texts)} texts in batches of {batch_size}...")
        
        # Process in batches
        for i in tqdm(range(0, len(texts), batch_size), desc="Classifying chunks"):
            batch_texts = texts[i:i + batch_size]
            batch_results = []
            
            for text in batch_texts:
                prediction, confidence = self.predict_stp(text)
                batch_results.append((prediction, confidence))
            
            results.extend(batch_results)
        
        return results
    
    def classify_chunks_dataframe(self, df: pd.DataFrame, text_column: str = 'content') -> pd.DataFrame:
        """
        Classify chunks in a pandas DataFrame and add STP classification columns.
        
        Args:
            df: DataFrame containing chunk data
            text_column: Name of the column containing text to classify
            
        Returns:
            Enhanced DataFrame with STP classification results
        """
        print(f"Classifying chunks with {self.model_type.upper()} ONNX model...")
        print(f"  Model: {self.current_model_name}")
        print(f"  Input shape: {df.shape}")
        print(f"  Text column: {text_column}")
        
        # Validate input
        if text_column not in df.columns:
            raise ValueError(f"Text column '{text_column}' not found in DataFrame")
        
        # Extract texts
        texts = df[text_column].tolist()
        
        # Classify texts
        classifications = self.predict_batch(texts)
        
        # Create results DataFrame (copy original)
        result_df = df.copy()
        
        # Add classification results
        predictions, confidences = zip(*classifications)
        result_df['stp_prediction'] = predictions
        result_df['stp_confidence'] = confidences
        
        # Add processing metadata
        result_df['stp_classification_timestamp'] = datetime.now().isoformat()
        result_df['stp_model_version'] = f"{self.model_type.upper()}-ONNX-{self.current_model_name}"
        
        print(f"✓ {self.model_type.upper()} classification completed")
        print(f"  Output shape: {result_df.shape}")
        
        # Show classification summary
        stp_counts = result_df['stp_prediction'].value_counts()
        print(f"  Classification summary: {stp_counts.to_dict()}")
        
        return result_df


def create_roberta_classifier_with_models_folder(models_folder: str = "models/onnx_exports", 
                                                tokenizer_path: str = None) -> RoBERTaONNXClassifier:
    """
    Convenience function to create a RoBERTa/DeBERTa classifier with model selection from a folder.
    
    Args:
        models_folder: Path to folder containing ONNX models (default: "models/onnx_exports")
        tokenizer_path: Path to tokenizer directory (optional)
        
    Returns:
        Initialized RoBERTaONNXClassifier with model selection capabilities
    """
    return RoBERTaONNXClassifier(models_folder=models_folder, tokenizer_path=tokenizer_path)


def interactive_model_selection(models_folder: str = "models/onnx_exports") -> RoBERTaONNXClassifier:
    """
    Interactive function to select and load an ONNX model.
    
    Args:
        models_folder: Path to folder containing ONNX models
        
    Returns:
        RoBERTaONNXClassifier with user-selected model
    """
    print("=== Interactive ONNX Model Selection ===")
    
    # Initialize classifier
    classifier = RoBERTaONNXClassifier(models_folder=models_folder)
    
    # Show available models
    classifier.list_available_models()
    
    if not classifier.available_models:
        print("No models available for selection.")
        return classifier
    
    print("Select a model:")
    print("  - Enter a number (1-{}) to select by index".format(len(classifier.available_models)))
    print("  - Enter a model name (or part of it) to select by name")
    print("  - Press Enter to keep current model")
    
    try:
        user_input = input("\nYour choice: ").strip()
        
        if not user_input:
            print(f"Keeping current model: {classifier.current_model_name} ({classifier.model_type})")
        elif user_input.isdigit():
            # Select by index
            index = int(user_input)
            classifier.select_model_by_index(index)
        else:
            # Select by name
            classifier.select_model_by_name(user_input)
            
    except (KeyboardInterrupt, EOFError):
        print("\nSelection cancelled. Using current model.")
    
    return classifier