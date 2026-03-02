"""
Test Plugin Loader

Tests for the modular plugin architecture:
- Dynamic mod discovery
- Mod registration
- Tool registry management
- Error handling for malformed mods
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from network_suite import TOOL_REGISTRY, register_tool


class TestPluginLoader:
    """Test the plugin loading system."""
    
    def setup_method(self):
        """Clear registry before each test."""
        TOOL_REGISTRY.clear()
    
    def test_tool_registry_exists(self):
        """Test that TOOL_REGISTRY is accessible."""
        assert isinstance(TOOL_REGISTRY, dict)
    
    def test_register_tool_basic(self):
        """Test basic tool registration."""
        # Create a mock tool
        class MockTool:
            name = "test_tool"
            description = "A test tool"
        
        mock_instance = MockTool()
        register_tool(mock_instance)
        
        assert "test_tool" in TOOL_REGISTRY
        assert TOOL_REGISTRY["test_tool"] == mock_instance
    
    def test_register_tool_duplicate_name(self):
        """Test that duplicate tool names overwrite (last one wins)."""
        class MockTool1:
            name = "duplicate"
            description = "First tool"
        
        class MockTool2:
            name = "duplicate"
            description = "Second tool"
        
        register_tool(MockTool1())
        register_tool(MockTool2())
        
        assert "duplicate" in TOOL_REGISTRY
        assert TOOL_REGISTRY["duplicate"].description == "Second tool"
    
    def test_register_tool_multiple(self):
        """Test registering multiple tools."""
        tools = []
        for i in range(5):
            class MockTool:
                name = f"tool_{i}"
                description = f"Tool {i}"
            tools.append(MockTool())
            register_tool(tools[-1])
        
        assert len(TOOL_REGISTRY) == 5
        for i in range(5):
            assert f"tool_{i}" in TOOL_REGISTRY


class TestModDiscovery:
    """Test discovery of mods from filesystem."""
    
    def test_mods_directory_exists(self):
        """Test that mods directory exists."""
        mods_dir = Path(__file__).parent.parent / "mods"
        assert mods_dir.exists()
        assert mods_dir.is_dir()
    
    def test_mods_have_init(self):
        """Test that mods package has __init__.py."""
        init_file = Path(__file__).parent.parent / "mods" / "__init__.py"
        assert init_file.exists()
    
    def test_example_mod_exists(self):
        """Test that example template exists."""
        example_mod = Path(__file__).parent.parent / "mods" / "example_tool.py"
        assert example_mod.exists()
    
    def test_core_mods_exist(self):
        """Test that core diagnostic mods exist."""
        mods_dir = Path(__file__).parent.parent / "mods"
        expected_mods = [
            "dns_tool.py",
            "ping_tool.py",
            "traceroute_tool.py",
            "http_tool.py",
            "interfaces_tool.py",
            "arp_tool.py",
            "route_tool.py",
            "lan_scan_tool.py",
        ]
        
        for mod_file in expected_mods:
            mod_path = mods_dir / mod_file
            assert mod_path.exists(), f"Missing mod: {mod_file}"


class TestModStructure:
    """Test that mods follow expected structure."""
    
    def test_dns_tool_structure(self):
        """Test DNS tool has required components."""
        from mods import dns_tool
        
        # Check for required classes/functions
        assert hasattr(dns_tool, "DNSLookupTool")
        
        # Check tool can be instantiated
        tool = dns_tool.DNSLookupTool()
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert tool.name == "dns-lookup"
    
    def test_ping_tool_structure(self):
        """Test Ping tool has required components."""
        from mods import ping_tool
        
        assert hasattr(ping_tool, "PingTool")
        tool = ping_tool.PingTool()
        assert tool.name == "ping"
    
    def test_all_mods_have_tool_class(self):
        """Test all mods can be imported and have Tool classes."""
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
            
            # Find the Tool class (convention: ends with "Tool")
            tool_classes = [
                name for name in dir(mod)
                if name.endswith("Tool") and not name.startswith("_")
            ]
            
            assert len(tool_classes) >= 1, f"{mod_name} missing Tool class"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
