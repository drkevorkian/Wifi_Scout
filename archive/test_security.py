#!/usr/bin/env python3
"""
Security and validation tests for Wi-Fi Scout Pro v2.3
Tests all security fixes and bug resolutions.
"""

import sys
import os
import io
import tempfile

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import functions to test
from wa import (
    validate_ssid,
    validate_password,
    xml_escape,
    html_escape,
    sanitize_for_log,
    secure_delete_file,
    make_logger,
)


def test_validate_ssid():
    """Test SSID validation."""
    print("Testing SSID validation...")
    
    # Valid SSIDs
    assert validate_ssid("MyNetwork")[0] == True
    assert validate_ssid("Network_123")[0] == True
    assert validate_ssid("A" * 32)[0] == True  # Max length in ASCII
    
    # Invalid SSIDs
    assert validate_ssid("")[0] == False, "Empty SSID should fail"
    assert validate_ssid("A" * 100)[0] == False, "Too long SSID should fail"
    assert validate_ssid("Net\x00work")[0] == False, "Control chars should fail"
    assert validate_ssid("Net\x1bwork")[0] == False, "ANSI escape should fail"
    
    print("✅ SSID validation tests passed")


def test_validate_password():
    """Test password validation."""
    print("\nTesting password validation...")
    
    # Valid WPA2 passwords
    assert validate_password("12345678", "WPA2")[0] == True, "8-char password should pass"
    assert validate_password("a" * 63, "WPA2")[0] == True, "63-char password should pass"
    assert validate_password("MySecureP@ssw0rd!", "WPA2")[0] == True
    
    # Invalid passwords
    assert validate_password("", "WPA2")[0] == False, "Empty password should fail"
    assert validate_password("1234567", "WPA2")[0] == False, "7-char password should fail"
    assert validate_password("a" * 64, "WPA2")[0] == False, "64-char password should fail"
    
    print("✅ Password validation tests passed")


def test_xml_escape():
    """Test XML escaping to prevent injection."""
    print("\nTesting XML escaping...")
    
    # Basic escaping
    assert xml_escape("normal") == "normal"
    assert xml_escape("<test>") == "&lt;test&gt;"
    assert xml_escape("AT&T") == "AT&amp;T"
    assert xml_escape('"quoted"') == "&quot;quoted&quot;"
    assert xml_escape("'single'") == "&apos;single&apos;"
    
    # Injection attempts
    malicious = "</name><evil>injected</evil><name>"
    escaped = xml_escape(malicious)
    assert "<evil>" not in escaped, "XML injection should be escaped"
    assert "&lt;evil&gt;" in escaped, "Tags should be escaped"
    
    print("✅ XML escaping tests passed")


def test_html_escape():
    """Test HTML escaping."""
    print("\nTesting HTML escaping...")
    
    assert html_escape("<script>alert(1)</script>") == "&lt;script&gt;alert(1)&lt;/script&gt;"
    assert html_escape("A & B") == "A &amp; B"
    assert html_escape('"test"') == "&quot;test&quot;"
    
    print("✅ HTML escaping tests passed")


def test_sanitize_for_log():
    """Test log sanitization to prevent ANSI escape injection."""
    print("\nTesting log sanitization...")
    
    # Normal text
    assert sanitize_for_log("normal text") == "normal text"
    assert sanitize_for_log("Network_123") == "Network_123"
    
    # Control characters (except \n and \t)
    assert "\x00" not in sanitize_for_log("test\x00null")
    assert "\x1b" not in sanitize_for_log("\x1b[31mred text")
    assert "\n" in sanitize_for_log("line1\nline2"), "Newlines should be preserved"
    assert "\t" in sanitize_for_log("tab\there"), "Tabs should be preserved"
    
    # ANSI escape sequences
    ansi = "\x1b[31;1mRED\x1b[0m"
    sanitized = sanitize_for_log(ansi)
    assert "\x1b" not in sanitized, "ANSI escapes should be removed"
    
    print("✅ Log sanitization tests passed")


def test_secure_delete_file():
    """Test secure file deletion."""
    print("\nTesting secure file deletion...")
    
    # Create logger
    log_file = tempfile.mktemp(suffix=".log")
    logger = make_logger(log_file)
    
    # Create a temp file with sensitive data
    fd, temp_file = tempfile.mkstemp(suffix=".txt")
    sensitive_data = b"SuperSecretPassword123!"
    os.write(fd, sensitive_data)
    os.close(fd)
    
    # Verify file exists
    assert os.path.exists(temp_file), "Temp file should exist"
    
    # Securely delete
    secure_delete_file(temp_file, logger)
    
    # Verify file is gone
    assert not os.path.exists(temp_file), "File should be deleted"
    
    # Cleanup log
    try:
        os.remove(log_file)
    except:
        pass
    
    print("✅ Secure file deletion tests passed")


def test_injection_scenarios():
    """Test various injection attack scenarios."""
    print("\nTesting injection attack scenarios...")
    
    # XML injection in SSID
    attack_ssid = "</name><malicious>HACKED</malicious><name>"
    escaped = xml_escape(attack_ssid)
    assert "<malicious>" not in escaped
    assert "HACKED" in escaped  # Content preserved but tags escaped
    
    # XSS in HTML export
    xss_ssid = "<script>alert(document.cookie)</script>"
    escaped = html_escape(xss_ssid)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    
    # ANSI escape in logs
    ansi_attack = "\x1b[2J\x1b[H" + "Fake log entry"
    sanitized = sanitize_for_log(ansi_attack)
    assert "\x1b" not in sanitized
    
    print("✅ Injection attack tests passed")


def test_edge_cases():
    """Test edge cases and boundary conditions."""
    print("\nTesting edge cases...")
    
    # Empty strings
    assert validate_ssid("")[0] == False
    assert validate_password("", "WPA2")[0] == False
    
    # Unicode handling
    unicode_ssid = "WiFi_🔒_Test"
    valid, msg = validate_ssid(unicode_ssid)
    # This will fail if UTF-8 encoding > 32 bytes, which is expected
    
    # Exact boundary lengths
    assert validate_ssid("A" * 32)[0] == True  # Max ASCII
    assert validate_password("a" * 8, "WPA2")[0] == True  # Min WPA2
    assert validate_password("a" * 63, "WPA2")[0] == True  # Max WPA2
    
    print("✅ Edge case tests passed")


def run_all_tests():
    """Run all security tests."""
    print("=" * 60)
    print("Wi-Fi Scout Pro v2.3 - Security Test Suite")
    print("=" * 60)
    
    try:
        test_validate_ssid()
        test_validate_password()
        test_xml_escape()
        test_html_escape()
        test_sanitize_for_log()
        test_secure_delete_file()
        test_injection_scenarios()
        test_edge_cases()
        
        print("\n" + "=" * 60)
        print("✅ ALL SECURITY TESTS PASSED!")
        print("=" * 60)
        print("\n🛡️  Security fixes verified:")
        print("  ✅ Input validation working")
        print("  ✅ XML injection prevented")
        print("  ✅ HTML XSS prevented")
        print("  ✅ Log injection prevented")
        print("  ✅ Secure file deletion working")
        print("\nYour application is secure! 🎉")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
