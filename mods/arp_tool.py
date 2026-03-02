"""
ARP Tool - ARP table viewer and analyzer.

Displays the system's ARP (Address Resolution Protocol) cache showing
IP-to-MAC address mappings for devices on the local network.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import platform
import re
import subprocess

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt6.QtCore import Qt
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== DATA MODEL ====================

@dataclass
class ARPEntry:
    """Single ARP table entry."""
    ip_address: str
    mac_address: str
    interface: Optional[str] = None
    type_status: Optional[str] = None  # e.g., "dynamic", "static"


@dataclass
class ARPResult:
    """ARP table result."""
    entries: List[ARPEntry] = field(default_factory=list)
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== ARP COLLECTOR ====================

class ARPCollector:
    """Collect ARP table entries."""
    
    @staticmethod
    def collect() -> ARPResult:
        """Collect ARP table."""
        import time
        result = ARPResult(timestamp=time.time())
        
        system = platform.system()
        
        try:
            if system == "Windows":
                result.entries = ARPCollector._collect_windows()
            elif system == "Linux":
                result.entries = ARPCollector._collect_linux()
            elif system == "Darwin":
                result.entries = ARPCollector._collect_macos()
            else:
                result.error = f"Unsupported platform: {system}"
                result.success = False
                return result
            
            result.success = True
        
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        return result
    
    @staticmethod
    def _collect_windows() -> List[ARPEntry]:
        """Collect ARP table on Windows using arp -a."""
        entries = []
        
        try:
            proc = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                current_interface = None
                
                for line in proc.stdout.splitlines():
                    # Interface line: "Interface: 192.168.1.100 --- 0x3"
                    if "Interface:" in line:
                        match = re.search(r'Interface:\s+(\S+)', line)
                        if match:
                            current_interface = match.group(1)
                        continue
                    
                    # ARP entry: "  192.168.1.1           00-11-22-33-44-55     dynamic"
                    parts = line.split()
                    if len(parts) >= 2:
                        # Try to find IP and MAC
                        ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', line)
                        mac_match = re.search(r'\b([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})\b', line)
                        
                        if ip_match and mac_match:
                            ip = ip_match.group(0)
                            mac = mac_match.group(0).replace('-', ':').lower()
                            
                            # Get type/status (last word usually)
                            type_status = parts[-1] if len(parts) >= 3 else None
                            
                            entries.append(ARPEntry(
                                ip_address=ip,
                                mac_address=mac,
                                interface=current_interface,
                                type_status=type_status
                            ))
        
        except Exception:
            pass
        
        return entries
    
    @staticmethod
    def _collect_linux() -> List[ARPEntry]:
        """Collect ARP table on Linux using ip neigh or arp."""
        entries = []
        
        # Try ip neigh first (modern Linux)
        try:
            proc = subprocess.run(
                ["ip", "neigh", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    # Format: "192.168.1.1 dev eth0 lladdr 00:11:22:33:44:55 REACHABLE"
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        
                        # Find MAC address (after "lladdr")
                        mac = None
                        interface = None
                        status = None
                        
                        for i, part in enumerate(parts):
                            if part == "dev" and i + 1 < len(parts):
                                interface = parts[i + 1]
                            elif part == "lladdr" and i + 1 < len(parts):
                                mac = parts[i + 1].lower()
                            elif i == len(parts) - 1 and re.match(r'^[A-Z]+$', part):
                                status = part.lower()
                        
                        if mac:
                            entries.append(ARPEntry(
                                ip_address=ip,
                                mac_address=mac,
                                interface=interface,
                                type_status=status
                            ))
                
                return entries
        
        except FileNotFoundError:
            pass
        
        # Fallback to arp command
        try:
            proc = subprocess.run(
                ["arp", "-n"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                for line in proc.stdout.splitlines()[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 3:
                        ip = parts[0]
                        mac = parts[2].lower()
                        
                        # Check if valid MAC
                        if re.match(r'^([0-9a-f]{2}:){5}[0-9a-f]{2}$', mac):
                            entries.append(ARPEntry(
                                ip_address=ip,
                                mac_address=mac,
                                interface=parts[4] if len(parts) > 4 else None
                            ))
        
        except Exception:
            pass
        
        return entries
    
    @staticmethod
    def _collect_macos() -> List[ARPEntry]:
        """Collect ARP table on macOS using arp -a."""
        entries = []
        
        try:
            proc = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    # Format: "? (192.168.1.1) at 00:11:22:33:44:55 on en0 ifscope [ethernet]"
                    # or: "router.local (192.168.1.1) at 00:11:22:33:44:55 on en0 ifscope [ethernet]"
                    
                    # Extract IP
                    ip_match = re.search(r'\((\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\)', line)
                    if not ip_match:
                        continue
                    
                    ip = ip_match.group(1)
                    
                    # Extract MAC
                    mac_match = re.search(r'at\s+([0-9a-f]{1,2}:[0-9a-f]{1,2}:[0-9a-f]{1,2}:[0-9a-f]{1,2}:[0-9a-f]{1,2}:[0-9a-f]{1,2})', line, re.IGNORECASE)
                    if not mac_match:
                        continue
                    
                    mac = mac_match.group(1).lower()
                    
                    # Extract interface
                    interface_match = re.search(r'on\s+(\S+)', line)
                    interface = interface_match.group(1) if interface_match else None
                    
                    entries.append(ARPEntry(
                        ip_address=ip,
                        mac_address=mac,
                        interface=interface
                    ))
        
        except Exception:
            pass
        
        return entries


# ==================== TOOL CLASS ====================

class ARPTool:
    """
    ARP table viewer tool.
    
    Features:
    - Displays system ARP cache
    - IP to MAC address mappings
    - Interface information
    - Entry type/status (dynamic/static/reachable)
    - Cross-platform support
    - CLI and GUI support
    """
    
    NAME = "ARP Table"
    DESCRIPTION = "View ARP cache with IP-to-MAC address mappings"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
    
    def run(self, params: Dict[str, Any]) -> ARPResult:
        """Collect ARP table."""
        if self.logger:
            self.logger.info("Collecting ARP table...")
        
        result = ARPCollector.collect()
        
        if self.logger:
            if result.success:
                self.logger.info(f"  Found {len(result.entries)} ARP entries")
            else:
                self.logger.error(f"  FAILED: {result.error}")
        
        return result
    
    def get_gui_panel(self, parent) -> Optional["QWidget"]:
        """Return PyQt6 widget for this tool's GUI."""
        if not HAS_PYQT6:
            return None
        
        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        
        # Title
        title = QLabel(f"<h2>{self.NAME}</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Info label
        info_label = QLabel("Displays the system's ARP cache (IP-to-MAC address mappings)")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        # Refresh button
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(lambda: self._on_refresh_clicked(
            arp_table, status_label, btn_refresh
        ))
        layout.addWidget(btn_refresh)
        
        # Status label
        status_label = QLabel()
        layout.addWidget(status_label)
        
        # ARP table
        arp_table = QTableWidget(0, 4)
        arp_table.setHorizontalHeaderLabels(["IP Address", "MAC Address", "Interface", "Type/Status"])
        arp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(arp_table, 1)
        
        # Auto-load on creation
        self._load_arp_table(arp_table, status_label)
        
        return widget
    
    def _on_refresh_clicked(self, arp_table, status_label, btn_refresh):
        """Handle refresh button click."""
        btn_refresh.setEnabled(False)
        btn_refresh.setText("Loading...")
        
        self._load_arp_table(arp_table, status_label)
        
        btn_refresh.setEnabled(True)
        btn_refresh.setText("🔄 Refresh")
    
    def _load_arp_table(self, arp_table, status_label):
        """Load ARP table into GUI."""
        result = self.run({})
        
        # Clear table
        arp_table.setRowCount(0)
        
        if result.success:
            # Populate table
            for entry in result.entries:
                row = arp_table.rowCount()
                arp_table.insertRow(row)
                
                arp_table.setItem(row, 0, QTableWidgetItem(entry.ip_address))
                arp_table.setItem(row, 1, QTableWidgetItem(entry.mac_address))
                arp_table.setItem(row, 2, QTableWidgetItem(entry.interface or "—"))
                arp_table.setItem(row, 3, QTableWidgetItem(entry.type_status or "—"))
            
            status_label.setText(f"✅ {len(result.entries)} ARP entries")
        else:
            status_label.setText(f"❌ Error: {result.error}")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "--format", "-f",
            choices=["text", "json"],
            default="text",
            help="Output format"
        )
    
    def cli_handler(self, args, logger) -> int:
        """Handle CLI execution."""
        self.logger = logger
        
        try:
            result = self.run({})
            
            if args.format == "json":
                import json
                from dataclasses import asdict
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"\n📋 ARP Table")
                print("=" * 80)
                print(f"{'IP Address':<18} {'MAC Address':<20} {'Interface':<15} {'Type/Status'}")
                print("-" * 80)
                
                for entry in result.entries:
                    interface = entry.interface or "—"
                    type_status = entry.type_status or "—"
                    
                    print(f"{entry.ip_address:<18} {entry.mac_address:<20} {interface:<15} {type_status}")
                
                print(f"\nTotal: {len(result.entries)} entries")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"ARP collection failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return ARPTool()
