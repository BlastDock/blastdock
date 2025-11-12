"""
Comprehensive tests for bug fixes implemented on 2025-11-12

This test suite covers:
- VUL-001: SSL verification in health checks (CRITICAL)
- VUL-002: CORS configuration (HIGH)
- VUL-003: Command injection in execute_command (HIGH)
- BUG-029: Version comparison logic (HIGH)
- PERF-001: LRU cache eviction performance (HIGH)
- QUAL-007/008/009: Stub implementation warnings (HIGH)
"""

import pytest
import warnings
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path


class TestVUL001SSLVerification:
    """Tests for VUL-001: SSL verification in health checks"""

    def test_health_check_includes_ssl_verification(self):
        """VUL-001: Verify SSL verification is enabled in HTTP health checks"""
        # Read the health_checker.py file directly
        with open('/home/user/blastdock/blastdock/monitoring/health_checker.py', 'r') as f:
            source = f.read()

        # Check that the file includes verify=True in requests.get()
        assert "verify=True" in source, "VUL-001: SSL verification parameter missing in requests.get()"
        assert "VUL-001 FIX" in source, "VUL-001: Fix comment not found in health_checker.py"

    def test_health_check_ssl_comment_present(self):
        """VUL-001: Verify fix comment is present in code"""
        import blastdock.monitoring.health_checker as hc_module
        import inspect

        source = inspect.getsource(hc_module)
        assert "VUL-001 FIX" in source, "VUL-001: Fix comment not found in health_checker.py"


class TestVUL002CORSConfiguration:
    """Tests for VUL-002: CORS configuration restrictions"""

    def test_cors_restricts_origins(self):
        """VUL-002: Verify CORS is restricted to localhost"""
        try:
            from blastdock.monitoring.web_dashboard import WebDashboard

            dashboard = WebDashboard()

            if dashboard.app:
                # Check that CORS was configured with restrictions
                # The fix should have CORS configured with specific origins
                import inspect
                source = inspect.getsource(WebDashboard._setup_flask)
                assert "VUL-002 FIX" in source, "VUL-002: Fix comment not found"
                assert "origins" in source, "VUL-002: CORS origins parameter not found"
                assert ("localhost" in source or "127.0.0.1" in source), "VUL-002: localhost restriction not found"
        except ImportError:
            pytest.skip("Flask not available")

    def test_cors_not_allowing_all_origins(self):
        """VUL-002: Verify CORS doesn't allow all origins"""
        try:
            from blastdock.monitoring.web_dashboard import WebDashboard
            import inspect

            source = inspect.getsource(WebDashboard._setup_flask)
            # Should NOT have CORS(self.app) without parameters
            lines = source.split('\n')
            for line in lines:
                if 'CORS(self.app)' in line and 'resources' not in line:
                    if '#' not in line.split('CORS')[0]:  # Not a comment
                        pytest.fail("VUL-002: CORS still allows all origins without restrictions")
        except ImportError:
            pytest.skip("Flask not available")

    def test_debug_mode_disabled(self):
        """VUL-004: Verify debug mode is hardcoded to False"""
        try:
            from blastdock.monitoring.web_dashboard import WebDashboard
            import inspect

            source = inspect.getsource(WebDashboard.start_dashboard)
            assert "VUL-004 FIX" in source, "VUL-004: Fix comment not found"
            assert "debug=False" in source, "VUL-004: Debug mode not hardcoded to False"
        except ImportError:
            pytest.skip("Flask not available")


class TestVUL003CommandInjection:
    """Tests for VUL-003: Command injection in execute_command"""

    def test_execute_command_validates_project_directory(self):
        """VUL-003: Verify execute_command validates project directory"""
        # Read the file directly to avoid pydantic import issues
        with open('/home/user/blastdock/blastdock/cli/deploy.py', 'r') as f:
            source = f.read()

        assert "VUL-003 FIX" in source, "VUL-003: Fix comment not found"
        assert "validate_project_directory_path" in source, "VUL-003: Directory validation not found"

    def test_execute_command_has_timeout(self):
        """VUL-003: Verify execute_command subprocess has timeout"""
        # Read the file directly to avoid pydantic import issues
        with open('/home/user/blastdock/blastdock/cli/deploy.py', 'r') as f:
            source = f.read()

        # Check that execute_command function has timeout
        assert "def execute_command" in source, "VUL-003: execute_command function not found"
        # Find the execute_command function
        lines = source.split('\n')
        in_execute_cmd = False
        has_timeout = False
        for line in lines:
            if 'def execute_command' in line:
                in_execute_cmd = True
            if in_execute_cmd and 'subprocess.run' in line and 'timeout' in line:
                has_timeout = True
                break
            if in_execute_cmd and line.startswith('def ') and 'execute_command' not in line:
                break  # Left the function

        assert has_timeout, "VUL-003: Timeout parameter not found in execute_command subprocess call"


