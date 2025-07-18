#!/usr/bin/env python3
"""
Unit tests for LazyModelLoader with mocking to test single loading behavior.

This test suite focuses on:
1. Ensuring models are loaded only once per language pair
2. Testing cache behavior and LRU eviction
3. Testing threaded loading mechanisms
4. Testing error handling and fallbacks
"""

import os
import sys
import threading
import time
import unittest
from unittest.mock import Mock, call, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.model_loader import LazyModelLoader


class TestLazyModelLoaderMocking(unittest.TestCase):
    """Test LazyModelLoader with mocking to assert single loading behavior."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_cache_dir = "./test_cache"
        self.loader = LazyModelLoader(cache_dir=self.test_cache_dir, max_cache_size=3)

        # Create mock progress callback
        self.progress_callback = Mock()
        self.loader.set_progress_callback(self.progress_callback)

    def tearDown(self):
        """Clean up test fixtures."""
        self.loader.shutdown()
        # Clean up test cache directory
        import shutil
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

    @patch('fluentai.model_loader.pipeline')
    def test_model_loaded_only_once_per_language_pair(self, mock_pipeline):
        """Test that models are loaded only once per language pair."""
        # Mock pipeline to return a fake model
        mock_model = Mock()
        mock_pipeline.return_value = mock_model

        # Request the same model multiple times
        src_lang, tgt_lang = 'es', 'en'

        # First request - should load model
        model1 = self.loader.get_model(src_lang, tgt_lang)

        # Second request - should return cached model
        model2 = self.loader.get_model(src_lang, tgt_lang)

        # Third request - should return cached model
        model3 = self.loader.get_model(src_lang, tgt_lang)

        # Assert pipeline was called only once
        mock_pipeline.assert_called_once_with(
            "translation",
            model='Helsinki-NLP/opus-mt-es-en',
            cache_dir=self.test_cache_dir
        )

        # Assert all returns are the same cached model
        self.assertIs(model1, model2)
        self.assertIs(model2, model3)
        self.assertIs(model1, mock_model)

        # Assert model is in cache
        self.assertIn((src_lang, tgt_lang), self.loader._translation_models)
        self.assertEqual(len(self.loader._translation_models), 1)

    @patch('fluentai.model_loader.pipeline')
    def test_different_language_pairs_load_separately(self, mock_pipeline):
        """Test that different language pairs are loaded separately."""
        # Mock pipeline to return different models for different calls
        mock_model1 = Mock()
        mock_model2 = Mock()
        mock_pipeline.side_effect = [mock_model1, mock_model2]

        # Load two different language pairs
        model1 = self.loader.get_model('es', 'en')
        model2 = self.loader.get_model('en', 'es')

        # Assert pipeline was called twice with different models
        expected_calls = [
            call("translation", model='Helsinki-NLP/opus-mt-es-en', cache_dir=self.test_cache_dir),
            call("translation", model='Helsinki-NLP/opus-mt-en-es', cache_dir=self.test_cache_dir)
        ]
        mock_pipeline.assert_has_calls(expected_calls)

        # Assert different models were returned
        self.assertIsNot(model1, model2)
        self.assertIs(model1, mock_model1)
        self.assertIs(model2, mock_model2)

        # Assert both models are in cache
        self.assertEqual(len(self.loader._translation_models), 2)

    @patch('fluentai.model_loader.pipeline')
    def test_lru_cache_eviction(self, mock_pipeline):
        """Test LRU cache eviction when cache size is exceeded."""
        # Set up loader with small cache size
        small_loader = LazyModelLoader(cache_dir=self.test_cache_dir, max_cache_size=2)

        # Mock pipeline to return different models
        mock_models = [Mock() for _ in range(3)]
        mock_pipeline.side_effect = mock_models

        # Load models up to cache limit
        model1 = small_loader.get_model('es', 'en')  # Should be cached
        model2 = small_loader.get_model('en', 'es')  # Should be cached

        # Check cache is at limit
        self.assertEqual(len(small_loader._translation_models), 2)

        # Load another model - should evict oldest
        model3 = small_loader.get_model('es', 'de')  # Should evict first model

        # Check cache size is maintained
        self.assertEqual(len(small_loader._translation_models), 2)

        # Check that first model was evicted
        self.assertNotIn(('es', 'en'), small_loader._translation_models)
        self.assertIn(('en', 'es'), small_loader._translation_models)
        self.assertIn(('es', 'de'), small_loader._translation_models)

        # Request first model again - should load again
        model1_again = small_loader.get_model('es', 'en')

        # Should have been called 4 times total (3 + 1 reload)
        self.assertEqual(mock_pipeline.call_count, 4)

        small_loader.shutdown()

    @patch('fluentai.model_loader.pipeline')
    def test_concurrent_loading_same_model(self, mock_pipeline):
        """Test concurrent loading of the same model results in single load."""
        # Mock pipeline with a delay to simulate loading time
        mock_model = Mock()

        def slow_pipeline(*args, **kwargs):
            time.sleep(0.1)  # Simulate loading time
            return mock_model

        mock_pipeline.side_effect = slow_pipeline

        # Results from concurrent threads
        results = []

        def load_model():
            model = self.loader.get_model('es', 'en')
            results.append(model)

        # Start multiple threads to load same model
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=load_model)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Assert pipeline was called only once despite concurrent requests
        mock_pipeline.assert_called_once()

        # Assert all threads that succeeded got the same model
        successful_results = [r for r in results if r is not None]
        self.assertGreater(len(successful_results), 0)

        # At least one thread should have gotten the model
        for result in successful_results:
            self.assertIs(result, mock_model)

    @patch('fluentai.model_loader.whisper')
    def test_whisper_model_loaded_only_once(self, mock_whisper):
        """Test that Whisper models are loaded only once."""
        # Mock whisper to return a fake model
        mock_model = Mock()
        mock_whisper.load_model.return_value = mock_model

        # Request the same model multiple times
        model_size = 'base'

        # First request - should load model
        model1 = self.loader.get_whisper_model(model_size)

        # Second request - should return cached model
        model2 = self.loader.get_whisper_model(model_size)

        # Third request - should return cached model
        model3 = self.loader.get_whisper_model(model_size)

        # Assert whisper.load_model was called only once
        mock_whisper.load_model.assert_called_once_with(model_size)

        # Assert all returns are the same cached model
        self.assertIs(model1, model2)
        self.assertIs(model2, model3)
        self.assertIs(model1, mock_model)

        # Assert model is in cache
        self.assertIn(model_size, self.loader._whisper_models)

    @patch('fluentai.model_loader.pipeline')
    def test_progress_callback_called(self, mock_pipeline):
        """Test that progress callback is called during loading."""
        mock_model = Mock()
        mock_pipeline.return_value = mock_model

        # Load a model
        self.loader.get_model('es', 'en')

        # Assert progress callback was called
        self.progress_callback.assert_any_call(
            "Loading translator es -> en...", 0.0
        )
        self.progress_callback.assert_any_call(
            "Loaded translator es -> en", 100.0
        )

    @patch('fluentai.model_loader.pipeline')
    def test_error_handling_in_model_loading(self, mock_pipeline):
        """Test error handling when model loading fails."""
        # Mock pipeline to raise an exception
        mock_pipeline.side_effect = Exception("Model loading failed")

        # Attempt to load model
        model = self.loader.get_model('es', 'en')

        # Assert model loading returned None
        self.assertIsNone(model)

        # Assert model is not in cache
        self.assertNotIn(('es', 'en'), self.loader._translation_models)

        # Assert progress callback was called for error
        self.progress_callback.assert_any_call(
            "Failed to load translator es -> en", 0.0
        )

    @patch('fluentai.model_loader.pipeline')
    def test_load_all_for_languages(self, mock_pipeline):
        """Test loading all models for specified languages."""
        # Mock pipeline to return different models
        mock_models = [Mock() for _ in range(4)]
        mock_pipeline.side_effect = mock_models

        # Load all models for es and en
        results = self.loader.load_all_for_languages(['es', 'en'])

        # Should have loaded es->en and en->es
        expected_results = {
            'es->en': True,
            'en->es': True
        }

        self.assertEqual(results, expected_results)

        # Assert pipeline was called for each pair
        self.assertEqual(mock_pipeline.call_count, 2)

        # Assert both models are cached
        self.assertEqual(len(self.loader._translation_models), 2)

    def test_unsupported_language_pair(self):
        """Test behavior with unsupported language pair."""
        # Request unsupported language pair
        model = self.loader.get_model('es', 'es')  # Same language

        # Should return None
        self.assertIsNone(model)

        # Model should not be in cache
        self.assertNotIn(('es', 'es'), self.loader._translation_models)

    def test_cache_info_accuracy(self):
        """Test that cache info reflects actual cache state."""
        # Initial state
        info = self.loader.get_cached_models_info()
        self.assertEqual(info['translation_models_cached'], 0)
        self.assertEqual(info['whisper_models_cached'], 0)

        # Load a translation model
        with patch('fluentai.model_loader.pipeline') as mock_pipeline:
            mock_pipeline.return_value = Mock()
            self.loader.get_model('es', 'en')

        # Check updated info
        info = self.loader.get_cached_models_info()
        self.assertEqual(info['translation_models_cached'], 1)
        self.assertEqual(info['whisper_models_cached'], 0)

        # Load a whisper model
        with patch('fluentai.model_loader.whisper') as mock_whisper:
            mock_whisper.load_model.return_value = Mock()
            self.loader.get_whisper_model('base')

        # Check final info
        info = self.loader.get_cached_models_info()
        self.assertEqual(info['translation_models_cached'], 1)
        self.assertEqual(info['whisper_models_cached'], 1)

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Load some models
        with patch('fluentai.model_loader.pipeline') as mock_pipeline:
            mock_pipeline.return_value = Mock()
            self.loader.get_model('es', 'en')

        with patch('fluentai.model_loader.whisper') as mock_whisper:
            mock_whisper.load_model.return_value = Mock()
            self.loader.get_whisper_model('base')

        # Verify models are cached
        self.assertEqual(len(self.loader._translation_models), 1)
        self.assertEqual(len(self.loader._whisper_models), 1)

        # Clear cache
        self.loader.clear_cache()

        # Verify cache is empty
        self.assertEqual(len(self.loader._translation_models), 0)
        self.assertEqual(len(self.loader._whisper_models), 0)


if __name__ == '__main__':
    unittest.main()
