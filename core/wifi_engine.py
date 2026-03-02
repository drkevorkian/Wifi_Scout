"""
WiFi Engine - Core WiFi scanning, scoring, and connection functionality.

Extracted from wa.py (WiFi Scout Pro) and adapted for modular architecture.
Supports Windows (netsh), Linux (nmcli), and macOS (airport) platforms.
"""

from __future__ import annotations

import logging
import os
import platform
import re
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Import utilities
import sys
sys.path.insert(0, str(Path(__file__).parent))

try:
    from utilities import (
        run_cmd, infer_band, percent_to_dbm, compute_snr, normalize_security,
        validate_ssid, validate_password, secure_delete_file, xml_escape
    )
except ImportError:
    # Fallback inline definitions if utilities not yet created
    def run_cmd(args: List[str], timeout: int = 20) -> Tuple[int, str, str]:
        """Run command and return (returncode, stdout, stderr)."""
        if not args or not args[0]:
            raise ValueError("Command arguments cannot be empty")
        p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    
    def infer_band(freq_mhz: Optional[int], channel: Optional[int]) -> Optional[str]:
        if freq_mhz:
            if 2400 <= freq_mhz < 2500: return "2.4GHz"
            if 4900 <= freq_mhz < 5900: return "5GHz"
            if 5925 <= freq_mhz < 7125: return "6GHz"
        if channel is not None:
            if 1 <= channel <= 14: return "2.4GHz"
            if 32 <= channel <= 177: return "5GHz"
        return None
    
    def percent_to_dbm(pct: int) -> int:
        return int((max(0, min(100, pct)) / 2) - 100)
    
    def compute_snr(signal_dbm: Optional[int], noise_dbm: Optional[int]) -> Optional[int]:
        if signal_dbm is None or noise_dbm is None: return None
        return int(signal_dbm - noise_dbm)
    
    def normalize_security(sec: str) -> str:
        s = (sec or "").strip().upper()
        if "WPA3" in s: return "WPA3"
        if "WPA2" in s: return "WPA2"
        if "WPA" in s: return "WPA"
        if "WEP" in s: return "WEP"
        if "OPEN" in s or "NONE" in s: return "OPEN"
        if not s: return "Unknown"
        return sec.strip()
    
    def validate_ssid(ssid: str) -> Tuple[bool, str]:
        if not ssid: return False, "SSID cannot be empty"
        if len(ssid.encode('utf-8')) > 32: return False, "SSID too long"
        if any(ord(c) < 32 for c in ssid): return False, "Invalid characters"
        return True, ""
    
    def validate_password(password: str, security: str) -> Tuple[bool, str]:
        if not password: return False, "Password cannot be empty"
        sec = normalize_security(security)
        if sec in ("WPA", "WPA2", "WPA3"):
            if len(password) < 8: return False, "Password must be at least 8 characters"
            if len(password) > 63: return False, "Password must be at most 63 characters"
        return True, ""
    
    def secure_delete_file(filepath: str, logger: logging.Logger) -> None:
        try:
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                with open(filepath, "wb") as f:
                    f.write(os.urandom(file_size))
                os.remove(filepath)
                logger.debug("Securely deleted: %s", filepath)
        except Exception as e:
            logger.warning("Could not securely delete %s: %s", filepath, e)
    
    def xml_escape(text: str) -> str:
        return (str(text).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


# Try to import PyQt6 for threading
try:
    from PyQt6.QtCore import QThread, pyqtSignal
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== TABLE COLUMNS ====================

COLUMNS = [
    ("SSID", "Network name"),
    ("BSSID", "Access point MAC address"),
    ("Signal (dBm)", "Signal strength in dBm (-30 excellent, -90 very weak)"),
    ("Signal (%)", "Signal strength as percentage"),
    ("Channel", "WiFi channel number"),
    ("Band", "Frequency band (2.4GHz, 5GHz, 6GHz)"),
    ("Security", "Encryption type (WPA3, WPA2, WPA, WEP, OPEN)"),
    ("Score", "Calculated quality score (higher is better)"),
    ("Status", "Connection status"),
]


# ==================== WINDOWS SCANNER ====================

def scan_windows_netsh(logger: logging.Logger) -> List:
    """Windows: netsh wlan show networks mode=bssid."""
    rc, out, err = run_cmd(["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=25)
    logger.debug("Windows netsh mode=bssid rc=%s", rc)
    
    if rc != 0 or not out.strip():
        rc2, out2, err2 = run_cmd(["netsh", "wlan", "show", "networks", "mode", "bssid"], timeout=25)
        logger.debug("Windows netsh mode bssid rc=%s", rc2)
        if rc2 == 0 and out2.strip():
            rc, out, err = rc2, out2, err2
        else:
            err_parts = [f"netsh wlan scan failed (exit code {rc})."]
            if err.strip():
                err_parts.append(f"Error: {err.strip()}")
            if out.strip():
                err_parts.append(f"Output: {out.strip()[:500]}")
            err_parts.append(
                "Common causes: (1) Wi-Fi is off or no adapter, "
                "(2) WLAN AutoConfig service stopped — run services.msc, find 'WLAN AutoConfig', set to Started, "
                "(3) Run this app as Administrator."
            )
            raise RuntimeError(" ".join(err_parts))

    # Import WifiNetwork from parent module to avoid duplication
    try:
        from network_suite import WifiNetwork
    except ImportError:
        # Fallback: define locally if network_suite not available
        from dataclasses import dataclass
        
        @dataclass
        class WifiNetwork:
            ssid: str
            bssid: str
            signal_dbm: Optional[int] = None
            signal_percent: Optional[int] = None
            noise_dbm: Optional[int] = None
            snr_db: Optional[int] = None
            channel: Optional[int] = None
            freq_mhz: Optional[int] = None
            band: Optional[str] = None
            security: str = "Unknown"
            auth_detail: str = ""
            source: str = ""
            score: Optional[float] = None
            score_breakdown: Optional[Dict[str, float]] = None
            notes: str = ""
            timestamp: Optional[float] = None
            is_connected: bool = False

    nets: List[WifiNetwork] = []
    current_ssid = ""
    current_auth = ""
    current_encrypt = ""
    current_bssid = ""
    current_signal_pct: Optional[int] = None
    current_channel: Optional[int] = None

    ssid_re = re.compile(r"^\s*SSID\s+\d+\s*:\s*(.*)\s*$")
    auth_re = re.compile(r"^\s*Authentication\s*:\s*(.*)\s*$", re.IGNORECASE)
    enc_re = re.compile(r"^\s*Encryption\s*:\s*(.*)\s*$", re.IGNORECASE)
    bssid_re = re.compile(r"^\s*BSSID\s+\d+\s*:\s*(.*)\s*$", re.IGNORECASE)
    sig_re = re.compile(r"^\s*Signal\s*:\s*(\d+)\s*%\s*$", re.IGNORECASE)
    ch_re = re.compile(r"^\s*Channel\s*:\s*(\d+)\s*$", re.IGNORECASE)

    for line in out.splitlines():
        m = ssid_re.match(line)
        if m:
            current_ssid = m.group(1).strip()
            current_auth = ""
            current_encrypt = ""
            continue
        m = auth_re.match(line)
        if m:
            current_auth = m.group(1).strip()
            continue
        m = enc_re.match(line)
        if m:
            current_encrypt = m.group(1).strip()
            continue
        m = bssid_re.match(line)
        if m:
            current_bssid = m.group(1).strip().lower()
            current_signal_pct = None
            current_channel = None
            continue
        m = sig_re.match(line)
        if m:
            current_signal_pct = int(m.group(1))
            continue
        m = ch_re.match(line)
        if m:
            current_channel = int(m.group(1))
            if current_ssid and current_bssid:
                sec = normalize_security(current_auth)
                dbm = percent_to_dbm(current_signal_pct) if current_signal_pct is not None else None
                nets.append(
                    WifiNetwork(
                        ssid=current_ssid,
                        bssid=current_bssid,
                        signal_dbm=dbm,
                        signal_percent=current_signal_pct,
                        channel=current_channel,
                        band=infer_band(None, current_channel),
                        security=sec,
                        auth_detail=f"{current_auth}/{current_encrypt}",
                        source="netsh",
                        timestamp=time.time()
                    )
                )
            current_bssid = ""
            current_signal_pct = None
            current_channel = None

    logger.info("Windows scan found %d BSSID entries", len(nets))
    return nets


# ==================== LINUX SCANNER ====================

def scan_linux_nmcli(logger: logging.Logger) -> List:
    """Linux: nmcli dev wifi list."""
    rc, out, err = run_cmd(["nmcli", "-t", "-f", "SSID,BSSID,MODE,CHAN,FREQ,RATE,SIGNAL,SECURITY", "dev", "wifi", "list"], timeout=20)
    if rc != 0:
        raise RuntimeError(f"nmcli failed (rc={rc}). {err.strip()}")

    # Import WifiNetwork from parent module to avoid duplication
    try:
        from network_suite import WifiNetwork
    except ImportError:
        # Fallback: define locally if network_suite not available
        from dataclasses import dataclass
        
        @dataclass
        class WifiNetwork:
            ssid: str
            bssid: str
            signal_dbm: Optional[int] = None
            signal_percent: Optional[int] = None
            noise_dbm: Optional[int] = None
            snr_db: Optional[int] = None
            channel: Optional[int] = None
            freq_mhz: Optional[int] = None
            band: Optional[str] = None
            security: str = "Unknown"
            auth_detail: str = ""
            source: str = ""
            score: Optional[float] = None
            score_breakdown: Optional[Dict[str, float]] = None
            notes: str = ""
            timestamp: Optional[float] = None
            is_connected: bool = False

    nets: List[WifiNetwork] = []
    for line in out.splitlines():
        fields = line.split(":")
        if len(fields) < 8:
            continue
        ssid, bssid, mode, chan_str, freq_str, rate, signal_str, security = fields[:8]
        if mode.strip().upper() != "INFRA":
            continue
        
        bssid = bssid.strip().lower()
        if not bssid or bssid == "--":
            continue
        
        try:
            signal_pct = int(signal_str.strip())
        except ValueError:
            signal_pct = None
        
        try:
            channel = int(chan_str.strip())
        except ValueError:
            channel = None
        
        try:
            freq = int(freq_str.strip().split()[0])
        except ValueError:
            freq = None
        
        dbm = percent_to_dbm(signal_pct) if signal_pct is not None else None
        nets.append(
            WifiNetwork(
                ssid=ssid.strip() or "(hidden)",
                bssid=bssid,
                signal_dbm=dbm,
                signal_percent=signal_pct,
                channel=channel,
                freq_mhz=freq,
                band=infer_band(freq, channel),
                security=normalize_security(security.strip()),
                source="nmcli",
                timestamp=time.time()
            )
        )
    
    logger.info("Linux scan found %d BSSID entries", len(nets))
    return nets


# ==================== MACOS SCANNER ====================

def get_macos_wifi_interface(logger: logging.Logger) -> str:
    """
    Detect the macOS Wi-Fi interface dynamically.
    Returns interface name (e.g., 'en0', 'en1') or raises RuntimeError if not found.
    """
    try:
        rc, out, err = run_cmd(["networksetup", "-listallhardwareports"], timeout=10)
        if rc != 0:
            raise RuntimeError(f"networksetup failed: {err}")
        
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if "Wi-Fi" in line or "AirPort" in line:
                if i + 1 < len(lines):
                    device_line = lines[i + 1]
                    match = re.search(r"Device:\s*(\S+)", device_line, re.IGNORECASE)
                    if match:
                        iface = match.group(1)
                        logger.debug("Detected macOS Wi-Fi interface: %s", iface)
                        return iface
        
        logger.warning("No Wi-Fi interface found, defaulting to en0")
        return "en0"
    
    except Exception as e:
        logger.warning("Failed to detect Wi-Fi interface: %s, defaulting to en0", e)
        return "en0"


def scan_macos_airport(logger: logging.Logger) -> List:
    """macOS: airport -s."""
    airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    if not os.path.exists(airport_path):
        raise RuntimeError(f"airport not found at {airport_path}")

    rc, out, err = run_cmd([airport_path, "-s"], timeout=20)
    if rc != 0:
        raise RuntimeError(f"airport failed (rc={rc}). {err.strip()}")

    # Import WifiNetwork from parent module to avoid duplication
    try:
        from network_suite import WifiNetwork
    except ImportError:
        # Fallback: define locally if network_suite not available
        from dataclasses import dataclass
        
        @dataclass
        class WifiNetwork:
            ssid: str
            bssid: str
            signal_dbm: Optional[int] = None
            signal_percent: Optional[int] = None
            noise_dbm: Optional[int] = None
            snr_db: Optional[int] = None
            channel: Optional[int] = None
            freq_mhz: Optional[int] = None
            band: Optional[str] = None
            security: str = "Unknown"
            auth_detail: str = ""
            source: str = ""
            score: Optional[float] = None
            score_breakdown: Optional[Dict[str, float]] = None
            notes: str = ""
            timestamp: Optional[float] = None
            is_connected: bool = False

    nets: List[WifiNetwork] = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 7:
            continue
        
        ssid = parts[0].strip()
        bssid = parts[1].strip().lower()
        
        try:
            rssi = int(parts[2])
        except ValueError:
            rssi = None
        
        try:
            channel_str = parts[3].strip()
            channel = int(channel_str.split(",")[0])
        except (ValueError, IndexError):
            channel = None
        
        security = " ".join(parts[6:]) if len(parts) > 6 else "Unknown"
        
        nets.append(
            WifiNetwork(
                ssid=ssid,
                bssid=bssid,
                signal_dbm=rssi,
                channel=channel,
                band=infer_band(None, channel),
                security=normalize_security(security),
                source="airport",
                timestamp=time.time()
            )
        )
    
    logger.info("macOS scan found %d BSSID entries", len(nets))
    return nets


# ==================== MAIN SCAN FUNCTION ====================

def scan_wifi(logger: logging.Logger) -> List:
    """Cross-platform WiFi scan."""
    system = platform.system()
    logger.info(f"Scanning Wi-Fi on {system}...")
    
    if system == "Windows":
        return scan_windows_netsh(logger)
    elif system == "Linux":
        return scan_linux_nmcli(logger)
    elif system == "Darwin":
        return scan_macos_airport(logger)
    else:
        raise RuntimeError(f"Unsupported platform: {system}")


# ==================== CONNECTION STATUS ====================

def get_connected_bssid(logger: logging.Logger) -> Optional[str]:
    """Get currently connected BSSID."""
    system = platform.system()
    
    try:
        if system == "Windows":
            rc, out, err = run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=10)
            if rc == 0:
                for line in out.splitlines():
                    if line.strip().startswith("BSSID"):
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip().lower()
        
        elif system == "Linux":
            rc, out, err = run_cmd(["nmcli", "-t", "-f", "BSSID", "dev", "wifi"], timeout=10)
            if rc == 0 and out.strip():
                lines = out.strip().splitlines()
                if lines:
                    bssid = lines[0].strip().lower()
                    if bssid and bssid != "--":
                        return bssid
        
        elif system == "Darwin":
            iface = get_macos_wifi_interface(logger)
            airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            rc, out, err = run_cmd([airport_path, "-I"], timeout=10)
            if rc == 0:
                for line in out.splitlines():
                    if "BSSID" in line or "bssid" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip().lower()
    
    except Exception as e:
        logger.debug("Failed to get connected BSSID: %s", e)
    
    return None


def mark_connected_and_enrich(logger: logging.Logger, networks: List) -> Optional[str]:
    """Mark connected network and return connected BSSID."""
    connected_bssid = get_connected_bssid(logger)
    
    if connected_bssid:
        logger.debug(f"Connected BSSID: {connected_bssid}")
        for net in networks:
            if net.bssid.lower() == connected_bssid:
                net.is_connected = True
                logger.info(f"Marked connected: {net.ssid}")
                break
    
    return connected_bssid


# ==================== SCORING ALGORITHM ====================

def calculate_channel_congestion(networks: List, target_channel: Optional[int], target_band: Optional[str]) -> int:
    """Calculate channel congestion."""
    if target_channel is None:
        return 0
    
    count = 0
    for n in networks:
        if n.channel == target_channel and n.band == target_band:
            count += 1
    
    return count


def score_network(networks: List, network, allow_open: bool = False) -> float:
    """Score a network based on multiple factors."""
    score = 100.0
    breakdown = {}
    
    # Security scoring
    sec = network.security
    if sec == "WPA3":
        sec_points = 20.0
    elif sec == "WPA2":
        sec_points = 15.0
    elif sec == "WPA":
        sec_points = 5.0
    elif sec == "WEP":
        sec_points = -10.0
    elif sec == "OPEN":
        sec_points = -30.0 if not allow_open else 0.0
    else:
        sec_points = 0.0
    
    score += sec_points
    breakdown["security"] = sec_points
    
    # Signal scoring
    if network.signal_dbm is not None:
        sig = network.signal_dbm
        if sig >= -50:
            sig_points = 30.0
        elif sig >= -60:
            sig_points = 20.0
        elif sig >= -70:
            sig_points = 10.0
        elif sig >= -80:
            sig_points = 0.0
        else:
            sig_points = -20.0
        
        score += sig_points
        breakdown["signal"] = sig_points
    
    # Band bonus
    if network.band == "5GHz":
        band_bonus = 10.0
    elif network.band == "6GHz":
        band_bonus = 15.0
    else:
        band_bonus = 0.0
    
    score += band_bonus
    breakdown["band"] = band_bonus
    
    # Channel congestion penalty (capped)
    congestion = calculate_channel_congestion(networks, network.channel, network.band)
    cong_penalty = min(congestion * 3.0, 25.0)
    score -= cong_penalty
    breakdown["congestion"] = -cong_penalty
    
    # SNR bonus
    if network.snr_db is not None:
        if network.snr_db >= 40:
            snr_bonus = 10.0
        elif network.snr_db >= 25:
            snr_bonus = 5.0
        else:
            snr_bonus = 0.0
        
        score += snr_bonus
        breakdown["snr"] = snr_bonus
    
    network.score_breakdown = breakdown
    return max(0.0, score)


def pick_best(networks: List):
    """Pick the best network based on score."""
    if not networks:
        return None
    
    valid = [n for n in networks if n.score is not None and n.score > 0]
    if not valid:
        return None
    
    return max(valid, key=lambda n: n.score)


# ==================== CONNECTION ====================

def connect_to_network(ssid: str, password: Optional[str], logger: logging.Logger) -> Tuple[bool, str]:
    """Connect to a WiFi network."""
    # Validate SSID
    valid, msg = validate_ssid(ssid)
    if not valid:
        return False, f"Invalid SSID: {msg}"
    
    system = platform.system()
    
    try:
        if system == "Windows":
            # Create temporary XML profile with secure permissions from creation
            temp_dir = tempfile.gettempdir()
            profile_name = f"wifi_profile_{uuid.uuid4().hex}.xml"
            profile_path = os.path.join(temp_dir, profile_name)
            
            try:
                # Create file with restrictive permissions BEFORE writing (prevents race condition)
                fd = os.open(profile_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
                
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    if password:
                        xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{xml_escape(ssid)}</name>
    <SSIDConfig>
        <SSID>
            <name>{xml_escape(ssid)}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{xml_escape(password)}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
                    else:
                        xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{xml_escape(ssid)}</name>
    <SSIDConfig>
        <SSID>
            <name>{xml_escape(ssid)}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>"""
                    
                    f.write(xml_content)
                
                # Add profile
                rc, out, err = run_cmd(["netsh", "wlan", "add", "profile", f"filename={profile_path}"], timeout=10)
                if rc != 0:
                    return False, f"Failed to add profile: {err.strip()}"
                
                # Connect
                rc, out, err = run_cmd(["netsh", "wlan", "connect", f"name={ssid}"], timeout=15)
                if rc != 0:
                    return False, f"Failed to connect: {err.strip()}"
                
                logger.info(f"Connected to {ssid}")
                return True, f"Successfully connected to {ssid}"
            
            finally:
                secure_delete_file(profile_path, logger)
        
        elif system == "Linux":
            if password:
                rc, out, err = run_cmd(["nmcli", "dev", "wifi", "connect", ssid, "password", password], timeout=20)
            else:
                rc, out, err = run_cmd(["nmcli", "dev", "wifi", "connect", ssid], timeout=20)
            
            if rc != 0:
                return False, f"Connection failed: {err.strip()}"
            
            logger.info(f"Connected to {ssid}")
            return True, f"Successfully connected to {ssid}"
        
        elif system == "Darwin":
            iface = get_macos_wifi_interface(logger)
            
            if password:
                rc, out, err = run_cmd(["networksetup", "-setairportnetwork", iface, ssid, password], timeout=20)
            else:
                rc, out, err = run_cmd(["networksetup", "-setairportnetwork", iface, ssid], timeout=20)
            
            if rc != 0:
                return False, f"Connection failed: {err.strip()}"
            
            logger.info(f"Connected to {ssid}")
            return True, f"Successfully connected to {ssid}"
        
        else:
            return False, f"Unsupported platform: {system}"
    
    except Exception as e:
        logger.error("Connection error: %s", e, exc_info=True)
        return False, f"Error: {str(e)}"


# ==================== SCAN THREAD ====================

if HAS_PYQT6:
    class ScanThread(QThread):
        """Background WiFi scan thread."""
        scan_complete = pyqtSignal(list)
        scan_error = pyqtSignal(str)
        
        def __init__(self, logger: logging.Logger):
            super().__init__()
            self.logger = logger
        
        def run(self):
            """Run scan in background."""
            try:
                networks = scan_wifi(self.logger)
                self.scan_complete.emit(networks)
            except Exception as e:
                self.logger.error("Background scan failed", exc_info=True)
                self.scan_error.emit(str(e))
