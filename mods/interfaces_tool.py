"""
Network Interfaces Tool - Display local network interfaces with configuration.

Shows all network interfaces with IP addresses, MAC addresses, MTU, status,
and gateway/DNS information. Uses psutil with fallback to system commands.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import platform
import re
import socket
import subprocess

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QTableWidget, QTableWidgetItem, QGroupBox, QTextEdit, QHeaderView
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

# Try to import psutil
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ==================== DATA MODEL ====================

@dataclass
class InterfaceInfo:
    """Network interface information."""
    name: str
    ip_addresses: List[str] = field(default_factory=list)
    mac_address: Optional[str] = None
    mtu: Optional[int] = None
    status: Optional[str] = None
    is_up: bool = False
    is_loopback: bool = False


@dataclass
class NetworkInfo:
    """Complete network information."""
    interfaces: List[InterfaceInfo] = field(default_factory=list)
    default_gateway: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    hostname: Optional[str] = None
    success: bool = True
    error: Optional[str] = None


# ==================== INTERFACE COLLECTOR ====================

class InterfaceCollector:
    """Collect network interface information."""
    
    @staticmethod
    def collect() -> NetworkInfo:
        """Collect all network information."""
        info = NetworkInfo()
        
        try:
            # Get hostname
            info.hostname = socket.gethostname()
            
            # Collect interfaces
            if HAS_PSUTIL:
                info.interfaces = InterfaceCollector._collect_with_psutil()
            else:
                info.interfaces = InterfaceCollector._collect_with_commands()
            
            # Collect gateway and DNS
            info.default_gateway = InterfaceCollector._get_default_gateway()
            info.dns_servers = InterfaceCollector._get_dns_servers()
            
            info.success = True
        
        except Exception as e:
            info.error = str(e)
            info.success = False
        
        return info
    
    @staticmethod
    def _collect_with_psutil() -> List[InterfaceInfo]:
        """Collect using psutil library."""
        interfaces = []
        
        # Get addresses
        addrs = psutil.net_if_addrs()
        # Get stats
        stats = psutil.net_if_stats()
        
        for name, addr_list in addrs.items():
            iface = InterfaceInfo(name=name)
            
            # Get addresses
            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    iface.ip_addresses.append(addr.address)
                elif addr.family == psutil.AF_LINK:
                    iface.mac_address = addr.address
            
            # Get stats
            if name in stats:
                stat = stats[name]
                iface.is_up = stat.isup
                iface.mtu = stat.mtu
                iface.status = "UP" if stat.isup else "DOWN"
            
            # Check if loopback
            iface.is_loopback = name.startswith('lo') or 'loopback' in name.lower()
            
            interfaces.append(iface)
        
        return interfaces
    
    @staticmethod
    def _collect_with_commands() -> List[InterfaceInfo]:
        """Collect using system commands."""
        system = platform.system()
        
        if system == "Windows":
            return InterfaceCollector._collect_windows()
        elif system == "Linux":
            return InterfaceCollector._collect_linux()
        elif system == "Darwin":
            return InterfaceCollector._collect_macos()
        else:
            return []
    
    @staticmethod
    def _collect_windows() -> List[InterfaceInfo]:
        """Collect interfaces on Windows using ipconfig."""
        interfaces = []
        
        try:
            result = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                current_iface = None
                
                for line in result.stdout.splitlines():
                    # New adapter
                    if "adapter" in line.lower() and ":" in line:
                        if current_iface:
                            interfaces.append(current_iface)
                        
                        name = line.split("adapter", 1)[1].split(":")[0].strip()
                        current_iface = InterfaceInfo(name=name)
                    
                    elif current_iface:
                        # IPv4 Address
                        if "IPv4 Address" in line or "IP Address" in line:
                            match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                            if match:
                                current_iface.ip_addresses.append(match.group(1))
                        
                        # MAC Address
                        elif "Physical Address" in line:
                            match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', line)
                            if match:
                                current_iface.mac_address = match.group(0)
                
                if current_iface:
                    interfaces.append(current_iface)
        
        except Exception:
            pass
        
        return interfaces
    
    @staticmethod
    def _collect_linux() -> List[InterfaceInfo]:
        """Collect interfaces on Linux using ip command."""
        interfaces = []
        
        try:
            result = subprocess.run(
                ["ip", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                current_iface = None
                
                for line in result.stdout.splitlines():
                    # New interface
                    match = re.match(r'^\d+:\s+(\S+):', line)
                    if match:
                        if current_iface:
                            interfaces.append(current_iface)
                        
                        name = match.group(1)
                        current_iface = InterfaceInfo(name=name)
                        
                        # Status and MTU
                        if "state UP" in line:
                            current_iface.is_up = True
                            current_iface.status = "UP"
                        else:
                            current_iface.status = "DOWN"
                        
                        mtu_match = re.search(r'mtu\s+(\d+)', line)
                        if mtu_match:
                            current_iface.mtu = int(mtu_match.group(1))
                    
                    elif current_iface:
                        # MAC address
                        if "link/ether" in line:
                            match = re.search(r'([0-9a-f]{2}:){5}[0-9a-f]{2}', line)
                            if match:
                                current_iface.mac_address = match.group(0)
                        
                        # IP address
                        elif "inet " in line:
                            match = re.search(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                            if match:
                                current_iface.ip_addresses.append(match.group(1))
                
                if current_iface:
                    interfaces.append(current_iface)
        
        except Exception:
            pass
        
        return interfaces
    
    @staticmethod
    def _collect_macos() -> List[InterfaceInfo]:
        """Collect interfaces on macOS using ifconfig."""
        interfaces = []
        
        try:
            result = subprocess.run(
                ["ifconfig"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                current_iface = None
                
                for line in result.stdout.splitlines():
                    # New interface
                    if line and not line.startswith('\t') and not line.startswith(' '):
                        if current_iface:
                            interfaces.append(current_iface)
                        
                        name = line.split(':')[0].strip()
                        current_iface = InterfaceInfo(name=name)
                        
                        # Status
                        if "UP" in line:
                            current_iface.is_up = True
                            current_iface.status = "UP"
                        else:
                            current_iface.status = "DOWN"
                        
                        # MTU
                        mtu_match = re.search(r'mtu\s+(\d+)', line)
                        if mtu_match:
                            current_iface.mtu = int(mtu_match.group(1))
                    
                    elif current_iface:
                        # MAC address
                        if "ether" in line:
                            match = re.search(r'([0-9a-f]{2}:){5}[0-9a-f]{2}', line)
                            if match:
                                current_iface.mac_address = match.group(0)
                        
                        # IP address
                        elif "inet " in line:
                            match = re.search(r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                            if match:
                                current_iface.ip_addresses.append(match.group(1))
                
                if current_iface:
                    interfaces.append(current_iface)
        
        except Exception:
            pass
        
        return interfaces
    
    @staticmethod
    def _get_default_gateway() -> Optional[str]:
        """Get default gateway IP."""
        system = platform.system()
        
        try:
            if system == "Windows":
                result = subprocess.run(
                    ["ipconfig"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                for line in result.stdout.splitlines():
                    if "Default Gateway" in line:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if match:
                            return match.group(1)
            
            elif system == "Linux":
                result = subprocess.run(
                    ["ip", "route", "show", "default"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                match = re.search(r'default via (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result.stdout)
                if match:
                    return match.group(1)
            
            elif system == "Darwin":
                result = subprocess.run(
                    ["route", "-n", "get", "default"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                for line in result.stdout.splitlines():
                    if "gateway:" in line:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if match:
                            return match.group(1)
        
        except Exception:
            pass
        
        return None
    
    @staticmethod
    def _get_dns_servers() -> List[str]:
        """Get DNS server IPs."""
        dns_servers = []
        system = platform.system()
        
        try:
            if system == "Windows":
                result = subprocess.run(
                    ["ipconfig", "/all"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                for line in result.stdout.splitlines():
                    if "DNS Servers" in line:
                        match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
                        if match:
                            dns_servers.append(match.group(1))
            
            elif system in ("Linux", "Darwin"):
                # Try /etc/resolv.conf
                try:
                    with open("/etc/resolv.conf", "r") as f:
                        for line in f:
                            if line.strip().startswith("nameserver"):
                                parts = line.split()
                                if len(parts) >= 2:
                                    dns_servers.append(parts[1])
                except FileNotFoundError:
                    pass
        
        except Exception:
            pass
        
        return dns_servers


# ==================== TOOL CLASS ====================

class InterfacesTool:
    """
    Network interfaces viewer tool.
    
    Features:
    - Lists all network interfaces
    - Shows IP addresses, MAC addresses, MTU
    - Interface status (UP/DOWN)
    - Default gateway information
    - DNS server configuration
    - Uses psutil with fallback to system commands
    - CLI and GUI support
    """
    
    NAME = "Network Interfaces"
    DESCRIPTION = "View local network interfaces with IP, MAC, MTU, and gateway info"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
    
    def run(self, params: Dict[str, Any]) -> NetworkInfo:
        """Collect network interface information."""
        if self.logger:
            self.logger.info("Collecting network interface information...")
        
        info = InterfaceCollector.collect()
        
        if self.logger:
            if info.success:
                self.logger.info(f"  Found {len(info.interfaces)} interfaces")
            else:
                self.logger.error(f"  FAILED: {info.error}")
        
        return info
    
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
        
        # Refresh button
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(lambda: self._on_refresh_clicked(
            iface_table, info_text, btn_refresh
        ))
        layout.addWidget(btn_refresh)
        
        # Interfaces table
        iface_table = QTableWidget(0, 5)
        iface_table.setHorizontalHeaderLabels(["Interface", "IP Address", "MAC Address", "MTU", "Status"])
        iface_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(iface_table, 1)
        
        # Network info
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Courier New", 9))
        info_text.setMaximumHeight(150)
        layout.addWidget(info_text)
        
        # Auto-load on creation
        self._load_interfaces(iface_table, info_text)
        
        return widget
    
    def _on_refresh_clicked(self, iface_table, info_text, btn_refresh):
        """Handle refresh button click."""
        btn_refresh.setEnabled(False)
        btn_refresh.setText("Loading...")
        
        self._load_interfaces(iface_table, info_text)
        
        btn_refresh.setEnabled(True)
        btn_refresh.setText("🔄 Refresh")
    
    def _load_interfaces(self, iface_table, info_text):
        """Load interface information into GUI."""
        result = self.run({})
        
        # Clear table
        iface_table.setRowCount(0)
        
        if result.success:
            # Populate table
            for iface in result.interfaces:
                row = iface_table.rowCount()
                iface_table.insertRow(row)
                
                iface_table.setItem(row, 0, QTableWidgetItem(iface.name))
                iface_table.setItem(row, 1, QTableWidgetItem(", ".join(iface.ip_addresses) if iface.ip_addresses else "—"))
                iface_table.setItem(row, 2, QTableWidgetItem(iface.mac_address or "—"))
                iface_table.setItem(row, 3, QTableWidgetItem(str(iface.mtu) if iface.mtu else "—"))
                iface_table.setItem(row, 4, QTableWidgetItem(iface.status or "—"))
            
            # Network info
            info_lines = []
            if result.hostname:
                info_lines.append(f"Hostname: {result.hostname}")
            if result.default_gateway:
                info_lines.append(f"Default Gateway: {result.default_gateway}")
            if result.dns_servers:
                info_lines.append(f"DNS Servers: {', '.join(result.dns_servers)}")
            
            info_text.setPlainText("\n".join(info_lines))
        else:
            info_text.setPlainText(f"Error: {result.error}")
    
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
                print(f"\n🖧  Network Interfaces")
                print("=" * 80)
                
                if result.hostname:
                    print(f"Hostname: {result.hostname}")
                if result.default_gateway:
                    print(f"Gateway:  {result.default_gateway}")
                if result.dns_servers:
                    print(f"DNS:      {', '.join(result.dns_servers)}")
                
                print("\n" + "-" * 80)
                print(f"{'Interface':<20} {'IP Address':<18} {'MAC Address':<20} {'MTU':<8} {'Status'}")
                print("-" * 80)
                
                for iface in result.interfaces:
                    ip_str = iface.ip_addresses[0] if iface.ip_addresses else "—"
                    mac_str = iface.mac_address or "—"
                    mtu_str = str(iface.mtu) if iface.mtu else "—"
                    status_str = iface.status or "—"
                    
                    print(f"{iface.name:<20} {ip_str:<18} {mac_str:<20} {mtu_str:<8} {status_str}")
                    
                    # Additional IPs
                    for ip in iface.ip_addresses[1:]:
                        print(f"{'':<20} {ip:<18}")
                
                print(f"\nTotal: {len(result.interfaces)} interfaces")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"Interface collection failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return InterfacesTool()
