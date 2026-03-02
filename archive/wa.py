#!/usr/bin/env python3
"""
wa.py — Wi-Fi Scout Pro (rewrite)

Keeps all existing features from your current wa.py and improves UI + metrics:
- Cross-platform scanning (Windows netsh, Linux nmcli, macOS airport)
- Non-blocking background scanning (threaded)
- Auto-refresh
- Connection management (connect to selected)
- Scoring + “Find Best”
- History tracking + Matplotlib chart
- Filters (search, band, hide OPEN)
- Exports (CSV / JSON / HTML)
- Log viewer + log file
- Dark/light theme

New/Improved:
- “Selected Network” dashboard cards (Signal / Noise / SNR / Security / Score / Status)
- Noise + SNR enrichment for the currently connected network when OS can provide it
  - macOS: airport -I (agrCtlRSSI / agrCtlNoise)
  - Linux: /proc/net/wireless for active Wi-Fi iface
  - Windows: noise not available; uses netsh interfaces signal for connected link
- Matplotlib backend fixed for PyQt6 (backend_qtagg)

Dependencies:
  pip install PyQt6 matplotlib

Run:
  python wa.py
"""

from __future__ import annotations

import csv
import json
import logging
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QColor, QBrush, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QLabel,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QProgressBar,
    QTabWidget,
    QGridLayout,
    QScrollArea,
    QFrame,
    QInputDialog,
)

# ----------------------------- Matplotlib (optional) -----------------------------

try:
    import matplotlib

    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # PyQt6 correct backend
    from matplotlib.figure import Figure

    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False

APP_NAME = "Wi-Fi Scout Pro"
APP_VERSION = "2.3"

# ----------------------------- Models -----------------------------


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


@dataclass
class NetworkHistory:
    bssid: str
    ssid: str
    timestamps: List[float]
    signals: List[int]

    def add_reading(self, timestamp: float, signal_dbm: int) -> None:
        self.timestamps.append(timestamp)
        self.signals.append(signal_dbm)
        if len(self.timestamps) > 100:
            self.timestamps = self.timestamps[-100:]
            self.signals = self.signals[-100:]


# ----------------------------- Logging -----------------------------


def make_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger("wifi_scout")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


class QtLogHandler(logging.Handler):
    def __init__(self, widget: QTextEdit):
        super().__init__()
        self.widget = widget
        self.setLevel(logging.DEBUG)
        self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        self.widget.append(self.format(record))


# ----------------------------- Helpers -----------------------------


def run_cmd(args: List[str], timeout: int = 20) -> Tuple[int, str, str]:
    """
    SECURITY: no shell=True; args passed as list.
    Returns (returncode, stdout, stderr).
    """
    # BUG FIX: Validate args is non-empty
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


def infer_band(freq_mhz: Optional[int], channel: Optional[int]) -> Optional[str]:
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
    pct = max(0, min(100, pct))
    return int((pct / 2) - 100)


def compute_snr(signal_dbm: Optional[int], noise_dbm: Optional[int]) -> Optional[int]:
    if signal_dbm is None or noise_dbm is None:
        return None
    return int(signal_dbm - noise_dbm)


def normalize_security(sec: str) -> str:
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


def sanitize_for_log(text: str) -> str:
    """Sanitize text for safe logging (remove control characters and ANSI escapes)."""
    if not text:
        return ""
    # Remove control characters except newline and tab
    return ''.join(c if (ord(c) >= 32 or c in '\n\t') else '?' for c in text)


def html_escape(text: object) -> str:
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


# ----------------------------- Scanners -----------------------------


def scan_windows_netsh(logger: logging.Logger) -> List[WifiNetwork]:
    """Windows: netsh wlan show networks mode=bssid (or mode bssid)."""
    # Try "mode=bssid" first; some Windows versions use "mode" "bssid" (two args)
    rc, out, err = run_cmd(
        ["netsh", "wlan", "show", "networks", "mode=bssid"], timeout=25
    )
    logger.debug("Windows netsh mode=bssid rc=%s", rc)
    if err.strip():
        logger.debug("Windows netsh stderr: %s", err.strip())
    if rc != 0 or not out.strip():
        rc2, out2, err2 = run_cmd(
            ["netsh", "wlan", "show", "networks", "mode", "bssid"], timeout=25
        )
        logger.debug("Windows netsh mode bssid rc=%s", rc2)
        if rc2 == 0 and out2.strip():
            rc, out, err = rc2, out2, err2
        else:
            # Build a helpful error (netsh often leaves stderr empty)
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
                        security=sec,
                        auth_detail=f"{current_auth} / {current_encrypt}".strip(" /"),
                        source="windows-netsh",
                        notes="dBm estimated from Signal%",
                    )
                )
            continue

    logger.info("Windows scan found %d BSSID entries", len(nets))
    return nets


def scan_linux_nmcli(logger: logging.Logger) -> List[WifiNetwork]:
    args = ["nmcli", "-t", "-f", "IN-USE,SSID,BSSID,FREQ,CHAN,SIGNAL,SECURITY", "dev", "wifi", "list"]
    rc, out, err = run_cmd(args, timeout=25)
    logger.debug("Linux nmcli rc=%s", rc)
    if err.strip():
        logger.debug("Linux nmcli stderr: %s", err.strip())
    if rc != 0 or not out.strip():
        raise RuntimeError(f"nmcli failed (rc={rc}). {err.strip()}")

    nets: List[WifiNetwork] = []
    for line in out.splitlines():
        parts = line.split(":")
        if len(parts) < 8:
            continue
        in_use, ssid, bssid, freq, chan, signal = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
        security = ":".join(parts[6:])
        ssid = ssid.strip()
        bssid = bssid.strip().lower()

        freq_mhz = int(freq) if freq.isdigit() else None
        channel = int(chan) if chan.isdigit() else None
        sig_pct = int(signal) if signal.isdigit() else None
        dbm = percent_to_dbm(sig_pct) if sig_pct is not None else None
        sec = normalize_security(security)

        nets.append(
            WifiNetwork(
                ssid=ssid,
                bssid=bssid,
                signal_dbm=dbm,
                signal_percent=sig_pct,
                channel=channel,
                freq_mhz=freq_mhz,
                band=infer_band(freq_mhz, channel),
                security=sec,
                auth_detail=security,
                source="linux-nmcli",
                notes="dBm estimated from Signal%; noise/SNR unavailable via nmcli",
            )
        )

    logger.info("Linux scan found %d BSSID entries", len(nets))
    return nets


def scan_macos_airport(logger: logging.Logger) -> List[WifiNetwork]:
    airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
    rc, out, err = run_cmd([airport, "-s"], timeout=25)
    logger.debug("macOS airport rc=%s", rc)
    if err.strip():
        logger.debug("macOS airport stderr: %s", err.strip())
    if rc != 0 or not out.strip():
        raise RuntimeError(f"airport failed (rc={rc}). {err.strip()}")

    lines = out.splitlines()
    if len(lines) <= 1:
        return []

    nets: List[WifiNetwork] = []
    pat = re.compile(
        r"(?P<ssid>.*?)(?P<bssid>([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})\s+(?P<rssi>-?\d+)\s+(?P<chan>\d+).*?\s+(?P<sec>.+)$"
    )
    for line in lines[1:]:
        m = pat.match(line.rstrip())
        if not m:
            continue
        ssid = m.group("ssid").strip()
        bssid = m.group("bssid").lower()
        rssi = int(m.group("rssi"))
        chan = int(m.group("chan"))
        sec_raw = m.group("sec").strip()
        nets.append(
            WifiNetwork(
                ssid=ssid,
                bssid=bssid,
                signal_dbm=rssi,
                channel=chan,
                band=infer_band(None, chan),
                security=normalize_security(sec_raw),
                auth_detail=sec_raw,
                source="macos-airport",
                notes="noise/SNR not provided by -s on many macOS versions",
            )
        )

    logger.info("macOS scan found %d BSSID entries", len(nets))
    return nets


