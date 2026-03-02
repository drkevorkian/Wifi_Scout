"""
Test CLI Functionality

Tests for command-line interface:
- Argument parsing
- Subcommand handling
- Output formatting
- Error handling
"""

import sys
from pathlib import Path
from io import StringIO
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from network_suite import create_cli_parser, APP_NAME, APP_VERSION


class TestCLIParser:
    """Test CLI argument parsing."""
    
    def test_parser_creation(self):
        """Test that parser can be created."""
        parser = create_cli_parser()
        assert parser is not None
    
    def test_help_argument(self):
        """Test --help argument."""
        parser = create_cli_parser()
        
        # Capture help output
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            parser.parse_args(["--help"])
        except SystemExit:
            # --help causes SystemExit, which is expected
            pass
        finally:
            help_output = sys.stdout.getvalue()
            sys.stdout = old_stdout
        
        assert APP_NAME in help_output or "network" in help_output.lower()
    
    def test_version_argument(self):
        """Test --version argument."""
        parser = create_cli_parser()
        
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            parser.parse_args(["--version"])
        except SystemExit:
            pass
        finally:
            version_output = sys.stdout.getvalue()
            sys.stdout = old_stdout
        
        assert APP_VERSION in version_output


class TestWiFiCommands:
    """Test WiFi subcommands."""
    
    def test_wifi_scan_command(self):
        """Test wifi scan command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["wifi", "scan"])
        
        assert args.command == "wifi"
        assert args.wifi_action == "scan"
    
    def test_wifi_best_command(self):
        """Test wifi best command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["wifi", "best"])
        
        assert args.command == "wifi"
        assert args.wifi_action == "best"
    
    def test_wifi_connect_command(self):
        """Test wifi connect command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["wifi", "connect", "TestNetwork", "--password", "test123"])
        
        assert args.command == "wifi"
        assert args.wifi_action == "connect"
        assert args.ssid == "TestNetwork"
        assert args.password == "test123"


class TestModCommands:
    """Test mod subcommands."""
    
    def test_dns_lookup_command(self):
        """Test DNS lookup command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["dns-lookup", "example.com"])
        
        assert args.command == "dns-lookup"
        assert args.domain == "example.com"
    
    def test_dns_lookup_with_types(self):
        """Test DNS lookup with record types."""
        parser = create_cli_parser()
        args = parser.parse_args(["dns-lookup", "example.com", "--types", "A", "AAAA", "MX"])
        
        assert args.command == "dns-lookup"
        assert args.domain == "example.com"
        assert "A" in args.types
        assert "AAAA" in args.types
        assert "MX" in args.types
    
    def test_ping_command(self):
        """Test ping command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["ping", "8.8.8.8"])
        
        assert args.command == "ping"
        assert args.host == "8.8.8.8"
    
    def test_ping_with_count(self):
        """Test ping with count option."""
        parser = create_cli_parser()
        args = parser.parse_args(["ping", "8.8.8.8", "--count", "10"])
        
        assert args.command == "ping"
        assert args.host == "8.8.8.8"
        assert args.count == 10
    
    def test_traceroute_command(self):
        """Test traceroute command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["traceroute", "google.com"])
        
        assert args.command == "traceroute"
        assert args.host == "google.com"
    
    def test_http_checker_command(self):
        """Test HTTP checker command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["http-checker", "https://example.com"])
        
        assert args.command == "http-checker"
        assert args.url == "https://example.com"
    
    def test_http_checker_with_method(self):
        """Test HTTP checker with method option."""
        parser = create_cli_parser()
        args = parser.parse_args(["http-checker", "https://api.example.com", "--method", "POST"])
        
        assert args.command == "http-checker"
        assert args.url == "https://api.example.com"
        assert args.method == "POST"
    
    def test_network_interfaces_command(self):
        """Test network interfaces command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["network-interfaces"])
        
        assert args.command == "network-interfaces"
    
    def test_arp_table_command(self):
        """Test ARP table command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["arp-table"])
        
        assert args.command == "arp-table"
    
    def test_routing_table_command(self):
        """Test routing table command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["routing-table"])
        
        assert args.command == "routing-table"
    
    def test_lan_scanner_command(self):
        """Test LAN scanner command parsing."""
        parser = create_cli_parser()
        args = parser.parse_args(["lan-scanner", "192.168.1.0/24"])
        
        assert args.command == "lan-scanner"
        assert args.network == "192.168.1.0/24"


class TestCLIErrorHandling:
    """Test CLI error handling."""
    
    def test_no_command(self):
        """Test behavior with no command (should show help or launch GUI)."""
        parser = create_cli_parser()
        # With no args, should default to GUI mode in main()
        # Parser itself will work, but main() decides behavior
        assert parser is not None
    
    def test_invalid_command(self):
        """Test invalid command."""
        parser = create_cli_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(["invalid-command"])
    
    def test_missing_required_argument(self):
        """Test missing required argument."""
        parser = create_cli_parser()
        
        with pytest.raises(SystemExit):
            # dns-lookup requires domain argument
            parser.parse_args(["dns-lookup"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
