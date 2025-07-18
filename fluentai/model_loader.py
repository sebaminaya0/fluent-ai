"""
LazyModelLoader: A shared model manager for FluentAI translation models.

This module provides a lazy loading mechanism for machine translation models
with LRU caching and async/threaded pre-loading capabilities.
"""

import asyncio
import logging
import threading

# Suppress warnings for package deprecations only
import warnings
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import whisper
from transformers import pipeline

warnings.filterwarnings("ignore", category=DeprecationWarning, module="pkg_resources")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LazyModelLoader:
    """
    A lazy-loading model manager that maintains an in-memory LRU cache of loaded models.
    
    Features:
    - Accepts a cache directory for model storage
    - Maintains an in-memory LRU cache of loaded models
    - Provides get_model(src_lang, tgt_lang) for on-demand model loading
    - Supports load_all_for_languages(lang_list) for auto-detection mode
    - Handles async/threaded pre-loading to keep GUI responsive
    """

    # Supported model configurations
    TRANSLATION_MODELS = {
        ('es', 'en'): 'Helsinki-NLP/opus-mt-es-en',
        ('en', 'es'): 'Helsinki-NLP/opus-mt-en-es',
        ('es', 'de'): 'Helsinki-NLP/opus-mt-es-de',
        ('de', 'es'): 'Helsinki-NLP/opus-mt-de-es',
        ('es', 'fr'): 'Helsinki-NLP/opus-mt-es-fr',
        ('fr', 'es'): 'Helsinki-NLP/opus-mt-fr-es',
        ('en', 'de'): 'Helsinki-NLP/opus-mt-en-de',
        ('de', 'en'): 'Helsinki-NLP/opus-mt-de-en',
        ('en', 'fr'): 'Helsinki-NLP/opus-mt-en-fr',
        ('fr', 'en'): 'Helsinki-NLP/opus-mt-fr-en',
    }

    WHISPER_MODELS = {
        'base': 'base',
        'small': 'small',
        'medium': 'medium',
        'large': 'large',
    }

    def __init__(self, cache_dir: str = "./model_cache", max_cache_size: int = 128):
        """
        Initialize the LazyModelLoader.
        
        Args:
            cache_dir: Directory to store cached models
            max_cache_size: Maximum number of models to keep in memory cache
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_cache_size = max_cache_size
        self._translation_models: dict[tuple[str, str], Any] = {}
        self._whisper_models: dict[str, Any] = {}
        self._loading_lock = threading.Lock()
        self._loading_status: dict[str, bool] = {}

        # Progress callback for GUI updates
        self.progress_callback: Callable[[str, float], None] | None = None

        # Thread pool for async loading
        self._executor = ThreadPoolExecutor(max_workers=4)

        logger.info(f"LazyModelLoader initialized with cache directory: {self.cache_dir}")

    def set_progress_callback(self, callback: Callable[[str, float], None]) -> None:
        """
        Set a callback function to report loading progress.
        
        Args:
            callback: Function that takes (status_message, progress_percentage) parameters
        """
        self.progress_callback = callback

    def _report_progress(self, message: str, progress: float) -> None:
        """Report progress to the callback if set."""
        if self.progress_callback:
            self.progress_callback(message, progress)
        logger.info(f"Progress: {message} ({progress:.1f}%)")

    def get_model(self, src_lang: str, tgt_lang: str) -> Any | None:
        """
        Get a translation model for the specified language pair.
        
        Loads the model on first request and reuses it from cache on subsequent requests.
        
        Args:
            src_lang: Source language code (e.g., 'es', 'en', 'de', 'fr')
            tgt_lang: Target language code (e.g., 'es', 'en', 'de', 'fr')
            
        Returns:
            The translation pipeline model, or None if not available
        """
        model_key = (src_lang, tgt_lang)

        # Check if model is already loaded
        if model_key in self._translation_models:
            logger.info(f"Using cached model for {src_lang} -> {tgt_lang}")
            return self._translation_models[model_key]

        # Check if model configuration exists
        if model_key not in self.TRANSLATION_MODELS:
            logger.warning(f"No model available for {src_lang} -> {tgt_lang}")
            return None

        # Load the model
        return self._load_translation_model(src_lang, tgt_lang)

    def _load_translation_model(self, src_lang: str, tgt_lang: str) -> Any | None:
        """
        Load a translation model and cache it.
        
        Args:
            src_lang: Source language code
            tgt_lang: Target language code
            
        Returns:
            The loaded model pipeline or None if loading failed
        """
        model_key = (src_lang, tgt_lang)
        model_id = self.TRANSLATION_MODELS[model_key]

        # Prevent multiple simultaneous loads of the same model
        with self._loading_lock:
            if model_key in self._translation_models:
                return self._translation_models[model_key]

            loading_key = f"translation_{src_lang}_{tgt_lang}"
            if loading_key in self._loading_status:
                # Model is currently being loaded by another thread
                logger.info(f"Model {model_key} is already being loaded, waiting...")
                return None

            self._loading_status[loading_key] = True

        try:
            self._report_progress(f"Loading translator {src_lang} -> {tgt_lang}...", 0.0)

            logger.info(f"Loading translation model: {model_id}")
            logger.info(f"Cache directory: {self.cache_dir}")

            # Load the model with explicit device handling
            import torch

            # Use CPU device for better compatibility
            device = "cpu"
            logger.info(f"Using device: {device}")

            # Load the model with device specification
            # Note: We don't pass cache_dir to pipeline as it can cause issues with model_kwargs
            model = pipeline(
                "translation",
                model=model_id,
                device=device,
                torch_dtype=torch.float32
            )

            logger.info(f"Pipeline created successfully for {model_key}")
            logger.info(f"Model type: {type(model)}")
            logger.info(f"Model device: {getattr(model.model, 'device', 'unknown')}")

            # Check if model has underlying PyTorch model
            if hasattr(model, 'model'):
                logger.info(f"Underlying model type: {type(model.model)}")
                logger.info(f"Model parameters on device: {next(model.model.parameters()).device if hasattr(model.model, 'parameters') else 'no parameters'}")

            # Cache the model (with LRU eviction if needed)
            self._cache_translation_model(model_key, model)

            self._report_progress(f"Loaded translator {src_lang} -> {tgt_lang}", 100.0)
            logger.info(f"Successfully loaded translation model: {model_key}")

            return model

        except Exception as e:
            logger.error(f"Failed to load translation model {model_key}: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception args: {e.args}")

            # Log traceback for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            self._report_progress(f"Failed to load translator {src_lang} -> {tgt_lang}", 0.0)
            return None

        finally:
            with self._loading_lock:
                self._loading_status.pop(loading_key, None)

    def _cache_translation_model(self, model_key: tuple[str, str], model: Any) -> None:
        """
        Cache a translation model with LRU eviction.
        
        Args:
            model_key: Language pair tuple
            model: The loaded model
        """
        # Simple LRU implementation - remove oldest if cache is full
        if len(self._translation_models) >= self.max_cache_size:
            # Remove the first (oldest) item
            oldest_key = next(iter(self._translation_models))
            removed_model = self._translation_models.pop(oldest_key)
            logger.info(f"Evicted model from cache: {oldest_key}")

            # Clean up if the model has cleanup methods
            if hasattr(removed_model, 'cleanup'):
                removed_model.cleanup()

        self._translation_models[model_key] = model

    def get_whisper_model(self, model_size: str = 'base') -> Any | None:
        """
        Get a Whisper model for speech recognition.
        
        Args:
            model_size: Size of the Whisper model ('base', 'small', 'medium', 'large')
            
        Returns:
            The Whisper model or None if loading failed
        """
        if model_size in self._whisper_models:
            logger.info(f"Using cached Whisper model: {model_size}")
            return self._whisper_models[model_size]

        if model_size not in self.WHISPER_MODELS:
            logger.warning(f"Unknown Whisper model size: {model_size}")
            return None

        return self._load_whisper_model(model_size)

    def _load_whisper_model(self, model_size: str) -> Any | None:
        """
        Load a Whisper model and cache it.
        
        Args:
            model_size: Size of the Whisper model
            
        Returns:
            The loaded Whisper model or None if loading failed
        """
        loading_key = f"whisper_{model_size}"

        # Prevent multiple simultaneous loads
        with self._loading_lock:
            if model_size in self._whisper_models:
                return self._whisper_models[model_size]

            if loading_key in self._loading_status:
                logger.info(f"Whisper model {model_size} is already being loaded, waiting...")
                return None

            self._loading_status[loading_key] = True

        try:
            self._report_progress(f"Loading Whisper model ({model_size})...", 0.0)

            logger.info(f"Loading Whisper model: {model_size}")
            model = whisper.load_model(model_size)

            logger.info("Whisper model loaded successfully")
            logger.info(f"Model type: {type(model)}")
            logger.info(f"Model device: {getattr(model, 'device', 'unknown')}")

            # Cache the model
            self._whisper_models[model_size] = model

            self._report_progress(f"Loaded Whisper model ({model_size})", 100.0)
            logger.info(f"Successfully loaded Whisper model: {model_size}")

            return model

        except Exception as e:
            logger.error(f"Failed to load Whisper model {model_size}: {e}")
            logger.error(f"Exception type: {type(e)}")
            logger.error(f"Exception args: {e.args}")

            # Log traceback for debugging
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

            self._report_progress(f"Failed to load Whisper model ({model_size})", 0.0)
            return None

        finally:
            with self._loading_lock:
                self._loading_status.pop(loading_key, None)

    def load_all_for_languages(self, lang_list: list[str]) -> dict[str, bool]:
        """
        Load all translation models for the specified languages.
        
        This method is used when auto-detection mode is enabled to pre-load
        all possible translation models for the given languages.
        
        Args:
            lang_list: List of language codes to load models for
            
        Returns:
            Dictionary mapping language pairs to loading success status
        """
        logger.info(f"Loading all models for languages: {lang_list}")

        # Generate all possible language pairs
        pairs_to_load = []
        for src_lang in lang_list:
            for tgt_lang in lang_list:
                if src_lang != tgt_lang and (src_lang, tgt_lang) in self.TRANSLATION_MODELS:
                    pairs_to_load.append((src_lang, tgt_lang))

        total_pairs = len(pairs_to_load)
        logger.info(f"Need to load {total_pairs} translation models")

        # Load models sequentially to avoid conflicts
        results = {}
        completed_count = 0

        for src_lang, tgt_lang in pairs_to_load:
            completed_count += 1

            try:
                logger.info(f"Loading model {completed_count}/{total_pairs}: {src_lang}->{tgt_lang}")
                model = self._load_translation_model(src_lang, tgt_lang)
                success = model is not None
                results[f"{src_lang}->{tgt_lang}"] = success

                # Report progress
                progress = (completed_count / total_pairs) * 100
                self._report_progress(
                    f"Loaded {completed_count}/{total_pairs} models",
                    progress
                )

            except Exception as e:
                logger.error(f"Error loading model {src_lang}->{tgt_lang}: {e}")
                results[f"{src_lang}->{tgt_lang}"] = False

        logger.info(f"Finished loading models. Success rate: {sum(results.values())}/{len(results)}")
        return results

    async def load_all_for_languages_async(self, lang_list: list[str]) -> dict[str, bool]:
        """
        Asynchronously load all translation models for the specified languages.
        
        This method provides the same functionality as load_all_for_languages
        but runs asynchronously to keep the GUI responsive.
        
        Args:
            lang_list: List of language codes to load models for
            
        Returns:
            Dictionary mapping language pairs to loading success status
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self.load_all_for_languages,
            lang_list
        )

    def preload_models_threaded(self, lang_list: list[str], callback: Callable[[dict[str, bool]], None] | None = None) -> threading.Thread:
        """
        Start pre-loading models in a separate thread.
        
        Args:
            lang_list: List of language codes to load models for
            callback: Optional callback to call when loading is complete
            
        Returns:
            The thread object handling the loading
        """
        def _load_and_callback():
            try:
                results = self.load_all_for_languages(lang_list)
                if callback:
                    callback(results)
            except Exception as e:
                logger.error(f"Error during threaded model loading: {e}")
                if callback:
                    callback({})

        thread = threading.Thread(target=_load_and_callback, daemon=True)
        thread.start()
        return thread

    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        """
        Get all supported language pairs for translation.
        
        Returns:
            List of (source_lang, target_lang) tuples
        """
        return list(self.TRANSLATION_MODELS.keys())

    def get_cached_models_info(self) -> dict[str, Any]:
        """
        Get information about currently cached models.
        
        Returns:
            Dictionary with cache statistics and model information
        """
        return {
            'translation_models_cached': len(self._translation_models),
            'whisper_models_cached': len(self._whisper_models),
            'cache_size_limit': self.max_cache_size,
            'translation_models': list(self._translation_models.keys()),
            'whisper_models': list(self._whisper_models.keys()),
            'supported_pairs': len(self.TRANSLATION_MODELS)
        }

    def clear_cache(self) -> None:
        """Clear all cached models to free memory."""
        with self._loading_lock:
            # Clear translation models
            for model_key, model in self._translation_models.items():
                if hasattr(model, 'cleanup'):
                    model.cleanup()
            self._translation_models.clear()

            # Clear Whisper models
            self._whisper_models.clear()

            logger.info("Model cache cleared")

    def shutdown(self) -> None:
        """Clean up resources and shutdown the model loader."""
        self.clear_cache()
        self._executor.shutdown(wait=True)
        logger.info("LazyModelLoader shutdown complete")