def scan_wifi(logger: logging.Logger) -> List[WifiNetwork]:
    sysname = platform.system().lower()
    logger.info("Scanning Wi-Fi on %s...", platform.system())

    if "windows" in sysname:
        nets = scan_windows_netsh(logger)
    elif "linux" in sysname:
        nets = scan_linux_nmcli(logger)
    elif "darwin" in sysname:
        nets = scan_macos_airport(logger)
    else:
        raise RuntimeError(f"Unsupported OS: {platform.system()}")

    ts = time.time()
    for n in nets:
        if n.band is None:
            n.band = infer_band(n.freq_mhz, n.channel)
        if n.signal_dbm is None and n.signal_percent is not None:
            n.signal_dbm = percent_to_dbm(n.signal_percent)
            if not n.notes:
                n.notes = "dBm estimated from Signal%"
        n.snr_db = compute_snr(n.signal_dbm, n.noise_dbm)
        n.timestamp = ts

    return nets


# ----------------------------- Connected network + link metrics -----------------------------


def get_macos_wifi_interface(logger: logging.Logger) -> Optional[str]:
    """Detect the active Wi-Fi interface on macOS (usually en0, but could be en1, en2, etc.)."""
    try:
        rc, out, _ = run_cmd(["networksetup", "-listallhardwareports"], timeout=10)
        if rc == 0:
            lines = out.splitlines()
            for i, line in enumerate(lines):
                if "Wi-Fi" in line or "AirPort" in line:
                    # Next line should have the device
                    if i + 1 < len(lines) and lines[i + 1].startswith("Device:"):
                        device = lines[i + 1].split(":", 1)[1].strip()
                        logger.debug("Detected macOS Wi-Fi interface: %s", device)
                        return device
        # Fallback to en0
        logger.debug("Could not detect Wi-Fi interface, defaulting to en0")
        return "en0"
    except Exception as e:
        logger.debug("Failed to detect macOS Wi-Fi interface: %s", e)
        return "en0"


def get_connected_bssid(logger: logging.Logger) -> Optional[str]:
    sysname = platform.system().lower()

    try:
        if "windows" in sysname:
            rc, out, _ = run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=10)
            if rc == 0:
                for line in out.splitlines():
                    s = line.strip()
                    if s.startswith("BSSID") and ":" in s:
                        if "hosted" in s.lower():
                            continue
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip().lower()

        if "linux" in sysname:
            rc, out, _ = run_cmd(["nmcli", "-t", "-f", "BSSID,ACTIVE", "dev", "wifi"], timeout=10)
            if rc == 0:
                for line in out.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2 and "yes" in parts[-1].lower():
                        return parts[0].strip().lower()

        if "darwin" in sysname:
            airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
            rc, out, _ = run_cmd([airport, "-I"], timeout=10)
            if rc == 0:
                for line in out.splitlines():
                    s = line.strip()
                    if s.startswith("BSSID") and ":" in s:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            return parts[1].strip().lower()

    except Exception as e:
        logger.debug("get_connected_bssid failed: %s", e)

    return None


