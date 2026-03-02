"""
Utilities - Shared utility functions for Network Suite.

Includes command execution, validation, parsing, and security utilities.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import List, Optional, Tuple


# ==================== COMMAND EXECUTION ====================

def run_cmd(args: List[str], timeout: int = 20) -> Tuple[int, str, str]:
    """
    Run a system command safely.
    
    SECURITY: no shell=True; args passed as list.
    Returns (returncode, stdout, stderr).
    """
    if not args or not args[0]:
        raise ValueError("Command arguments cannot be empty")
    
    p = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    return p.returncode, p.stdout, p.stderr


# ==================== WIFI HELPERS ====================

def infer_band(freq_mhz: Optional[int], channel: Optional[int]) -> Optional[str]:
    """Infer WiFi band from frequency or channel."""
    if freq_mhz:
        if 2400 <= freq_mhz < 2500:
            return "2.4GHz"
        if 4900 <= freq_mhz < 5900:
            return "5GHz"
        if 5925 <= freq_mhz < 7125:
            return "6GHz"
    
    if channel is not None:
        if 1 <= channel <= 14:
            return "2.4GHz"
        if 32 <= channel <= 177:
            return "5GHz"
        if channel >= 1 and channel <= 233 and channel not in range(1, 15):
            return "6GHz"
    
    return None


def percent_to_dbm(pct: int) -> int:
    """Convert signal percentage to dBm (rough approximation)."""
    pct = max(0, min(100, pct))
    return int((pct / 2) - 100)


def compute_snr(signal_dbm: Optional[int], noise_dbm: Optional[int]) -> Optional[int]:
    """Compute Signal-to-Noise Ratio."""
    if signal_dbm is None or noise_dbm is None:
        return None
    return int(signal_dbm - noise_dbm)


def normalize_security(sec: str) -> str:
    """Normalize security type string."""
    s = (sec or "").strip().upper()
    if "WPA3" in s:
        return "WPA3"
    if "WPA2" in s:
        return "WPA2"
    if "WPA" in s:
        return "WPA"
    if "WEP" in s:
        return "WEP"
    if "OPEN" in s or "NONE" in s:
        return "OPEN"
    if not s:
        return "Unknown"
    return sec.strip()


# ==================== VALIDATION ====================

def validate_ssid(ssid: str) -> Tuple[bool, str]:
    """Validate SSID for security and spec compliance."""
    if not ssid:
        return False, "SSID cannot be empty"
    
    # Wi-Fi SSIDs are max 32 bytes (UTF-8)
    if len(ssid.encode('utf-8')) > 32:
        return False, "SSID too long (max 32 bytes)"
    
    # Check for control characters
    if any(ord(c) < 32 for c in ssid):
        return False, "SSID contains invalid control characters"
    
    return True, ""


def validate_password(password: str, security: str) -> Tuple[bool, str]:
    """Validate password based on security type."""
    if not password:
        return False, "Password cannot be empty"
    
    sec = normalize_security(security)
    
    if sec in ("WPA", "WPA2", "WPA3"):
        # WPA/WPA2/WPA3 requires 8-63 ASCII characters
        if len(password) < 8:
            return False, "WPA/WPA2/WPA3 password must be at least 8 characters"
        if len(password) > 63:
            return False, "WPA/WPA2/WPA3 password must be at most 63 characters"
    
    return True, ""


# ==================== ESCAPE UTILITIES ====================

def html_escape(text: object) -> str:
    """Escape text for safe HTML insertion."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def xml_escape(text: str) -> str:
    """Escape text for safe XML insertion."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def sanitize_for_log(text: str) -> str:
    """Sanitize text for safe logging (remove control characters and ANSI escapes)."""
    if not text:
        return ""
    # Remove control characters except newline and tab
    return ''.join(c if (ord(c) >= 32 or c in '\n\t') else '?' for c in text)


# ==================== SECURE FILE HANDLING ====================

def secure_delete_file(filepath: str, logger: logging.Logger) -> None:
    """Securely delete a file by overwriting before removal."""
    try:
        if os.path.exists(filepath):
            # Overwrite with random data
            file_size = os.path.getsize(filepath)
            with open(filepath, "wb") as f:
                f.write(os.urandom(file_size))
            # Now delete
            os.remove(filepath)
            logger.debug("Securely deleted: %s", filepath)
    except Exception as e:
        logger.warning("Could not securely delete %s: %s", filepath, e)


# ==================== FORMATTING ====================

def format_bytes(num_bytes: int) -> str:
    """Format bytes into human-readable format."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"
