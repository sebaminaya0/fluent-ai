#!/usr/bin/env python3
"""
Example usage of LazyModelLoader for FluentAI.

This script demonstrates how to use the LazyModelLoader class for:
1. Loading individual translation models on-demand
2. Loading all models for a set of languages (auto-detection mode)
3. Using async/threaded loading to keep GUI responsive
4. Monitoring cache status and performance
"""

import asyncio
import time

from fluentai.model_loader import LazyModelLoader


def progress_callback(message: str, progress: float):
    """Example progress callback for GUI updates."""
    print(f"Progress: {message} ({progress:.1f}%)")


async def main():
    """Demonstrate LazyModelLoader usage."""

    # Initialize the model loader
    print("🚀 Initializing LazyModelLoader...")
    loader = LazyModelLoader(
        cache_dir="./models",
        max_cache_size=10  # Small cache for demo
    )

    # Set up progress callback
    loader.set_progress_callback(progress_callback)

    # Example 1: Load individual models on demand
    print("\n📚 Example 1: Loading individual models on demand")
    print("=" * 50)

    # Load Spanish to English translator
    print("Loading Spanish -> English translator...")
    es_en_model = loader.get_model('es', 'en')
    if es_en_model:
        # Test translation
        result = es_en_model("Hola, ¿cómo estás?")
        print(f"Translation: {result[0]['translation_text']}")

    # Load English to Spanish translator (should be faster due to caching)
    print("Loading English -> Spanish translator...")
    en_es_model = loader.get_model('en', 'es')
    if en_es_model:
        # Test translation
        result = en_es_model("Hello, how are you?")
        print(f"Translation: {result[0]['translation_text']}")

    # Example 2: Load Whisper model
    print("\n🎤 Example 2: Loading Whisper model")
    print("=" * 50)

    whisper_model = loader.get_whisper_model('base')
    if whisper_model:
        print("Whisper model loaded successfully")

    # Example 3: Load all models for auto-detection mode
    print("\n🔄 Example 3: Loading all models for auto-detection")
    print("=" * 50)

    # Languages to support
    languages = ['es', 'en', 'de', 'fr']

    # Load all models synchronously (use this for demo, use async in GUI)
    print("Loading all models for languages:", languages)
    start_time = time.time()
    results = loader.load_all_for_languages(languages)
    end_time = time.time()

    print(f"\nLoading completed in {end_time - start_time:.2f} seconds")
    print("Results:")
    for pair, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} {pair}")

    # Example 4: Check cache status
    print("\n📊 Example 4: Cache status")
    print("=" * 50)

    cache_info = loader.get_cached_models_info()
    print(f"Translation models cached: {cache_info['translation_models_cached']}")
    print(f"Whisper models cached: {cache_info['whisper_models_cached']}")
    print(f"Cache size limit: {cache_info['cache_size_limit']}")
    print(f"Supported language pairs: {cache_info['supported_pairs']}")
    print("Cached translation models:", cache_info['translation_models'])
    print("Cached Whisper models:", cache_info['whisper_models'])

    # Example 5: Demonstrate async loading (for GUI integration)
    print("\n⚡ Example 5: Async loading demonstration")
    print("=" * 50)

    # Clear cache first
    loader.clear_cache()

    # Load models asynchronously
    print("Starting async loading...")
    async_start = time.time()
    async_results = await loader.load_all_for_languages_async(['es', 'en'])
    async_end = time.time()

    print(f"Async loading completed in {async_end - async_start:.2f} seconds")
    print("Async results:", async_results)

    # Example 6: Demonstrate threaded loading with callback
    print("\n🧵 Example 6: Threaded loading with callback")
    print("=" * 50)

    def loading_complete_callback(results):
        print("🎉 Threaded loading complete!")
        success_count = sum(1 for success in results.values() if success)
        print(f"Successfully loaded {success_count}/{len(results)} models")

    # Clear cache and start threaded loading
    loader.clear_cache()
    thread = loader.preload_models_threaded(['es', 'en'], loading_complete_callback)

    # Simulate doing other work while loading
    print("Doing other work while models load in background...")
    for i in range(5):
        time.sleep(1)
        print(f"  Other work step {i+1}/5")

    # Wait for loading to complete
    thread.join()

    # Cleanup
    print("\n🧹 Cleaning up...")
    loader.shutdown()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
