#!/usr/bin/env python3
"""
Test script to verify Wi-Fi Scout Pro functionality without running full GUI
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required imports work"""
    print("Testing imports...")
    try:
        import wa
        print("✓ Main module imports successfully")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("✓ PyQt6 is available")
    except ImportError:
        print("✗ PyQt6 not installed. Run: pip install PyQt6")
        return False
    
    try:
        import matplotlib
        print("✓ matplotlib is available (signal history will work)")
    except ImportError:
        print("⚠ matplotlib not installed (signal history charts disabled)")
        print("  Install with: pip install matplotlib")
    
    return True

def test_scanner_logic():
    """Test scanner utility functions"""
    print("\nTesting scanner logic...")
    try:
        from wa import infer_band, normalize_security, percent_to_dbm
        
        # Test band inference
        assert infer_band(2437, None) == "2.4GHz"
        assert infer_band(5180, None) == "5GHz"
        assert infer_band(None, 6) == "2.4GHz"
        assert infer_band(None, 36) == "5GHz"
        print("✓ Band inference works correctly")
        
        # Test security normalization
        assert normalize_security("WPA2-Personal") == "WPA2"
        assert normalize_security("Open") == "OPEN"
        assert normalize_security("WPA3-SAE") == "WPA3"
        print("✓ Security normalization works correctly")
        
        # Test percent to dBm conversion
        assert percent_to_dbm(100) == -50
        assert percent_to_dbm(0) == -100
        print("✓ Signal conversion works correctly")
        
        return True
    except Exception as e:
        print(f"✗ Logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_models():
    """Test data classes"""
    print("\nTesting data models...")
    try:
        from wa import WifiNetwork, NetworkHistory
        
        # Test WifiNetwork creation
        net = WifiNetwork(
            ssid="TestNetwork",
            bssid="aa:bb:cc:dd:ee:ff",
            signal_dbm=-65,
            channel=6,
            security="WPA2"
        )
        assert net.ssid == "TestNetwork"
        assert net.signal_dbm == -65
        print("✓ WifiNetwork dataclass works")
        
        # Test NetworkHistory
        hist = NetworkHistory(
            bssid="aa:bb:cc:dd:ee:ff",
            ssid="TestNetwork",
            timestamps=[],
            signals=[]
        )
        hist.add_reading(1000.0, -65)
        hist.add_reading(1001.0, -67)
        assert len(hist.timestamps) == 2
        assert len(hist.signals) == 2
        print("✓ NetworkHistory works correctly")
        
        return True
    except Exception as e:
        print(f"✗ Data model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scoring():
    """Test network scoring algorithm"""
    print("\nTesting scoring algorithm...")
    try:
        from wa import score_network, WifiNetwork
        
        # Create test networks
        net1 = WifiNetwork(
            ssid="SecureNetwork",
            bssid="aa:bb:cc:dd:ee:01",
            signal_dbm=-55,
            channel=6,
            band="2.4GHz",
            security="WPA2"
        )
        
        net2 = WifiNetwork(
            ssid="OpenNetwork",
            bssid="aa:bb:cc:dd:ee:02",
            signal_dbm=-50,
            channel=1,
            band="2.4GHz",
            security="OPEN"
        )
        
        networks = [net1, net2]
        
        score1 = score_network(networks, net1)
        score2 = score_network(networks, net2)
        
        # WPA2 network should score higher than OPEN even with weaker signal
        assert score1 > score2, f"WPA2 network ({score1}) should score higher than OPEN ({score2})"
        print(f"✓ Scoring works correctly: WPA2={score1:.1f}, OPEN={score2:.1f}")
        
        return True
    except Exception as e:
        print(f"✗ Scoring test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 60)
    print("Wi-Fi Scout Pro - Test Suite")
    print("=" * 60)
    
    all_passed = True
    
    if not test_imports():
        all_passed = False
    
    if not test_scanner_logic():
        all_passed = False
    
    if not test_data_models():
        all_passed = False
    
    if not test_scoring():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed!")
        print("\nYou can now run the application:")
        print("  python wa.py")
    else:
        print("✗ Some tests failed. Please check the errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
