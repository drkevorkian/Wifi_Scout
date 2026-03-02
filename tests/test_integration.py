"""
Integration Tests

Tests that verify end-to-end functionality:
- Mod loading and registration
- CLI execution paths
- Cross-platform compatibility checks
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestModIntegration:
    """Test mod integration with main application."""
    
    def test_all_mods_can_import(self):
        """Test that all mods can be imported without errors."""
        from mods import (
            dns_tool,
            ping_tool,
            traceroute_tool,
            http_tool,
            interfaces_tool,
            arp_tool,
            route_tool,
            lan_scan_tool,
        )
        
        # If we get here without ImportError, test passes
        assert True
    
    def test_all_mods_have_tool_instance(self):
        """Test that all mods provide a Tool class that can be instantiated."""
        mod_names = [
            "dns_tool",
            "ping_tool",
            "traceroute_tool",
            "http_tool",
            "interfaces_tool",
            "arp_tool",
            "route_tool",
            "lan_scan_tool",
        ]
        
        for mod_name in mod_names:
            mod = __import__(f"mods.{mod_name}", fromlist=["*"])
            
            # Find Tool class
            tool_classes = [
                getattr(mod, name) for name in dir(mod)
                if name.endswith("Tool") and not name.startswith("_")
            ]
            
            assert len(tool_classes) >= 1, f"{mod_name} has no Tool class"
            
            # Try to instantiate
            tool_instance = tool_classes[0]()
            assert hasattr(tool_instance, "name")
            assert hasattr(tool_instance, "description")


class TestApplicationImports:
    """Test main application imports."""
    
    def test_import_network_suite(self):
        """Test that network_suite can be imported."""
        import network_suite
        assert hasattr(network_suite, "main")
        assert hasattr(network_suite, "cli_main")
        assert hasattr(network_suite, "APP_NAME")
        assert hasattr(network_suite, "APP_VERSION")
    
    def test_import_wifi_engine(self):
        """Test that wifi_engine can be imported."""
        from core import wifi_engine
        assert hasattr(wifi_engine, "scan_wifi_networks")
    
    def test_import_utilities(self):
        """Test that utilities can be imported."""
        from core import utilities
        assert hasattr(utilities, "is_valid_ssid")
        assert hasattr(utilities, "xml_escape")
        assert hasattr(utilities, "html_escape")


class TestFeatureDetection:
    """Test optional feature detection."""
    
    def test_pyqt6_detection(self):
        """Test PyQt6 availability detection."""
        import network_suite
        assert hasattr(network_suite, "HAS_PYQT6")
        assert isinstance(network_suite.HAS_PYQT6, bool)
    
    def test_matplotlib_detection(self):
        """Test matplotlib availability detection."""
        import network_suite
        assert hasattr(network_suite, "HAS_MATPLOTLIB")
        assert isinstance(network_suite.HAS_MATPLOTLIB, bool)


class TestCoreDataStructures:
    """Test core data structures."""
    
    def test_tool_registry_accessible(self):
        """Test that TOOL_REGISTRY is accessible."""
        from network_suite import TOOL_REGISTRY
        assert isinstance(TOOL_REGISTRY, dict)
    
    def test_wifi_network_dataclass(self):
        """Test WifiNetwork dataclass."""
        from network_suite import WifiNetwork
        from dataclasses import is_dataclass
        
        assert is_dataclass(WifiNetwork)
        
        # Create instance
        net = WifiNetwork(ssid="Test", bssid="00:00:00:00:00:00")
        assert net.ssid == "Test"


class TestGoldenOutputs:
    """Test golden outputs for common operations."""
    
    def test_help_output_contains_commands(self):
        """Test that --help shows available commands."""
        from network_suite import create_cli_parser
        from io import StringIO
        import sys
        
        parser = create_cli_parser()
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            parser.parse_args(["--help"])
        except SystemExit:
            pass
        finally:
            help_text = sys.stdout.getvalue()
            sys.stdout = old_stdout
        
        # Should mention key commands
        assert "wifi" in help_text.lower()
        assert "dns" in help_text.lower() or "lookup" in help_text.lower()
        assert "ping" in help_text.lower()
    
    def test_version_output_format(self):
        """Test that --version output is properly formatted."""
        from network_suite import create_cli_parser, APP_VERSION
        from io import StringIO
        import sys
        
        parser = create_cli_parser()
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            parser.parse_args(["--version"])
        except SystemExit:
            pass
        finally:
            version_text = sys.stdout.getvalue()
            sys.stdout = old_stdout
        
        # Should contain version number
        assert APP_VERSION in version_text or "2.2.9" in version_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