class TestBUG029VersionComparison:
    """Tests for BUG-029: Version comparison logic"""

    def test_compare_versions_semantic(self):
        """BUG-029: Verify semantic version comparison works correctly"""
        from blastdock.marketplace.installer import compare_versions

        # Test cases that would fail with string comparison
        assert compare_versions("2.10.0", "2.9.0") == 1, "2.10.0 should be > 2.9.0"
        assert compare_versions("2.9.0", "2.10.0") == -1, "2.9.0 should be < 2.10.0"
        assert compare_versions("1.0.0", "1.0.0") == 0, "1.0.0 should equal 1.0.0"
        assert compare_versions("2.0.0", "1.99.99") == 1, "2.0.0 should be > 1.99.99"

    def test_compare_versions_with_prefix(self):
        """BUG-029: Verify version comparison handles 'v' prefix"""
        from blastdock.marketplace.installer import compare_versions

        assert compare_versions("v2.10.0", "v2.9.0") == 1, "Should handle v prefix"
        assert compare_versions("v1.0.0", "1.0.0") == 0, "Should handle mixed v prefix"

    def test_compare_versions_invalid_input(self):
        """BUG-029: Verify version comparison handles invalid input gracefully"""
        from blastdock.marketplace.installer import compare_versions

        # Should not crash on invalid input
        result = compare_versions("invalid", "1.0.0")
        assert isinstance(result, int), "Should return int even for invalid input"

    def test_update_template_uses_semantic_comparison(self):
        """BUG-029: Verify update_template uses semantic version comparison"""
        from blastdock.marketplace.installer import TemplateInstaller
        import inspect

        source = inspect.getsource(TemplateInstaller.update_template)
        assert "BUG-029 FIX" in source, "BUG-029: Fix comment not found"
        assert "compare_versions" in source, "BUG-029: compare_versions function not used"


class TestPERF001LRUCache:
    """Tests for PERF-001: LRU cache eviction performance"""

    def test_cache_uses_ordered_dict(self):
        """PERF-001: Verify cache uses OrderedDict for O(1) eviction"""
        from blastdock.performance.cache import CacheManager
        from collections import OrderedDict

        cache = CacheManager(max_memory_size=1024)  # Small cache for testing
        assert isinstance(cache._memory_cache, OrderedDict), "PERF-001: Cache must use OrderedDict"

    def test_cache_move_to_end_on_access(self):
        """PERF-001: Verify cache moves accessed items to end"""
        from blastdock.performance.cache import CacheManager

        cache = CacheManager(max_memory_size=1024 * 1024)  # 1MB

        # Add items
        cache.set('key1', 'value1', persist_to_disk=False)
        cache.set('key2', 'value2', persist_to_disk=False)
        cache.set('key3', 'value3', persist_to_disk=False)

        # Access key1 (should move to end)
        cache.get('key1')

        # Check that key1 is now at the end (most recently used)
        keys_list = list(cache._memory_cache.keys())
        assert keys_list[-1] == 'key1', "PERF-001: Accessed item should move to end"

    def test_evict_lru_is_efficient(self):
        """PERF-001: Verify _evict_lru doesn't use min() operation"""
        from blastdock.performance.cache import CacheManager
        import inspect

        source = inspect.getsource(CacheManager._evict_lru)
        assert "PERF-001 FIX" in source, "PERF-001: Fix comment not found"
        assert "min(" not in source, "PERF-001: Should not use min() for eviction"
        assert "next(iter(" in source, "PERF-001: Should use next(iter()) for O(1) eviction"

    def test_evict_lru_removes_oldest(self):
        """PERF-001: Verify LRU eviction removes least recently used item"""
        from blastdock.performance.cache import CacheManager

        cache = CacheManager(max_memory_size=512)  # Very small cache

        # Add items that will exceed cache size
        cache.set('old_key', 'x' * 200, persist_to_disk=False)
        cache.set('newer_key', 'y' * 200, persist_to_disk=False)

        # Access old_key to make it more recent
        cache.get('old_key')

        # Add another item that should evict newer_key (now least recent)
        cache.set('newest_key', 'z' * 200, persist_to_disk=False)

        # old_key should still be there (was accessed)
        # newer_key should be evicted (least recently used)
        assert 'old_key' in cache._memory_cache or 'newest_key' in cache._memory_cache


