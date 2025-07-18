#!/usr/bin/env python3
"""
Benchmark tests for LazyModelLoader to measure startup time and memory usage.

This test suite focuses on:
1. Measuring startup time before/after lazy loading implementation
2. Measuring memory footprint with different numbers of language pairs
3. Comparing performance across different scenarios
4. Generating performance reports
"""

import json
import os
import sys
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

import psutil

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fluentai.model_loader import LazyModelLoader


class BenchmarkResults:
    """Container for benchmark results."""

    def __init__(self):
        self.results = {}
        self.metadata = {
            'timestamp': time.time(),
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'platform': sys.platform,
                'python_version': sys.version
            }
        }

    def add_result(self, test_name, result):
        """Add a benchmark result."""
        self.results[test_name] = result

    def save_to_file(self, filename):
        """Save results to JSON file."""
        data = {
            'metadata': self.metadata,
            'results': self.results
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def load_from_file(self, filename):
        """Load results from JSON file."""
        if not os.path.exists(filename):
            return None

        with open(filename) as f:
            data = json.load(f)
            self.metadata = data.get('metadata', {})
            self.results = data.get('results', {})

        return self


class MemoryProfiler:
    """Memory profiling utilities."""

    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = None

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        return self.process.memory_info().rss / 1024 / 1024

    def set_baseline(self):
        """Set baseline memory usage."""
        self.baseline_memory = self.get_memory_usage()

    def get_memory_delta(self):
        """Get memory usage delta from baseline."""
        if self.baseline_memory is None:
            self.set_baseline()
        return self.get_memory_usage() - self.baseline_memory


@contextmanager
def time_block(description=""):
    """Context manager to time a block of code."""
    start_time = time.time()
    yield
    elapsed = time.time() - start_time
    print(f"{description}: {elapsed:.3f}s")


class TestLazyModelLoaderBenchmarks(unittest.TestCase):
    """Benchmark tests for LazyModelLoader performance."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_cache_dir = "./test_cache_bench"
        self.memory_profiler = MemoryProfiler()
        self.benchmark_results = BenchmarkResults()
        self.results_file = Path("./test_data/benchmark_results.json")

        # Create test data directory
        Path("./test_data").mkdir(exist_ok=True)

        # Set memory baseline
        self.memory_profiler.set_baseline()

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up test cache directory
        import shutil
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)

        # Save benchmark results
        self.benchmark_results.save_to_file(self.results_file)

    def benchmark_startup_time_without_lazy_loading(self):
        """Benchmark startup time without lazy loading (simulated eager loading)."""
        print("Benchmarking startup time without lazy loading...")

        # Mock pipeline to simulate model loading time
        def mock_slow_pipeline(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms model loading time
            return Mock()

        with patch('fluentai.model_loader.pipeline', side_effect=mock_slow_pipeline):
            # Simulate eager loading by loading all models at startup
            start_time = time.time()
            start_memory = self.memory_profiler.get_memory_usage()

            loader = LazyModelLoader(cache_dir=self.test_cache_dir)

            # Load all supported language pairs (simulating eager loading)
            supported_pairs = loader.get_supported_language_pairs()
            for src_lang, tgt_lang in supported_pairs[:5]:  # Load first 5 pairs
                loader.get_model(src_lang, tgt_lang)

            end_time = time.time()
            end_memory = self.memory_profiler.get_memory_usage()

            startup_time = end_time - start_time
            memory_used = end_memory - start_memory

            result = {
                'startup_time': startup_time,
                'memory_usage': memory_used,
                'models_loaded': 5,
                'loading_strategy': 'eager'
            }

            self.benchmark_results.add_result('startup_without_lazy_loading', result)
            loader.shutdown()

            return result

    def benchmark_startup_time_with_lazy_loading(self):
        """Benchmark startup time with lazy loading."""
        print("Benchmarking startup time with lazy loading...")

        # Mock pipeline to simulate model loading time
        def mock_slow_pipeline(*args, **kwargs):
            time.sleep(0.1)  # Simulate 100ms model loading time
            return Mock()

        with patch('fluentai.model_loader.pipeline', side_effect=mock_slow_pipeline):
            start_time = time.time()
            start_memory = self.memory_profiler.get_memory_usage()

            # With lazy loading, just initialize the loader
            loader = LazyModelLoader(cache_dir=self.test_cache_dir)

            end_time = time.time()
            end_memory = self.memory_profiler.get_memory_usage()

            startup_time = end_time - start_time
            memory_used = end_memory - start_memory

            result = {
                'startup_time': startup_time,
                'memory_usage': memory_used,
                'models_loaded': 0,
                'loading_strategy': 'lazy'
            }

            self.benchmark_results.add_result('startup_with_lazy_loading', result)
            loader.shutdown()

            return result

    def benchmark_memory_footprint_multiple_language_pairs(self):
        """Benchmark memory footprint with 1, 5, and 20 language pairs."""
        print("Benchmarking memory footprint with multiple language pairs...")

        results = {}

        # Mock pipeline to return lightweight models
        def mock_pipeline(*args, **kwargs):
            # Simulate memory usage with a mock model
            mock_model = Mock()
            # Add some data to simulate memory usage
            mock_model._fake_data = b'x' * (1024 * 1024)  # 1MB of fake data
            return mock_model

        with patch('fluentai.model_loader.pipeline', side_effect=mock_pipeline):
            # Test with 1, 5, and 20 language pairs
            test_counts = [1, 5, 20]

            for pair_count in test_counts:
                print(f"Testing with {pair_count} language pairs...")

                start_memory = self.memory_profiler.get_memory_usage()
                loader = LazyModelLoader(cache_dir=self.test_cache_dir)

                supported_pairs = loader.get_supported_language_pairs()
                pairs_to_load = supported_pairs[:pair_count]

                # Load models and measure memory
                load_start_time = time.time()
                for src_lang, tgt_lang in pairs_to_load:
                    loader.get_model(src_lang, tgt_lang)
                load_end_time = time.time()

                end_memory = self.memory_profiler.get_memory_usage()

                result = {
                    'language_pairs': pair_count,
                    'memory_usage_mb': end_memory - start_memory,
                    'load_time_seconds': load_end_time - load_start_time,
                    'memory_per_pair_mb': (end_memory - start_memory) / pair_count if pair_count > 0 else 0
                }

                results[f'{pair_count}_pairs'] = result
                loader.shutdown()

                # Force garbage collection
                import gc
                gc.collect()

        self.benchmark_results.add_result('memory_footprint_multiple_pairs', results)
        return results

    def benchmark_concurrent_model_loading(self):
        """Benchmark concurrent model loading performance."""
        print("Benchmarking concurrent model loading...")

        def mock_slow_pipeline(*args, **kwargs):
            time.sleep(0.05)  # Simulate 50ms model loading time
            return Mock()

        with patch('fluentai.model_loader.pipeline', side_effect=mock_slow_pipeline):
            loader = LazyModelLoader(cache_dir=self.test_cache_dir)

            # Test sequential loading
            start_time = time.time()
            for i, (src_lang, tgt_lang) in enumerate(loader.get_supported_language_pairs()[:3]):
                loader.get_model(src_lang, tgt_lang)
            sequential_time = time.time() - start_time

            # Clear cache for concurrent test
            loader.clear_cache()

            # Test concurrent loading
            start_time = time.time()
            threads = []
            pairs_to_load = loader.get_supported_language_pairs()[:3]

            def load_model(src_lang, tgt_lang):
                loader.get_model(src_lang, tgt_lang)

            for src_lang, tgt_lang in pairs_to_load:
                thread = threading.Thread(target=load_model, args=(src_lang, tgt_lang))
                threads.append(thread)
                thread.start()

            for thread in threads:
                thread.join()

            concurrent_time = time.time() - start_time

            result = {
                'sequential_time': sequential_time,
                'concurrent_time': concurrent_time,
                'speedup_factor': sequential_time / concurrent_time if concurrent_time > 0 else 0,
                'models_loaded': 3
            }

            self.benchmark_results.add_result('concurrent_loading', result)
            loader.shutdown()

            return result

    def benchmark_cache_performance(self):
        """Benchmark cache hit vs miss performance."""
        print("Benchmarking cache performance...")

        def mock_slow_pipeline(*args, **kwargs):
            time.sleep(0.02)  # Simulate 20ms model loading time
            return Mock()

        with patch('fluentai.model_loader.pipeline', side_effect=mock_slow_pipeline):
            loader = LazyModelLoader(cache_dir=self.test_cache_dir)

            # Test cache miss (first load)
            start_time = time.time()
            model1 = loader.get_model('es', 'en')
            cache_miss_time = time.time() - start_time

            # Test cache hit (second load)
            start_time = time.time()
            model2 = loader.get_model('es', 'en')
            cache_hit_time = time.time() - start_time

            result = {
                'cache_miss_time': cache_miss_time,
                'cache_hit_time': cache_hit_time,
                'cache_speedup': cache_miss_time / cache_hit_time if cache_hit_time > 0 else 0,
                'models_same_instance': model1 is model2
            }

            self.benchmark_results.add_result('cache_performance', result)
            loader.shutdown()

            return result

    def benchmark_lru_eviction_performance(self):
        """Benchmark LRU cache eviction performance."""
        print("Benchmarking LRU eviction performance...")

        def mock_pipeline(*args, **kwargs):
            return Mock()

        with patch('fluentai.model_loader.pipeline', side_effect=mock_pipeline):
            # Create loader with small cache size
            loader = LazyModelLoader(cache_dir=self.test_cache_dir, max_cache_size=3)

            # Load models up to cache limit
            pairs = loader.get_supported_language_pairs()[:3]
            for src_lang, tgt_lang in pairs:
                loader.get_model(src_lang, tgt_lang)

            # Measure eviction performance
            start_time = time.time()
            # This should trigger eviction
            loader.get_model(pairs[3][0], pairs[3][1])
            eviction_time = time.time() - start_time

            result = {
                'eviction_time': eviction_time,
                'cache_size': len(loader._translation_models),
                'max_cache_size': loader.max_cache_size
            }

            self.benchmark_results.add_result('lru_eviction_performance', result)
            loader.shutdown()

            return result

    def test_startup_time_comparison(self):
        """Test and compare startup times with and without lazy loading."""
        eager_result = self.benchmark_startup_time_without_lazy_loading()
        lazy_result = self.benchmark_startup_time_with_lazy_loading()

        # Lazy loading should be significantly faster
        speedup = eager_result['startup_time'] / lazy_result['startup_time']

        print("Startup time comparison:")
        print(f"  Eager loading: {eager_result['startup_time']:.3f}s")
        print(f"  Lazy loading: {lazy_result['startup_time']:.3f}s")
        print(f"  Speedup: {speedup:.1f}x")

        # Assert that lazy loading is faster
        self.assertLess(lazy_result['startup_time'], eager_result['startup_time'],
                       "Lazy loading should be faster than eager loading")

        # Assert significant speedup (at least 2x)
        self.assertGreater(speedup, 2.0, "Lazy loading should provide at least 2x speedup")

    def test_memory_footprint_scaling(self):
        """Test memory footprint scaling with different numbers of language pairs."""
        results = self.benchmark_memory_footprint_multiple_language_pairs()

        print("Memory footprint scaling:")
        for test_name, result in results.items():
            print(f"  {result['language_pairs']} pairs: {result['memory_usage_mb']:.1f}MB "
                  f"({result['memory_per_pair_mb']:.1f}MB/pair)")

        # Memory usage should scale roughly linearly
        if '1_pairs' in results and '5_pairs' in results:
            memory_1 = results['1_pairs']['memory_usage_mb']
            memory_5 = results['5_pairs']['memory_usage_mb']

            # Memory should increase with more models
            self.assertGreater(memory_5, memory_1,
                             "Memory usage should increase with more language pairs")

            # Memory per pair should be relatively consistent
            per_pair_1 = results['1_pairs']['memory_per_pair_mb']
            per_pair_5 = results['5_pairs']['memory_per_pair_mb']

            # Allow some variance but should be in same ballpark
            self.assertLess(abs(per_pair_5 - per_pair_1) / per_pair_1, 0.5,
                           "Memory per pair should be relatively consistent")

    def test_concurrent_loading_performance(self):
        """Test concurrent model loading performance."""
        result = self.benchmark_concurrent_model_loading()

        print("Concurrent loading performance:")
        print(f"  Sequential: {result['sequential_time']:.3f}s")
        print(f"  Concurrent: {result['concurrent_time']:.3f}s")
        print(f"  Speedup: {result['speedup_factor']:.1f}x")

        # Concurrent loading should be faster (though not necessarily much faster
        # due to threading overhead and mocking)
        self.assertLessEqual(result['concurrent_time'], result['sequential_time'] * 1.1,
                            "Concurrent loading should not be significantly slower")

    def test_cache_hit_performance(self):
        """Test cache hit vs miss performance."""
        result = self.benchmark_cache_performance()

        print("Cache performance:")
        print(f"  Cache miss: {result['cache_miss_time']:.3f}s")
        print(f"  Cache hit: {result['cache_hit_time']:.3f}s")
        print(f"  Cache speedup: {result['cache_speedup']:.1f}x")

        # Cache hits should be much faster
        self.assertLess(result['cache_hit_time'], result['cache_miss_time'],
                       "Cache hits should be faster than cache misses")

        # Cache should provide significant speedup
        self.assertGreater(result['cache_speedup'], 10.0,
                          "Cache should provide at least 10x speedup")

        # Should return same instance
        self.assertTrue(result['models_same_instance'],
                       "Cache should return same model instance")

    def test_lru_eviction_performance(self):
        """Test LRU cache eviction performance."""
        result = self.benchmark_lru_eviction_performance()

        print("LRU eviction performance:")
        print(f"  Eviction time: {result['eviction_time']:.3f}s")
        print(f"  Cache size after eviction: {result['cache_size']}")
        print(f"  Max cache size: {result['max_cache_size']}")

        # Cache size should be maintained
        self.assertEqual(result['cache_size'], result['max_cache_size'],
                        "Cache size should be maintained at max_cache_size")

        # Eviction should be reasonably fast
        self.assertLess(result['eviction_time'], 0.1,
                       "Cache eviction should be fast")

    def test_performance_regression(self):
        """Test for performance regression against previous results."""
        # Load previous results if they exist
        previous_results = BenchmarkResults()
        if previous_results.load_from_file(self.results_file):
            print("Comparing against previous benchmark results...")

            # Compare key metrics
            current_cache_result = self.benchmark_cache_performance()

            if 'cache_performance' in previous_results.results:
                prev_cache = previous_results.results['cache_performance']

                # Check for significant regression (>50% slower)
                if current_cache_result['cache_hit_time'] > prev_cache['cache_hit_time'] * 1.5:
                    self.fail(f"Cache performance regression detected: "
                             f"current={current_cache_result['cache_hit_time']:.3f}s "
                             f"vs previous={prev_cache['cache_hit_time']:.3f}s")

                print("Cache performance comparison:")
                print(f"  Previous cache hit time: {prev_cache['cache_hit_time']:.3f}s")
                print(f"  Current cache hit time: {current_cache_result['cache_hit_time']:.3f}s")
        else:
            print("No previous benchmark results found - this is the baseline run")

    def test_generate_performance_report(self):
        """Generate comprehensive performance report."""
        print("\n" + "="*60)
        print("PERFORMANCE REPORT")
        print("="*60)

        # Run all benchmarks
        self.benchmark_startup_time_with_lazy_loading()
        self.benchmark_startup_time_without_lazy_loading()
        self.benchmark_memory_footprint_multiple_language_pairs()
        self.benchmark_concurrent_model_loading()
        self.benchmark_cache_performance()
        self.benchmark_lru_eviction_performance()

        # Print summary
        print("\nBenchmark Summary:")
        for test_name, result in self.benchmark_results.results.items():
            print(f"\n{test_name}:")
            if isinstance(result, dict):
                for key, value in result.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for subkey, subvalue in value.items():
                            print(f"    {subkey}: {subvalue}")
                    else:
                        print(f"  {key}: {value}")

        print(f"\nResults saved to: {self.results_file}")
        print("="*60)


if __name__ == '__main__':
    unittest.main()
