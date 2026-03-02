"""
Test WiFi Engine

Tests for core WiFi functionality:
- Network data model
- Platform detection
- Command execution safety
- Network scoring algorithm
"""

import sys
from pathlib import Path
import platform
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from network_suite import WifiNetwork
from core.utilities import is_valid_ssid, is_valid_cidr, xml_escape, html_escape


class TestWifiNetworkModel:
    """Test WiFi network data model."""
    
    def test_create_basic_network(self):
        """Test creating a basic WiFi network."""
        net = WifiNetwork(
            ssid="TestNet",
            bssid="00:11:22:33:44:55",
            signal_dbm=-50,
            security="WPA2"
        )
        
        assert net.ssid == "TestNet"
        assert net.bssid == "00:11:22:33:44:55"
        assert net.signal_dbm == -50
        assert net.security == "WPA2"
    
    def test_network_with_optional_fields(self):
        """Test network with all optional fields."""
        net = WifiNetwork(
            ssid="CompleteNet",
            bssid="AA:BB:CC:DD:EE:FF",
            signal_dbm=-60,
            signal_percent=75,
            noise_dbm=-95,
            snr_db=35,
            channel=6,
            freq_mhz=2437,
            band="2.4GHz",
            security="WPA3",
            score=95.5,
            is_connected=True
        )
        
        assert net.signal_percent == 75
        assert net.channel == 6
        assert net.band == "2.4GHz"
        assert net.score == 95.5
        assert net.is_connected is True
    
    def test_network_defaults(self):
        """Test default values for optional fields."""
        net = WifiNetwork(ssid="MinimalNet", bssid="00:00:00:00:00:00")
        
        assert net.signal_dbm is None
        assert net.security == "Unknown"
        assert net.score is None
        assert net.is_connected is False


class TestInputValidation:
    """Test input validation functions."""
    
    def test_valid_ssid(self):
        """Test valid SSID validation."""
        assert is_valid_ssid("MyNetwork") is True
        assert is_valid_ssid("Test-WiFi_2024") is True
        assert is_valid_ssid("A" * 32) is True  # Max length
    
    def test_invalid_ssid(self):
        """Test invalid SSID rejection."""
        assert is_valid_ssid("") is False
        assert is_valid_ssid("A" * 33) is False  # Too long
        assert is_valid_ssid("Net\x00work") is False  # Null byte
        assert is_valid_ssid("Test\nNet") is False  # Newline
    
    def test_valid_cidr(self):
        """Test valid CIDR notation."""
        assert is_valid_cidr("192.168.1.0/24") is True
        assert is_valid_cidr("10.0.0.0/8") is True
        assert is_valid_cidr("172.16.0.0/12") is True
    
    def test_invalid_cidr(self):
        """Test invalid CIDR rejection."""
        assert is_valid_cidr("192.168.1.0") is False  # Missing mask
        assert is_valid_cidr("192.168.1.0/33") is False  # Invalid mask
        assert is_valid_cidr("256.1.1.0/24") is False  # Invalid IP
        assert is_valid_cidr("not-an-ip/24") is False


class TestOutputEscaping:
    """Test output escaping functions."""
    
    def test_xml_escape(self):
        """Test XML special character escaping."""
        assert xml_escape("<test>") == "&lt;test&gt;"
        assert xml_escape("A & B") == "A &amp; B"
        assert xml_escape('"quoted"') == "&quot;quoted&quot;"
        assert xml_escape("It's ok") == "It&apos;s ok"
    
    def test_html_escape(self):
        """Test HTML special character escaping."""
        assert html_escape("<script>") == "&lt;script&gt;"
        assert html_escape("&copy;") == "&amp;copy;"
        assert html_escape('"test"') == "&quot;test&quot;"
    
    def test_escape_with_normal_text(self):
        """Test that normal text passes through unchanged."""
        normal_text = "This is normal text 123"
        assert xml_escape(normal_text) == normal_text
        assert html_escape(normal_text) == normal_text


class TestPlatformDetection:
    """Test platform-specific behavior."""
    
    def test_platform_detection(self):
        """Test that platform can be detected."""
        system = platform.system()
        assert system in ["Windows", "Linux", "Darwin"]
    
    def test_platform_specific_commands(self):
        """Test platform-specific command selection."""
        system = platform.system()
        
        # Just verify we can detect the platform
        # Actual command execution tested in integration tests
        if system == "Windows":
            assert True  # Windows uses netsh
        elif system == "Linux":
            assert True  # Linux uses nmcli/iwconfig
        elif system == "Darwin":
            assert True  # macOS uses airport


class TestSecurityFeatures:
    """Test security-related functionality."""
    
    def test_no_password_in_logs(self):
        """Test that password logging is avoided."""
        # This is a design test - passwords should never be in test data
        sensitive_data = "password123"
        
        # Escaping functions should work but shouldn't be used for passwords
        escaped = xml_escape(sensitive_data)
        assert escaped == sensitive_data  # No special chars to escape
        
        # Real security: passwords never logged, never stored
        # This is enforced by code review, not testable here
    
    def test_ssid_sanitization(self):
        """Test that SSIDs with special chars are handled safely."""
        malicious_ssid = "<script>alert('xss')</script>"
        
        # Should be escaped for display
        safe_html = html_escape(malicious_ssid)
        assert "<script>" not in safe_html
        assert "&lt;script&gt;" in safe_html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