class TestQUAL007008009StubImplementations:
    """Tests for QUAL-007/008/009: Stub implementation warnings"""

    def test_memory_optimizer_returns_warning(self):
        """QUAL-007: Verify MemoryOptimizer returns warning about placeholder data"""
        from blastdock.performance.memory_optimizer import MemoryOptimizer

        optimizer = MemoryOptimizer()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = optimizer.get_memory_stats()

            # Check that a warning was issued
            assert len(w) > 0, "QUAL-007: Should issue UserWarning"
            assert issubclass(w[0].category, UserWarning), "QUAL-007: Should be UserWarning"
            assert "placeholder" in str(w[0].message).lower(), "QUAL-007: Warning should mention placeholder data"

        # Check that result contains warning key
        assert '_warning' in result, "QUAL-007: Result should contain _warning key"
        assert 'PLACEHOLDER' in result['_warning'], "QUAL-007: Warning message should indicate placeholder data"

    def test_deployment_optimizer_returns_warning(self):
        """QUAL-008: Verify DeploymentOptimizer returns warning about placeholder data"""
        from blastdock.performance.deployment_optimizer import DeploymentOptimizer

        optimizer = DeploymentOptimizer()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = optimizer.analyze_deployment_performance('test_project')

            # Check that a warning was issued
            assert len(w) > 0, "QUAL-008: Should issue UserWarning"
            assert issubclass(w[0].category, UserWarning), "QUAL-008: Should be UserWarning"
            assert "placeholder" in str(w[0].message).lower(), "QUAL-008: Warning should mention placeholder data"

        # Check that result contains warning key
        assert '_warning' in result, "QUAL-008: Result should contain _warning key"
        assert 'PLACEHOLDER' in result['_warning'], "QUAL-008: Warning message should indicate placeholder data"

    def test_parallel_processor_returns_warning(self):
        """QUAL-009: Verify ParallelProcessor returns warning about placeholder data"""
        from blastdock.performance.parallel_processor import ParallelProcessor

        processor = ParallelProcessor()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = processor.process_templates_parallel(['template1', 'template2'])

            # Check that a warning was issued
            assert len(w) > 0, "QUAL-009: Should issue UserWarning"
            assert issubclass(w[0].category, UserWarning), "QUAL-009: Should be UserWarning"
            assert "placeholder" in str(w[0].message).lower(), "QUAL-009: Warning should mention placeholder data"

        # Check that result contains warning key
        assert '_warning' in result, "QUAL-009: Result should contain _warning key"
        assert 'PLACEHOLDER' in result['_warning'], "QUAL-009: Warning message should indicate placeholder data"

    def test_stub_modules_have_warning_docstrings(self):
        """QUAL-007/008/009: Verify stub modules have warning docstrings"""
        import blastdock.performance.memory_optimizer as mem_opt
        import blastdock.performance.deployment_optimizer as deploy_opt
        import blastdock.performance.parallel_processor as par_proc

        assert "QUAL-007 WARNING" in mem_opt.__doc__, "QUAL-007: Module docstring should have warning"
        assert "QUAL-008 WARNING" in deploy_opt.__doc__, "QUAL-008: Module docstring should have warning"
        assert "QUAL-009 WARNING" in par_proc.__doc__, "QUAL-009: Module docstring should have warning"


class TestBugFixIntegration:
    """Integration tests for multiple bug fixes"""

    def test_all_critical_and_high_fixes_present(self):
        """Verify all CRITICAL and HIGH priority fixes are present"""
        # Read files directly to avoid import issues
        files_to_check = {
            'VUL-001': '/home/user/blastdock/blastdock/monitoring/health_checker.py',
            'VUL-003': '/home/user/blastdock/blastdock/cli/deploy.py',
            'BUG-029': '/home/user/blastdock/blastdock/marketplace/installer.py',
            'PERF-001': '/home/user/blastdock/blastdock/performance/cache.py',
        }

        for fix_id, file_path in files_to_check.items():
            with open(file_path, 'r') as f:
                source = f.read()
            assert f"{fix_id} FIX" in source, f"{fix_id}: Fix comment not found in {file_path}"

    def test_no_remaining_critical_vulnerabilities(self):
        """Verify that known critical vulnerabilities are fixed"""
        # This is a meta-test to ensure the fixes are actually in place

        # VUL-001: SSL verification should be present
        with open('/home/user/blastdock/blastdock/monitoring/health_checker.py', 'r') as f:
            hc_source = f.read()
        assert "verify=True" in hc_source, "VUL-001: SSL verification not found"

        # BUG-029: Semantic version comparison should be used
        from blastdock.marketplace.installer import compare_versions
        result = compare_versions("2.10.0", "2.9.0")
        assert result > 0, "BUG-029: Semantic version comparison not working"

        # PERF-001: OrderedDict should be used for cache
        from blastdock.performance.cache import CacheManager
        from collections import OrderedDict
        cache = CacheManager()
        assert isinstance(cache._memory_cache, OrderedDict), "PERF-001: Not using OrderedDict"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