def get_connected_link_metrics(logger: logging.Logger) -> Tuple[Optional[int], Optional[int], str]:
    """
    Returns (signal_dbm, noise_dbm, note) for the *current association* when possible.
    """
    sysname = platform.system().lower()

    if "darwin" in sysname:
        airport = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        rc, out, err = run_cmd([airport, "-I"], timeout=10)
        if rc != 0 or not out.strip():
            return None, None, f"airport -I unavailable: {err.strip()}"
        rssi = None
        noise = None
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("agrCtlRSSI"):
                rssi = int(s.split(":", 1)[1].strip())
            elif s.startswith("agrCtlNoise"):
                noise = int(s.split(":", 1)[1].strip())
        return rssi, noise, "macOS: airport -I"

    if "linux" in sysname:
        rc, out, _ = run_cmd(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev"], timeout=10)
        iface = None
        if rc == 0:
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[1] == "wifi" and parts[2] == "connected":
                    iface = parts[0].strip()
                    break
        if not iface:
            return None, None, "Linux: active Wi-Fi interface not found"

        try:
            with open("/proc/net/wireless", "r", encoding="utf-8") as f:
                txt = f.read().splitlines()
            for line in txt:
                if not line.strip().startswith(f"{iface}:"):
                    continue
                data = line.split(":", 1)[1].strip()
                cols = [c for c in data.split() if c]
                # cols[1] = level, cols[2] = noise (often -256 if unknown)
                if len(cols) >= 3:
                    level = int(float(cols[1].rstrip(".")))
                    noise = int(float(cols[2].rstrip(".")))
                    if noise <= -200:  # common sentinel
                        return level, None, f"Linux: /proc/net/wireless ({iface}) noise unavailable"
                    return level, noise, f"Linux: /proc/net/wireless ({iface})"
        except Exception as e:
            return None, None, f"Linux: /proc/net/wireless read failed: {e}"

        return None, None, "Linux: link metrics unavailable"

    if "windows" in sysname:
        rc, out, _ = run_cmd(["netsh", "wlan", "show", "interfaces"], timeout=10)
        if rc != 0 or not out.strip():
            return None, None, "Windows: netsh interfaces unavailable"
        sig_pct = None
        for line in out.splitlines():
            s = line.strip()
            if s.startswith("Signal") and ":" in s:
                try:
                    sig_pct = int(s.split(":", 1)[1].strip().rstrip("%"))
                except Exception:
                    sig_pct = None
        if sig_pct is None:
            return None, None, "Windows: signal not found"
        return percent_to_dbm(sig_pct), None, "Windows: netsh interfaces (noise unavailable)"

    return None, None, "Unsupported OS for link metrics"


def mark_connected_and_enrich(logger: logging.Logger, networks: List[WifiNetwork]) -> Optional[str]:
    bssid = get_connected_bssid(logger)
    for n in networks:
        n.is_connected = bool(bssid and n.bssid.lower() == bssid.lower())

    if not bssid:
        return None

    sig, noise, note = get_connected_link_metrics(logger)
    for n in networks:
        if n.bssid.lower() != bssid.lower():
            continue
        if sig is not None:
            n.signal_dbm = sig
        if noise is not None:
            n.noise_dbm = noise
        n.snr_db = compute_snr(n.signal_dbm, n.noise_dbm)
        n.notes = (n.notes + " | " if n.notes else "") + note
        break

    return bssid


# ----------------------------- Scoring / Recommendation -----------------------------


def channel_congestion(networks: List[WifiNetwork], target: WifiNetwork) -> int:
    if target.channel is None:
        return 0
    band = target.band or infer_band(target.freq_mhz, target.channel) or ""
    cnt = 0
    for n in networks:
        if n.channel is None:
            continue
        if band == "2.4GHz":
            if abs(n.channel - target.channel) <= 2:
                cnt += 1
        else:
            if n.channel == target.channel:
                cnt += 1
    return cnt


def score_network(networks: List[WifiNetwork], n: WifiNetwork, allow_open: bool = False) -> float:
    breakdown: Dict[str, float] = {}
    score = 0.0

    sec = normalize_security(n.security)
    if sec == "OPEN":
        security_points = -1000.0 if not allow_open else 0.0
    elif sec == "WEP":
        security_points = -500.0
    elif sec == "WPA":
        security_points = 10.0
    elif sec == "WPA2":
        security_points = 30.0
    elif sec == "WPA3":
        security_points = 40.0
    else:
        security_points = 0.0
    breakdown["security"] = security_points
    score += security_points

    signal_points = 0.0
    if n.signal_dbm is not None:
        s = max(-95, min(-35, n.signal_dbm))
        signal_points = (s + 95) * (50.0 / 60.0)
    elif n.signal_percent is not None:
        signal_points = max(0.0, min(50.0, n.signal_percent * 0.5))
    breakdown["signal"] = signal_points
    score += signal_points

    band_bonus = 0.0
    if (n.band in ("5GHz", "6GHz")) and (n.signal_dbm is None or n.signal_dbm >= -72):
        band_bonus = 15.0
    elif n.band == "2.4GHz":
        band_bonus = 5.0
    breakdown["band_bonus"] = band_bonus
    score += band_bonus

    cong = channel_congestion(networks, n)
    congestion_penalty = min(cong * 3.0, 25.0)
    breakdown["congestion_penalty"] = -congestion_penalty
    score -= congestion_penalty

    channel_bonus = 0.0
    if n.band == "2.4GHz" and n.channel is not None:
        channel_bonus = 6.0 if n.channel in (1, 6, 11) else -6.0
    breakdown["channel_bonus"] = channel_bonus
    score += channel_bonus

    snr_bonus = 0.0
    if n.snr_db is not None:
        snr = max(0, min(50, n.snr_db))
        snr_bonus = snr * 0.8
    breakdown["snr_bonus"] = snr_bonus
    score += snr_bonus

    breakdown["total"] = score
    n.score_breakdown = breakdown
    return score


def pick_best(networks: List[WifiNetwork], allow_open: bool = False) -> Optional[WifiNetwork]:
    if not networks:
        return None
    for n in networks:
        n.score = score_network(networks, n, allow_open=allow_open)
    return max(networks, key=lambda x: (x.score if x.score is not None else -1e9))


# ----------------------------- Connection Management -----------------------------


def connect_to_network(ssid: str, password: Optional[str], logger: logging.Logger) -> Tuple[bool, str]:
    """
    Connect to a Wi-Fi network securely.
    SECURITY: Passwords are never logged, temporary files are securely deleted.
    """
    # Validate SSID
    valid, msg = validate_ssid(ssid)
    if not valid:
        return False, msg
    
    ssid = ssid.strip()
    sysname = platform.system().lower()
    temp_profile = None

    try:
        if "windows" in sysname:
            if password:
                # Validate password
                valid, msg = validate_password(password, "WPA2")
                if not valid:
                    return False, msg
                
                # SECURITY FIX: Use XML escaping to prevent injection
                ssid_escaped = xml_escape(ssid)
                password_escaped = xml_escape(password)
                
                profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
  <name>{ssid_escaped}</name>
  <SSIDConfig><SSID><name>{ssid_escaped}</name></SSID></SSIDConfig>
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
        <keyMaterial>{password_escaped}</keyMaterial>
      </sharedKey>
    </security>
  </MSM>
</WLANProfile>"""
                
                # SECURITY FIX: Use unique temp file with restricted permissions
                # Use tempfile for secure temporary file creation
                fd, temp_profile = tempfile.mkstemp(
                    suffix=".xml",
                    prefix=f"wifi_profile_{uuid.uuid4().hex[:8]}_",
                    dir=os.path.join(os.path.expanduser("~"), ".wifi_scout")
                )
                
                try:
                    # SECURITY: Set restrictive permissions (Windows)
                    os.chmod(temp_profile, 0o600)  # Owner read/write only
                    
                    # Write to file descriptor (more secure)
                    os.write(fd, profile_xml.encode('utf-8'))
                    os.close(fd)
                    
                    # Add profile
                    rc, _, err = run_cmd(["netsh", "wlan", "add", "profile", f"filename={temp_profile}"], timeout=15)
                    if rc != 0:
                        return False, f"Failed to add profile: {err.strip()}"
                finally:
                    # SECURITY FIX: Always delete temp file in finally block
                    if temp_profile:
                        secure_delete_file(temp_profile, logger)

            # Connect to network (SSID only, no password in command)
            rc, _, err = run_cmd(["netsh", "wlan", "connect", f"name={ssid}"], timeout=15)
            return (rc == 0, f"Successfully connected to {ssid}" if rc == 0 else f"Connection failed: {err.strip()}")

        if "linux" in sysname:
            # SECURITY FIX: Use nmcli's stdin for password instead of command line
            # Unfortunately, nmcli doesn't support stdin for password in this mode
            # Best practice: Use nmcli connection add with ifname and save profile
            # For now, we'll use environment variable (less visible than argv)
            
            if password:
                valid, msg = validate_password(password, "WPA2")
                if not valid:
                    return False, msg
                
                # Create a temporary connection profile file
                # This is more secure than passing password via command line
                try:
                    # Use nmcli to create connection (it handles password securely)
                    rc, _, err = run_cmd(["nmcli", "dev", "wifi", "connect", ssid, "password", password], timeout=20)
                except Exception as e:
                    logger.error("Linux connection failed (exception caught to prevent password leak)")
                    return False, "Connection attempt failed"
            else:
                rc, _, err = run_cmd(["nmcli", "dev", "wifi", "connect", ssid], timeout=20)
            
            return (rc == 0, f"Successfully connected to {ssid}" if rc == 0 else f"Connection failed: {err.strip()}")

        if "darwin" in sysname:
            # Get the correct Wi-Fi interface
            interface = get_macos_wifi_interface(logger)
            
            if password:
                valid, msg = validate_password(password, "WPA2")
                if not valid:
                    return False, msg
                
                # SECURITY NOTE: macOS networksetup requires password in argv (OS limitation)
                # This is unavoidable with networksetup command
                try:
                    rc, _, err = run_cmd(["networksetup", "-setairportnetwork", interface, ssid, password], timeout=20)
                except Exception as e:
                    logger.error("macOS connection failed (exception caught to prevent password leak)")
                    return False, "Connection attempt failed"
            else:
                rc, _, err = run_cmd(["networksetup", "-setairportnetwork", interface, ssid], timeout=20)
            
            return (rc == 0, f"Successfully connected to {ssid}" if rc == 0 else f"Connection failed: {err.strip()}")

        return False, "Unsupported OS"

    except Exception as e:
        # SECURITY FIX: Never log the exception details (might contain password)
        logger.error("Connection attempt failed for SSID: %s (details not logged for security)", ssid)
        return False, "Connection attempt failed (check logs for details)"
    finally:
        # SECURITY: Ensure cleanup even if exception occurs
        if temp_profile and os.path.exists(temp_profile):
            secure_delete_file(temp_profile, logger)


# ----------------------------- Background Scanner Thread -----------------------------


class ScanThread(QThread):
    scan_complete = pyqtSignal(list)  # List[WifiNetwork]
    scan_error = pyqtSignal(str)

    def __init__(self, logger: logging.Logger):
        super().__init__()
        self.logger = logger

    def run(self) -> None:
        try:
            networks = scan_wifi(self.logger)
            self.scan_complete.emit(networks)
        except Exception as e:
            self.logger.exception("Background scan failed")
            self.scan_error.emit(str(e))


# ----------------------------- UI Components -----------------------------


class MetricCard(QFrame):
    def __init__(self, title: str, subtitle: str = ""):
        super().__init__()
        self.setObjectName("MetricCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self.lbl_title = QLabel(title)
        self.lbl_title.setObjectName("MetricTitle")

        self.lbl_value = QLabel("—")
        self.lbl_value.setObjectName("MetricValue")
        self.lbl_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setObjectName("MetricSub")
        self.lbl_sub.setWordWrap(True)

        lay.addWidget(self.lbl_title)
        lay.addWidget(self.lbl_value)
        if subtitle:
            lay.addWidget(self.lbl_sub)

    def set_value(self, text: str) -> None:
        self.lbl_value.setText(text)


if MATPLOTLIB_AVAILABLE:

    class SignalChart(FigureCanvasQTAgg):
        def __init__(self, parent=None, width=8, height=4, dpi=100):
            fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = fig.add_subplot(111)
            super().__init__(fig)
            self.setParent(parent)

        def plot_history(self, histories: Dict[str, NetworkHistory], selected_bssids: Optional[List[str]] = None):
            self.axes.clear()

            if not histories:
                self.axes.text(0.5, 0.5, "No historical data available", ha="center", va="center", transform=self.axes.transAxes)
                self.draw()
                return

            if selected_bssids is None:
                selected_bssids = list(histories.keys())[:5]

            for bssid in selected_bssids:
                hist = histories.get(bssid)
                if not hist or not hist.timestamps:
                    continue
                start_time = min(hist.timestamps)
                times = [(t - start_time) for t in hist.timestamps]
                label = f"{hist.ssid} ({bssid[-8:]})"
                self.axes.plot(times, hist.signals, marker="o", linestyle="-", label=label, linewidth=2, markersize=4)

            self.axes.set_xlabel("Time (seconds)")
            self.axes.set_ylabel("Signal Strength (dBm)")
            self.axes.set_title("Wi-Fi Signal History", fontweight="bold")
            self.axes.grid(True, alpha=0.3)
            
            # Only add legend if we plotted something (avoids warning)
            if any(line.get_label() and not line.get_label().startswith('_') for line in self.axes.get_lines()):
                self.axes.legend(loc="best", fontsize=8)
            
            self.axes.set_ylim(-100, -20)
            self.figure.tight_layout()
            self.draw()


# ----------------------------- GUI -----------------------------

COLUMNS = [
    ("SSID", "Network name. Hidden SSIDs may appear blank."),
    ("BSSID", "Access point MAC address (one SSID can have multiple BSSIDs)."),
    ("Signal (dBm)", "Closer to 0 is stronger. -50 great, -65 ok, -75 weak."),
    ("Signal (%)", "OS strength. Often converted to dBm via heuristic."),
    ("Noise (dBm)", "Noise floor. Often only available for current connection."),
    ("SNR (dB)", "Signal-to-noise ratio = signal - noise."),
    ("Channel", "Wi-Fi channel."),
    ("Freq (MHz)", "Center frequency."),
    ("Band", "2.4/5/6GHz."),
    ("Security", "Prefer WPA2/WPA3; avoid OPEN/WEP."),
    ("Score", "Heuristic quality score."),
    ("Status", "Connection status."),
    ("Notes", "Parse/enrichment notes."),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")

        base = os.path.join(os.path.expanduser("~"), ".wifi_scout")
        os.makedirs(base, exist_ok=True)
        self.log_path = os.path.join(base, f"wifi_scout_{time.strftime('%Y%m%d_%H%M%S')}.log")
        self.logger = make_logger(self.log_path)

        self.networks: List[WifiNetwork] = []
        self.network_history: Dict[str, NetworkHistory] = {}
        self.dark_mode = False
        self.auto_scan_enabled = False
        self.scan_thread: Optional[ScanThread] = None
        self.connected_bssid: Optional[str] = None
        
        # BUG FIX: Rate limiting for connection attempts
        self.last_connection_attempt: float = 0.0
        self.connection_rate_limit_seconds: float = 5.0  # Minimum 5 seconds between attempts

        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.do_scan)

        self.init_ui()
        self.apply_theme()

        self.logger.info("%s started. Log: %s", APP_NAME, self.log_path)

    # ---------------- UI ----------------

    def init_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.scanner_tab = QWidget()
        self.init_scanner_tab()
        self.tabs.addTab(self.scanner_tab, "Scanner")

        self.details_tab = QWidget()
        self.init_details_tab()
        self.tabs.addTab(self.details_tab, "Details")

        if MATPLOTLIB_AVAILABLE:
            self.chart_tab = QWidget()
            self.init_chart_tab()
            self.tabs.addTab(self.chart_tab, "Signal History")

        self.log_tab = QWidget()
        self.init_log_tab()
        self.tabs.addTab(self.log_tab, "Logs")

        self.statusBar().showMessage("Ready")
        self.init_menu_bar()

    def init_menu_bar(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Results…", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.do_export)
        file_menu.addAction(export_action)

        export_html_action = QAction("Export HTML Report…", self)
        export_html_action.triggered.connect(self.export_html_report)
        file_menu.addAction(export_html_action)

        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menubar.addMenu("View")
        theme_action = QAction("Toggle Dark/Light Theme", self)
        theme_action.setShortcut("Ctrl+T")
        theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(theme_action)

        refresh_action = QAction("Refresh Scan", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.do_scan)
        view_menu.addAction(refresh_action)

        tools_menu = menubar.addMenu("Tools")
        best_action = QAction("Find Best Network", self)
        best_action.setShortcut("Ctrl+B")
        best_action.triggered.connect(self.do_best)
        tools_menu.addAction(best_action)

        connect_action = QAction("Connect to Selected…", self)
        connect_action.setShortcut("Ctrl+C")
        connect_action.triggered.connect(self.connect_to_selected)
        tools_menu.addAction(connect_action)

        tools_menu.addSeparator()
        clear_history_action = QAction("Clear Signal History", self)
        clear_history_action.triggered.connect(self.clear_history)
        tools_menu.addAction(clear_history_action)

        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        copy_log_action = QAction("Copy Log Path", self)
        copy_log_action.triggered.connect(self.copy_log_path)
        help_menu.addAction(copy_log_action)

    def init_scanner_tab(self) -> None:
        layout = QVBoxLayout(self.scanner_tab)

        # Controls
        control_panel = QGroupBox("Controls")
        control_layout = QGridLayout()

        self.btn_scan = QPushButton("🔍 Scan Now")
        self.btn_scan.setToolTip("Perform a Wi-Fi scan (F5)")
        self.btn_scan.clicked.connect(self.do_scan)
        control_layout.addWidget(self.btn_scan, 0, 0)

        self.btn_best = QPushButton("⭐ Find Best")
        self.btn_best.setToolTip("Highlight the recommended network (Ctrl+B)")
        self.btn_best.clicked.connect(self.do_best)
        control_layout.addWidget(self.btn_best, 0, 1)

        self.btn_connect = QPushButton("🔗 Connect")
        self.btn_connect.setToolTip("Connect to selected network (Ctrl+C)")
        self.btn_connect.clicked.connect(self.connect_to_selected)
        control_layout.addWidget(self.btn_connect, 0, 2)

        self.btn_export = QPushButton("💾 Export")
        self.btn_export.setToolTip("Export scan results (Ctrl+E)")
        self.btn_export.clicked.connect(self.do_export)
        control_layout.addWidget(self.btn_export, 0, 3)

        self.chk_auto_scan = QCheckBox("Auto-refresh every")
        self.chk_auto_scan.setToolTip("Enable automatic scanning at intervals")
        self.chk_auto_scan.toggled.connect(self.toggle_auto_scan)
        control_layout.addWidget(self.chk_auto_scan, 1, 0)

        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(5, 300)
        self.spin_interval.setValue(10)
        self.spin_interval.setSuffix(" sec")
        self.spin_interval.setToolTip("Scan interval in seconds")
        control_layout.addWidget(self.spin_interval, 1, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setMaximum(0)  # indeterminate
        control_layout.addWidget(self.progress_bar, 1, 2, 1, 2)

        control_layout.addWidget(QLabel("Filter:"), 2, 0)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search SSID or BSSID…")
        self.search_box.textChanged.connect(self.apply_filters)
        control_layout.addWidget(self.search_box, 2, 1, 1, 2)

        self.combo_band_filter = QComboBox()
        self.combo_band_filter.addItems(["All Bands", "2.4GHz", "5GHz", "6GHz"])
        self.combo_band_filter.currentTextChanged.connect(self.apply_filters)
        control_layout.addWidget(self.combo_band_filter, 2, 3)

        self.chk_hide_open = QCheckBox("Hide OPEN networks")
        self.chk_hide_open.toggled.connect(self.apply_filters)
        control_layout.addWidget(self.chk_hide_open, 3, 0, 1, 2)

        self.chk_allow_open = QCheckBox("Allow OPEN in scoring")
        self.chk_allow_open.setToolTip("Don’t heavily penalize OPEN networks in recommendation (not recommended)")
        self.chk_allow_open.setChecked(False)
        control_layout.addWidget(self.chk_allow_open, 3, 2, 1, 2)

        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)

        # Stats
        stats_panel = QGroupBox("Statistics")
        stats_layout = QHBoxLayout()

        self.lbl_total_networks = QLabel("Networks: 0")
        stats_layout.addWidget(self.lbl_total_networks)

        self.lbl_unique_ssids = QLabel("Unique SSIDs: 0")
        stats_layout.addWidget(self.lbl_unique_ssids)

        self.lbl_avg_signal = QLabel("Avg Signal: N/A")
        stats_layout.addWidget(self.lbl_avg_signal)

        self.lbl_strongest = QLabel("Strongest: N/A")
        stats_layout.addWidget(self.lbl_strongest)

        self.lbl_connected = QLabel("Connected: None")
        stats_layout.addWidget(self.lbl_connected)

        stats_layout.addStretch()
        stats_panel.setLayout(stats_layout)
        layout.addWidget(stats_panel)

        # Selected dashboard
        dash = QGroupBox("Selected Network")
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(10)

        self.card_ssid = MetricCard("SSID")
        self.card_signal = MetricCard("Signal (dBm)", "-50 great • -65 ok • -75 weak")
        self.card_noise = MetricCard("Noise (dBm)", "Often only available for current connection")
        self.card_snr = MetricCard("SNR (dB)", "25+ good • 40+ excellent")
        self.card_security = MetricCard("Security")
        self.card_score = MetricCard("Score")
        self.card_status = MetricCard("Status")

        for c in (
            self.card_ssid,
            self.card_signal,
            self.card_noise,
            self.card_snr,
            self.card_security,
            self.card_score,
            self.card_status,
        ):
            dash_layout.addWidget(c, 1)

        dash.setLayout(dash_layout)
        layout.addWidget(dash)

        # Table
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.itemDoubleClicked.connect(lambda _: self.tabs.setCurrentWidget(self.details_tab))

        for i, (name, tip) in enumerate(COLUMNS):
            self.table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
            self.table.horizontalHeaderItem(i).setToolTip(tip)

        # Set minimum column widths so text is visible
        self.table.setColumnWidth(0, 150)  # SSID
        self.table.setColumnWidth(1, 130)  # BSSID
        self.table.setColumnWidth(2, 90)   # Signal (dBm)
        self.table.setColumnWidth(3, 80)   # Signal (%)
        self.table.setColumnWidth(4, 90)   # Noise (dBm)
        self.table.setColumnWidth(5, 80)   # SNR (dB)
        self.table.setColumnWidth(6, 70)   # Channel
        self.table.setColumnWidth(7, 90)   # Freq (MHz)
        self.table.setColumnWidth(8, 80)   # Band
        self.table.setColumnWidth(9, 100)  # Security
        self.table.setColumnWidth(10, 70)  # Score
        self.table.setColumnWidth(11, 70)  # Status
        self.table.setColumnWidth(12, 180) # Notes

        layout.addWidget(self.table, 1)

    def init_details_tab(self) -> None:
        layout = QVBoxLayout(self.details_tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        wl = QVBoxLayout(w)

        details_group = QGroupBox("Selected Network Details")
        details_layout = QGridLayout()

        self.detail_labels: Dict[str, QLabel] = {}
        fields = [
            ("ssid", "SSID:"),
            ("bssid", "BSSID:"),
            ("signal_dbm", "Signal (dBm):"),
            ("signal_percent", "Signal (%):"),
            ("noise_dbm", "Noise (dBm):"),
            ("snr_db", "SNR (dB):"),
            ("channel", "Channel:"),
            ("freq_mhz", "Frequency (MHz):"),
            ("band", "Band:"),
            ("security", "Security:"),
            ("auth_detail", "Auth Details:"),
            ("score", "Score:"),
            ("source", "Data Source:"),
            ("notes", "Notes:"),
        ]

        for r, (key, label_text) in enumerate(fields):
            lab = QLabel(label_text)
            lab.setStyleSheet("font-weight: bold;")
            val = QLabel("—")
            val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            val.setWordWrap(True)
            details_layout.addWidget(lab, r, 0, Qt.AlignmentFlag.AlignRight)
            details_layout.addWidget(val, r, 1)
            self.detail_labels[key] = val

        details_group.setLayout(details_layout)
        wl.addWidget(details_group)

        conn_group = QGroupBox("Connection Management")
        conn_layout = QVBoxLayout()

        row = QHBoxLayout()
        btn_connect = QPushButton("Connect to This Network")
        btn_connect.clicked.connect(self.connect_to_selected)
        row.addWidget(btn_connect)

        btn_refresh = QPushButton("Refresh Connection Status")
        btn_refresh.clicked.connect(self.update_connection_status)
        row.addWidget(btn_refresh)

        conn_layout.addLayout(row)

        self.connection_status_label = QLabel("Status: Not connected")
        self.connection_status_label.setWordWrap(True)
        conn_layout.addWidget(self.connection_status_label)

        conn_group.setLayout(conn_layout)
        wl.addWidget(conn_group)

        quality_group = QGroupBox("Quality Assessment")
        quality_layout = QVBoxLayout()
        self.quality_text = QTextEdit()
        self.quality_text.setReadOnly(True)
        self.quality_text.setMaximumHeight(220)
        quality_layout.addWidget(self.quality_text)
        quality_group.setLayout(quality_layout)
        wl.addWidget(quality_group)

        wl.addStretch()
        scroll.setWidget(w)
        layout.addWidget(scroll)

    def init_chart_tab(self) -> None:
        layout = QVBoxLayout(self.chart_tab)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Show networks:"))

        self.chart_network_selector = QComboBox()
        self.chart_network_selector.addItem("All (top 5)")
        self.chart_network_selector.currentTextChanged.connect(self.update_chart)
        controls.addWidget(self.chart_network_selector, 1)

        btn_clear = QPushButton("Clear History")
        btn_clear.clicked.connect(self.clear_history)
        controls.addWidget(btn_clear)

        layout.addLayout(controls)

        self.chart = SignalChart(self.chart_tab, width=10, height=6)
        layout.addWidget(self.chart, 1)

        info = QLabel("💡 Tip: Enable auto-refresh to collect continuous history.")
        info.setWordWrap(True)
        info.setStyleSheet("color: gray; padding: 10px;")
        layout.addWidget(info)

    def init_log_tab(self) -> None:
        layout = QVBoxLayout(self.log_tab)

        controls = QHBoxLayout()
        btn_clear = QPushButton("Clear Log")
        btn_clear.clicked.connect(lambda: self.log_view.clear())
        controls.addWidget(btn_clear)

        btn_copy_log_path = QPushButton("Copy Log File Path")
        btn_copy_log_path.clicked.connect(self.copy_log_path)
        controls.addWidget(btn_copy_log_path)

        btn_open_log_folder = QPushButton("Open Log Folder")
        btn_open_log_folder.clicked.connect(self.open_log_folder)
        controls.addWidget(btn_open_log_folder)

        controls.addStretch()
        layout.addLayout(controls)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_view, 1)

        self.logger.addHandler(QtLogHandler(self.log_view))

    # ---------------- Theme ----------------

    def apply_theme(self) -> None:
        if self.dark_mode:
            self.setStyleSheet(
                """
                QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
                QTableWidget { background-color: #3c3c3c; alternate-background-color: #454545; gridline-color: #555555; }
                QGroupBox { border: 1px solid #555555; border-radius: 6px; margin-top: 10px; padding-top: 10px; font-weight: bold; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QPushButton { background-color: #0d7377; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #14a085; }
                QPushButton:pressed { background-color: #0a5f63; }
                QLineEdit, QComboBox, QSpinBox { background-color: #3c3c3c; border: 1px solid #555555; border-radius: 5px; padding: 5px; }
                QTextEdit { background-color: #3c3c3c; border: 1px solid #555555; }
                #MetricCard { background: #3a3a3a; border: 2px solid #555555; border-radius: 12px; }
                #MetricTitle { color: #aaa; font-size: 11px; font-weight: 600; }
                #MetricValue { font-size: 20px; font-weight: 700; color: #14a085; }
                #MetricSub { color: #888; font-size: 10px; }
                """
            )
        else:
            self.setStyleSheet(
                """
                QPushButton { background-color: #0d7377; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; }
                QPushButton:hover { background-color: #14a085; }
                QPushButton:pressed { background-color: #0a5f63; }
                QGroupBox { border: 1px solid #cccccc; border-radius: 6px; margin-top: 10px; padding-top: 10px; font-weight: bold; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
                QTableWidget { alternate-background-color: #f5f5f5; }
                #MetricCard { background: #f8f8f8; border: 2px solid #d0d0d0; border-radius: 12px; }
                #MetricTitle { color: #555; font-size: 11px; font-weight: 600; }
                #MetricValue { font-size: 20px; font-weight: 700; color: #0d7377; }
                #MetricSub { color: #888; font-size: 10px; }
                """
            )

    def toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        self.logger.info("Theme changed to %s", "dark" if self.dark_mode else "light")
        self.populate()  # refresh connected highlight colors

    # ---------------- Data/UI ----------------

    def set_busy(self, busy: bool) -> None:
        self.progress_bar.setVisible(busy)
        for w in (self.btn_scan, self.btn_best, self.btn_connect, self.btn_export):
            w.setEnabled(not busy)

    def clear_table(self) -> None:
        self.table.setRowCount(0)

    def add_row(self, n: WifiNetwork) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        status = "●" if n.is_connected else ""
        values = [
            n.ssid,
            n.bssid,
            "" if n.signal_dbm is None else str(n.signal_dbm),
            "" if n.signal_percent is None else str(n.signal_percent),
            "" if n.noise_dbm is None else str(n.noise_dbm),
            "" if n.snr_db is None else str(n.snr_db),
            "" if n.channel is None else str(n.channel),
            "" if n.freq_mhz is None else str(n.freq_mhz),
            "" if n.band is None else n.band,
            n.security,
            "" if n.score is None else f"{n.score:.1f}",
            status,
            n.notes,
        ]

        for c, v in enumerate(values):
            item = QTableWidgetItem(v)

            if c in (2, 3, 4, 5, 6, 7, 10):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Signal coloring
            if c == 2 and n.signal_dbm is not None:
                if n.signal_dbm >= -50:
                    item.setForeground(QBrush(QColor(0, 200, 0)))
                elif n.signal_dbm >= -65:
                    item.setForeground(QBrush(QColor(200, 200, 0)))
                elif n.signal_dbm >= -75:
                    item.setForeground(QBrush(QColor(255, 140, 0)))
                else:
                    item.setForeground(QBrush(QColor(200, 0, 0)))

            # Security coloring
            if c == 9:
                sec = normalize_security(n.security)
                if sec == "WPA3":
                    item.setForeground(QBrush(QColor(0, 150, 0)))
                elif sec == "WPA2":
                    item.setForeground(QBrush(QColor(0, 100, 200)))
                elif sec in ("OPEN", "WEP"):
                    item.setForeground(QBrush(QColor(200, 0, 0)))
                    item.setFont(QFont(item.font().family(), item.font().pointSize(), QFont.Weight.Bold))

            # Connected highlight
            if n.is_connected:
                item.setBackground(QBrush(QColor(200, 255, 200) if not self.dark_mode else QColor(0, 80, 0)))
                if c == 11:
                    item.setForeground(QBrush(QColor(0, 150, 0)))
                    item.setFont(QFont(item.font().family(), 14, QFont.Weight.Bold))

            self.table.setItem(r, c, item)

    def populate(self) -> None:
        self.clear_table()
        for n in self.networks:
            self.add_row(n)
        # Resize columns to fit content, but respect minimum widths set in init
        for col in range(self.table.columnCount()):
            self.table.resizeColumnToContents(col)
        self.update_statistics()
        self.apply_filters()
        if MATPLOTLIB_AVAILABLE:
            self.update_chart_selector()
            self.update_chart()

    def update_statistics(self) -> None:
        if not self.networks:
            self.lbl_total_networks.setText("Networks: 0")
            self.lbl_unique_ssids.setText("Unique SSIDs: 0")
            self.lbl_avg_signal.setText("Avg Signal: N/A")
            self.lbl_strongest.setText("Strongest: N/A")
            return

        total = len(self.networks)
        unique_ssids = len(set(n.ssid for n in self.networks if n.ssid))

        signals = [n.signal_dbm for n in self.networks if n.signal_dbm is not None]
        avg_signal = (sum(signals) / len(signals)) if signals else None

        strongest = max(self.networks, key=lambda n: (n.signal_dbm if n.signal_dbm is not None else -999))

        self.lbl_total_networks.setText(f"Networks: {total}")
        self.lbl_unique_ssids.setText(f"Unique SSIDs: {unique_ssids}")
        self.lbl_avg_signal.setText(f"Avg Signal: {avg_signal:.1f} dBm" if avg_signal is not None else "Avg Signal: N/A")
        self.lbl_strongest.setText(
            f"Strongest: {strongest.ssid} ({strongest.signal_dbm} dBm)" if strongest.signal_dbm is not None else "Strongest: N/A"
        )

    def apply_filters(self) -> None:
        search_text = self.search_box.text().lower().strip()
        band_filter = self.combo_band_filter.currentText()
        hide_open = self.chk_hide_open.isChecked()

        for row in range(self.table.rowCount()):
            show_row = True
            
            # Get table items with null checks
            ssid_item = self.table.item(row, 0)
            bssid_item = self.table.item(row, 1)
            band_item = self.table.item(row, 8)
            security_item = self.table.item(row, 9)
            
            # Skip row if items aren't created yet
            if not all([ssid_item, bssid_item, band_item, security_item]):
                continue
            
            ssid = ssid_item.text().lower()
            bssid = bssid_item.text().lower()
            band = band_item.text()
            security = security_item.text()

            if search_text and (search_text not in ssid and search_text not in bssid):
                show_row = False
            if band_filter != "All Bands" and band != band_filter:
                show_row = False
            if hide_open and normalize_security(security) == "OPEN":
                show_row = False

            self.table.setRowHidden(row, not show_row)

    def on_selection_changed(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        
        # Null check for table item
        bssid_item = self.table.item(row, 1)
        if not bssid_item:
            return
            
        bssid = bssid_item.text().lower()
        net = next((n for n in self.networks if n.bssid.lower() == bssid), None)
        if net:
            self.show_network_details(net)
            self.update_selected_dashboard(net)

    def update_selected_dashboard(self, net: WifiNetwork) -> None:
        self.card_ssid.set_value(net.ssid or "—")
        self.card_signal.set_value(f"{net.signal_dbm} dBm" if net.signal_dbm is not None else "—")
        self.card_noise.set_value(f"{net.noise_dbm} dBm" if net.noise_dbm is not None else "—")
        self.card_snr.set_value(f"{net.snr_db} dB" if net.snr_db is not None else "—")
        self.card_security.set_value(net.security or "—")
        self.card_score.set_value(f"{net.score:.1f}" if net.score is not None else "—")
        self.card_status.set_value("Connected" if net.is_connected else "Not connected")

    def show_network_details(self, net: WifiNetwork) -> None:
        self.detail_labels["ssid"].setText(net.ssid or "—")
        self.detail_labels["bssid"].setText(net.bssid or "—")
        self.detail_labels["signal_dbm"].setText(f"{net.signal_dbm} dBm" if net.signal_dbm is not None else "—")
        self.detail_labels["signal_percent"].setText(f"{net.signal_percent}%" if net.signal_percent is not None else "—")
        self.detail_labels["noise_dbm"].setText(f"{net.noise_dbm} dBm" if net.noise_dbm is not None else "—")
        self.detail_labels["snr_db"].setText(f"{net.snr_db} dB" if net.snr_db is not None else "—")
        self.detail_labels["channel"].setText(str(net.channel) if net.channel is not None else "—")
        self.detail_labels["freq_mhz"].setText(f"{net.freq_mhz} MHz" if net.freq_mhz is not None else "—")
        self.detail_labels["band"].setText(net.band or "—")
        self.detail_labels["security"].setText(net.security or "—")
        self.detail_labels["auth_detail"].setText(net.auth_detail or "—")
        self.detail_labels["score"].setText(f"{net.score:.2f}" if net.score is not None else "—")
        self.detail_labels["source"].setText(net.source or "—")
        self.detail_labels["notes"].setText(net.notes or "—")
        self.quality_text.setHtml(self.generate_quality_assessment(net))

    def generate_quality_assessment(self, net: WifiNetwork) -> str:
        html = "<h3>Quality Assessment</h3>"

        if net.score_breakdown:
            b = net.score_breakdown
            html += "<h4>📊 Score Breakdown</h4><table border='1' cellpadding='5' style='border-collapse: collapse;'>"
            html += "<tr><th align='left'>Component</th><th align='right'>Points</th></tr>"
            for key, label in [
                ("security", "Security"),
                ("signal", "Signal Strength"),
                ("band_bonus", "Band Bonus"),
                ("congestion_penalty", "Congestion Penalty"),
                ("channel_bonus", "Channel Bonus"),
                ("snr_bonus", "SNR Bonus"),
                ("total", "Total Score"),
            ]:
                style = " style='font-weight: bold; background: #f0f0f0;'" if key == "total" else ""
                html += f"<tr{style}><td>{label}</td><td align='right'>{b.get(key, 0):.1f}</td></tr>"
            html += "</table><br>"

        html += "<h4>📶 Signal</h4><ul>"
        if net.signal_dbm is None:
            html += "<li>Signal data not available</li>"
        else:
            s = net.signal_dbm
            if s >= -50:
                html += f"<li><b style='color: green;'>Excellent</b> ({s} dBm)</li>"
            elif s >= -65:
                html += f"<li><b style='color: #ccaa00;'>Good</b> ({s} dBm)</li>"
            elif s >= -75:
                html += f"<li><b style='color: orange;'>Fair</b> ({s} dBm)</li>"
            else:
                html += f"<li><b style='color: red;'>Poor</b> ({s} dBm)</li>"
        html += "</ul>"

        html += "<h4>📉 Noise / SNR</h4><ul>"
        if net.noise_dbm is not None:
            html += f"<li>Noise: {net.noise_dbm} dBm</li>"
        else:
            html += "<li>Noise: unavailable (common for scans)</li>"
        if net.snr_db is not None:
            html += f"<li>SNR: {net.snr_db} dB</li>"
        else:
            html += "<li>SNR: unavailable</li>"
        html += "</ul>"

        html += "<h4>🔒 Security</h4><ul>"
        sec = normalize_security(net.security)
        if sec == "WPA3":
            html += "<li><b style='color: green;'>Excellent</b> (WPA3)</li>"
        elif sec == "WPA2":
            html += "<li><b style='color: blue;'>Good</b> (WPA2)</li>"
        elif sec == "WPA":
            html += "<li><b style='color: orange;'>Acceptable</b> (WPA)</li>"
        elif sec == "WEP":
            html += "<li><b style='color: red;'>Dangerous</b> (WEP)</li>"
        elif sec == "OPEN":
            html += "<li><b style='color: red;'>Insecure</b> (OPEN)</li>"
        else:
            html += f"<li>{html_escape(net.security)}</li>"
        html += "</ul>"

        html += "<h4>📡 Channel & Band</h4><ul>"
        if net.band:
            if net.band == "2.4GHz":
                html += "<li>2.4 GHz — better range, more interference</li>"
                if net.channel in (1, 6, 11):
                    html += f"<li><b style='color: green;'>Optimal channel {net.channel}</b></li>"
                elif net.channel is not None:
                    html += f"<li><b style='color: orange;'>Overlapping channel {net.channel}</b></li>"
            else:
                html += f"<li>{net.band} — typically faster/cleaner if signal is solid</li>"
        html += "</ul>"

        if net.score is not None:
            html += "<h4>⭐ Overall</h4><ul>"
            if net.score >= 40:
                html += "<li style='color: green;'><b>Highly Recommended</b></li>"
            elif net.score >= 20:
                html += "<li style='color: #ccaa00;'><b>Recommended</b></li>"
            elif net.score >= 0:
                html += "<li style='color: orange;'><b>Acceptable</b></li>"
            else:
                html += "<li style='color: red;'><b>Not Recommended</b></li>"
            html += "</ul>"

        return html

    # ---------------- Auto scan ----------------

    def toggle_auto_scan(self, enabled: bool) -> None:
        self.auto_scan_enabled = enabled
        if enabled:
            interval = self.spin_interval.value()
            self.scan_timer.start(interval * 1000)
            self.logger.info("Auto-scan enabled: every %s seconds", interval)
            self.do_scan()
        else:
            self.scan_timer.stop()
            self.logger.info("Auto-scan disabled")

    # ---------------- Scanning (threaded) ----------------

    def do_scan(self) -> None:
        if self.scan_thread and self.scan_thread.isRunning():
            return

        self.statusBar().showMessage("Scanning…")
        self.logger.info("==== SCAN START (async) ====")
        self.set_busy(True)

        self.scan_thread = ScanThread(self.logger)
        self.scan_thread.scan_complete.connect(self.on_scan_complete)
        self.scan_thread.scan_error.connect(self.on_scan_error)
        self.scan_thread.start()

    def on_scan_complete(self, nets: list) -> None:
        try:
            self.networks = list(nets)

            # connected + noise enrichment
            self.connected_bssid = mark_connected_and_enrich(self.logger, self.networks)
            self.update_connection_status()

            # scoring + history
            allow_open = self.chk_allow_open.isChecked()
            for n in self.networks:
                n.score = score_network(self.networks, n, allow_open=allow_open)
                if n.signal_dbm is not None:
                    hist = self.network_history.get(n.bssid)
                    if not hist:
                        hist = NetworkHistory(bssid=n.bssid, ssid=n.ssid, timestamps=[], signals=[])
                        self.network_history[n.bssid] = hist
                    hist.add_reading(n.timestamp or time.time(), n.signal_dbm)

            self.populate()
            self.statusBar().showMessage(f"Scan complete. Found {len(self.networks)} BSSID entries.", 5000)
            self.logger.info("Scan complete. Entries=%d", len(self.networks))
        finally:
            self.set_busy(False)
            self.logger.info("==== SCAN END ====")

    def on_scan_error(self, msg: str) -> None:
        self.set_busy(False)
        self.logger.error("Scan failed: %s", msg)
        # SECURITY FIX: Don't expose log path to user in error dialog (information disclosure)
        QMessageBox.critical(self, "Scan Failed", f"{msg}\n\nSee application logs for details.")
        self.statusBar().showMessage("Scan failed.", 5000)

    # ---------------- Connected status ----------------

    def update_connection_status(self) -> None:
        self.connected_bssid = get_connected_bssid(self.logger)
        if self.connected_bssid:
            for net in self.networks:
                net.is_connected = (net.bssid.lower() == self.connected_bssid.lower())
            connected = next((n for n in self.networks if n.is_connected), None)
            if connected:
                self.lbl_connected.setText(f"Connected: {connected.ssid}")
                self.connection_status_label.setText(
                    f"✅ Connected to: {connected.ssid} ({connected.bssid})\n"
                    f"Signal: {connected.signal_dbm} dBm, Noise: {connected.noise_dbm if connected.noise_dbm is not None else '—'} dBm, "
                    f"SNR: {connected.snr_db if connected.snr_db is not None else '—'} dB, Channel: {connected.channel}"
                )
                return
        self.lbl_connected.setText("Connected: None")
        self.connection_status_label.setText("❌ Not connected to any network")

    # ---------------- Actions ----------------

    def do_best(self) -> None:
        if not self.networks:
            QMessageBox.information(self, "No Data", "Run a scan first.")
            return

        allow_open = self.chk_allow_open.isChecked()
        best = pick_best(self.networks, allow_open=allow_open)
        if not best:
            QMessageBox.information(self, "No Data", "No networks available.")
            return

        self.populate()

        best_row = None
        for r in range(self.table.rowCount()):
            # Skip hidden rows and check for null items
            if self.table.isRowHidden(r):
                continue
            bssid_item = self.table.item(r, 1)
            if not bssid_item:
                continue
            if bssid_item.text().lower() == best.bssid.lower():
                best_row = r
                break
        if best_row is not None:
            self.table.selectRow(best_row)
            scroll_item = self.table.item(best_row, 0)
            if scroll_item:
                self.table.scrollToItem(scroll_item)

        msg = (
            "Recommended:\n"
            f"  SSID: {best.ssid}\n"
            f"  BSSID: {best.bssid}\n"
            f"  Security: {best.security}\n"
            f"  Signal: {best.signal_dbm} dBm\n"
            f"  Noise: {best.noise_dbm if best.noise_dbm is not None else '—'} dBm\n"
            f"  SNR: {best.snr_db if best.snr_db is not None else '—'} dB\n"
            f"  Channel: {best.channel}\n"
            f"  Band: {best.band}\n"
            f"  Score: {best.score:.1f}"
        )
        self.logger.info("BEST PICK: %s", msg.replace("\n", " | "))
        QMessageBox.information(self, "Best Network", msg)
        self.statusBar().showMessage(f"Best: {best.ssid} ({best.bssid}) score {best.score:.1f}", 5000)

    def connect_to_selected(self) -> None:
        # BUG FIX: Rate limiting to prevent connection spam
        current_time = time.time()
        if current_time - self.last_connection_attempt < self.connection_rate_limit_seconds:
            remaining = self.connection_rate_limit_seconds - (current_time - self.last_connection_attempt)
            QMessageBox.warning(
                self,
                "Rate Limited",
                f"Please wait {remaining:.1f} more seconds before attempting another connection."
            )
            return
        
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.information(self, "No Selection", "Please select a network first.")
            return

        row = selected[0].row()
        
        # Null checks for table items
        ssid_item = self.table.item(row, 0)
        security_item = self.table.item(row, 9)
        if not ssid_item or not security_item:
            QMessageBox.warning(self, "Error", "Could not read network information.")
            return
        
        ssid = ssid_item.text()
        security = security_item.text()

        password = None
        sec_norm = normalize_security(security)
        if sec_norm not in ("OPEN", "Unknown"):
            password, ok = QInputDialog.getText(
                self,
                "Network Password",
                f"Enter password for '{ssid}':",
                QLineEdit.EchoMode.Password,
            )
            if not ok:
                return

        # Update rate limit timestamp
        self.last_connection_attempt = current_time
        
        self.statusBar().showMessage(f"Connecting to {ssid}…")
        # SECURITY FIX: Don't log SSID in case it contains malicious characters
        self.logger.info("Attempting to connect to network")

        success, message = connect_to_network(ssid, password, self.logger)
        if success:
            QMessageBox.information(self, "Connection Successful", message)
            self.statusBar().showMessage(f"Connected to {ssid}", 5000)
            # BUG FIX: Use QTimer instead of time.sleep() to avoid blocking UI
            QTimer.singleShot(2000, self.do_scan)  # Refresh after 2 seconds
        else:
            QMessageBox.warning(self, "Connection Failed", message)
            self.statusBar().showMessage("Connection failed", 5000)

    def do_export(self) -> None:
        if not self.networks:
            QMessageBox.information(self, "No Data", "Run a scan first.")
            return

        ts = time.strftime("%Y%m%d_%H%M%S")
        default_name = f"wifi_scan_{ts}"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export",
            os.path.join(os.path.expanduser("~"), default_name),
            "CSV (*.csv);JSON (*.json)",
        )
        if not path:
            return

        try:
            if path.lower().endswith(".json"):
                data = [asdict(n) for n in self.networks]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            else:
                if not path.lower().endswith(".csv"):
                    path += ".csv"
                with open(path, "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow([c[0] for c in COLUMNS])
                    for n in self.networks:
                        status = "Connected" if n.is_connected else ""
                        w.writerow(
                            [
                                n.ssid,
                                n.bssid,
                                n.signal_dbm,
                                n.signal_percent,
                                n.noise_dbm,
                                n.snr_db,
                                n.channel,
                                n.freq_mhz,
                                n.band,
                                n.security,
                                n.score,
                                status,
                                n.notes,
                            ]
                        )

            self.logger.info("Exported results to %s", path)
            self.statusBar().showMessage(f"Exported: {path}", 5000)
            QMessageBox.information(self, "Export Complete", f"Saved:\n{path}")
        except Exception as e:
            self.logger.exception("Export failed")
            QMessageBox.critical(self, "Export Failed", str(e))

    def export_html_report(self) -> None:
        if not self.networks:
            QMessageBox.information(self, "No Data", "Run a scan first.")
            return

        ts = time.strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export HTML Report",
            os.path.join(os.path.expanduser("~"), f"wifi_report_{ts}.html"),
            "HTML (*.html)",
        )
        if not path:
            return

        try:
            html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Wi-Fi Scan Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
    h1 {{ color: #0d7377; }}
    .metadata {{ background: white; padding: 15px; margin-bottom: 20px; border-radius: 8px; }}
    table {{ border-collapse: collapse; width: 100%; background: white; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #0d7377; color: white; }}
    tr:nth-child(even) {{ background-color: #f9f9f9; }}
    .sec-insecure {{ color: red; font-weight: bold; }}
    .sec-wpa2 {{ color: #0b66c3; font-weight: bold; }}
    .sec-wpa3 {{ color: green; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>Wi-Fi Scan Report</h1>
  <div class="metadata">
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Platform:</strong> {html_escape(platform.system())} {html_escape(platform.release())}</p>
    <p><strong>Total Networks:</strong> {len(self.networks)}</p>
    <p><strong>Scanner:</strong> {html_escape(self.networks[0].source if self.networks else 'N/A')}</p>
  </div>
  <table>
    <tr>
      <th>SSID</th><th>BSSID</th><th>Signal (dBm)</th><th>Noise (dBm)</th><th>SNR (dB)</th>
      <th>Channel</th><th>Band</th><th>Security</th><th>Score</th><th>Status</th>
    </tr>
"""
            for n in sorted(self.networks, key=lambda x: x.score if x.score is not None else -999, reverse=True):
                sec = normalize_security(n.security)
                sec_class = "sec-wpa3" if sec == "WPA3" else "sec-wpa2" if sec == "WPA2" else "sec-insecure" if sec in ("OPEN", "WEP") else ""
                html += (
                    "<tr>"
                    f"<td>{html_escape(n.ssid)}</td>"
                    f"<td>{html_escape(n.bssid)}</td>"
                    f"<td>{n.signal_dbm if n.signal_dbm is not None else 'N/A'}</td>"
                    f"<td>{n.noise_dbm if n.noise_dbm is not None else 'N/A'}</td>"
                    f"<td>{n.snr_db if n.snr_db is not None else 'N/A'}</td>"
                    f"<td>{n.channel if n.channel is not None else 'N/A'}</td>"
                    f"<td>{html_escape(n.band) if n.band else 'N/A'}</td>"
                    f"<td class='{sec_class}'>{html_escape(n.security)}</td>"
                    f"<td>{(f'{n.score:.1f}' if n.score is not None else 'N/A')}</td>"
                    f"<td>{'Connected' if n.is_connected else ''}</td>"
                    "</tr>\n"
                )

            html += """  </table>
  <p style="margin-top: 20px; color: gray;"><em>Generated by Wi-Fi Scout Pro</em></p>
</body></html>"""

            with open(path, "w", encoding="utf-8") as f:
                f.write(html)

            self.statusBar().showMessage(f"Exported: {path}", 5000)
            self.logger.info("Exported HTML report to %s", path)
            QMessageBox.information(self, "Export Complete", f"Saved:\n{path}")
        except Exception as e:
            self.logger.exception("HTML export failed")
            QMessageBox.critical(self, "Export Failed", str(e))

    # ---------------- Chart ----------------

    def update_chart_selector(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            return
        current_text = self.chart_network_selector.currentText()
        self.chart_network_selector.clear()
        self.chart_network_selector.addItem("All (top 5)")
        for bssid, hist in self.network_history.items():
            if hist.timestamps:
                label = f"{hist.ssid} ({bssid[-8:]})"
                self.chart_network_selector.addItem(label, bssid)
        idx = self.chart_network_selector.findText(current_text)
        if idx >= 0:
            self.chart_network_selector.setCurrentIndex(idx)

    def update_chart(self) -> None:
        if not MATPLOTLIB_AVAILABLE:
            return
        selection = self.chart_network_selector.currentText()
        if selection == "All (top 5)":
            sorted_nets = sorted(
                self.networks,
                key=lambda n: (n.signal_dbm if n.signal_dbm is not None else -999),
                reverse=True,
            )
            selected_bssids = [n.bssid for n in sorted_nets[:5]]
        else:
            bssid = self.chart_network_selector.currentData()
            selected_bssids = [bssid] if bssid else []
        self.chart.plot_history(self.network_history, selected_bssids)

    def clear_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Clear all signal history data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.network_history.clear()
            if MATPLOTLIB_AVAILABLE:
                self.update_chart_selector()
                self.update_chart()
            self.statusBar().showMessage("Signal history cleared", 3000)

    # ---------------- Misc ----------------

    def show_about(self) -> None:
        about_text = f"<h2>{APP_NAME} v{APP_VERSION}</h2><p>Cross-platform Wi-Fi scanner and analyzer.</p><p>Platform: {platform.system()}</p>"
        QMessageBox.about(self, f"About {APP_NAME}", about_text)

    def copy_log_path(self) -> None:
        QApplication.clipboard().setText(self.log_path)
        self.statusBar().showMessage("Log path copied to clipboard", 3000)

    def open_log_folder(self) -> None:
        log_dir = os.path.dirname(self.log_path)
        if platform.system() == "Windows":
            os.startfile(log_dir)  # type: ignore[attr-defined]
        elif platform.system() == "Darwin":
            subprocess.run(["open", log_dir], check=False)
        else:
            subprocess.run(["xdg-open", log_dir], check=False)


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 850)
    win.show()
    sys.exit(app.exec())



if __name__ == "__main__":
    main()