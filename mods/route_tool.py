"""
Route Tool - Routing table viewer and analyzer.

Displays the system's routing table showing how network packets are routed,
including destination networks, gateways, interfaces, and metrics.
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
class RouteEntry:
    """Single routing table entry."""
    destination: str
    gateway: str
    netmask: Optional[str] = None
    interface: Optional[str] = None
    metric: Optional[int] = None
    flags: Optional[str] = None


@dataclass
class RouteResult:
    """Routing table result."""
    entries: List[RouteEntry] = field(default_factory=list)
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== ROUTE COLLECTOR ====================

class RouteCollector:
    """Collect routing table entries."""
    
    @staticmethod
    def collect() -> RouteResult:
        """Collect routing table."""
        import time
        result = RouteResult(timestamp=time.time())
        
        system = platform.system()
        
        try:
            if system == "Windows":
                result.entries = RouteCollector._collect_windows()
            elif system == "Linux":
                result.entries = RouteCollector._collect_linux()
            elif system == "Darwin":
                result.entries = RouteCollector._collect_macos()
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
    def _collect_windows() -> List[RouteEntry]:
        """Collect routing table on Windows using route print."""
        entries = []
        
        try:
            proc = subprocess.run(
                ["route", "print"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                in_ipv4_section = False
                
                for line in proc.stdout.splitlines():
                    # Look for IPv4 Route Table section
                    if "IPv4 Route Table" in line:
                        in_ipv4_section = True
                        continue
                    
                    # End of IPv4 section
                    if in_ipv4_section and ("IPv6" in line or "Persistent Routes" in line):
                        break
                    
                    # Parse route entries
                    if in_ipv4_section:
                        # Format: "  0.0.0.0          0.0.0.0      192.168.1.1    192.168.1.100     25"
                        parts = line.split()
                        if len(parts) >= 4:
                            # Check if first part looks like an IP or network
                            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', parts[0]):
                                destination = parts[0]
                                netmask = parts[1] if len(parts) > 1 else None
                                gateway = parts[2] if len(parts) > 2 else None
                                interface = parts[3] if len(parts) > 3 else None
                                metric = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
                                
                                entries.append(RouteEntry(
                                    destination=destination,
                                    netmask=netmask,
                                    gateway=gateway,
                                    interface=interface,
                                    metric=metric
                                ))
        
        except Exception:
            pass
        
        return entries
    
    @staticmethod
    def _collect_linux() -> List[RouteEntry]:
        """Collect routing table on Linux using ip route."""
        entries = []
        
        # Try ip route first (modern Linux)
        try:
            proc = subprocess.run(
                ["ip", "route", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    # Format: "default via 192.168.1.1 dev eth0 proto dhcp metric 100"
                    # or: "192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100 metric 100"
                    
                    parts = line.split()
                    if not parts:
                        continue
                    
                    destination = parts[0]
                    gateway = None
                    interface = None
                    metric = None
                    
                    # Parse tokens
                    for i, part in enumerate(parts):
                        if part == "via" and i + 1 < len(parts):
                            gateway = parts[i + 1]
                        elif part == "dev" and i + 1 < len(parts):
                            interface = parts[i + 1]
                        elif part == "metric" and i + 1 < len(parts):
                            try:
                                metric = int(parts[i + 1])
                            except ValueError:
                                pass
                    
                    # Default gateway if none specified
                    if not gateway:
                        gateway = "0.0.0.0" if destination != "default" else None
                    
                    entries.append(RouteEntry(
                        destination=destination,
                        gateway=gateway or "—",
                        interface=interface,
                        metric=metric
                    ))
                
                return entries
        
        except FileNotFoundError:
            pass
        
        # Fallback to route command
        try:
            proc = subprocess.run(
                ["route", "-n"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                for line in proc.stdout.splitlines()[2:]:  # Skip headers
                    parts = line.split()
                    if len(parts) >= 7:
                        entries.append(RouteEntry(
                            destination=parts[0],
                            gateway=parts[1],
                            netmask=parts[2],
                            flags=parts[3],
                            metric=int(parts[4]) if parts[4].isdigit() else None,
                            interface=parts[7] if len(parts) > 7 else None
                        ))
        
        except Exception:
            pass
        
        return entries
    
    @staticmethod
    def _collect_macos() -> List[RouteEntry]:
        """Collect routing table on macOS using netstat -nr."""
        entries = []
        
        try:
            proc = subprocess.run(
                ["netstat", "-nr", "-f", "inet"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                in_route_table = False
                
                for line in proc.stdout.splitlines():
                    # Look for routing table header
                    if "Destination" in line and "Gateway" in line:
                        in_route_table = True
                        continue
                    
                    # Parse routes
                    if in_route_table:
                        parts = line.split()
                        if len(parts) >= 4:
                            # Check if first part is a destination
                            if re.match(r'^(default|\d+\.|\d{1,3}\.\d{1,3})', parts[0]):
                                destination = parts[0]
                                gateway = parts[1]
                                flags = parts[2] if len(parts) > 2 else None
                                interface = parts[3] if len(parts) > 3 else None
                                
                                entries.append(RouteEntry(
                                    destination=destination,
                                    gateway=gateway,
                                    flags=flags,
                                    interface=interface
                                ))
        
        except Exception:
            pass
        
        return entries


# ==================== TOOL CLASS ====================

class RouteTool:
    """
    Routing table viewer tool.
    
    Features:
    - Displays system routing table
    - Destination networks and gateways
    - Network interfaces for each route
    - Route metrics and flags
    - Default route highlighting
    - Cross-platform support
    - CLI and GUI support
    """
    
    NAME = "Routing Table"
    DESCRIPTION = "View system routing table with destinations and gateways"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
    
    def run(self, params: Dict[str, Any]) -> RouteResult:
        """Collect routing table."""
        if self.logger:
            self.logger.info("Collecting routing table...")
        
        result = RouteCollector.collect()
        
        if self.logger:
            if result.success:
                self.logger.info(f"  Found {len(result.entries)} routing entries")
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
        info_label = QLabel("Displays the system's routing table showing how packets are routed")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
        
        # Refresh button
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(lambda: self._on_refresh_clicked(
            route_table, status_label, btn_refresh
        ))
        layout.addWidget(btn_refresh)
        
        # Status label
        status_label = QLabel()
        layout.addWidget(status_label)
        
        # Route table
        route_table = QTableWidget(0, 6)
        route_table.setHorizontalHeaderLabels(["Destination", "Gateway", "Netmask", "Interface", "Metric", "Flags"])
        route_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(route_table, 1)
        
        # Auto-load on creation
        self._load_route_table(route_table, status_label)
        
        return widget
    
    def _on_refresh_clicked(self, route_table, status_label, btn_refresh):
        """Handle refresh button click."""
        btn_refresh.setEnabled(False)
        btn_refresh.setText("Loading...")
        
        self._load_route_table(route_table, status_label)
        
        btn_refresh.setEnabled(True)
        btn_refresh.setText("🔄 Refresh")
    
    def _load_route_table(self, route_table, status_label):
        """Load routing table into GUI."""
        result = self.run({})
        
        # Clear table
        route_table.setRowCount(0)
        
        if result.success:
            # Populate table
            for entry in result.entries:
                row = route_table.rowCount()
                route_table.insertRow(row)
                
                route_table.setItem(row, 0, QTableWidgetItem(entry.destination))
                route_table.setItem(row, 1, QTableWidgetItem(entry.gateway))
                route_table.setItem(row, 2, QTableWidgetItem(entry.netmask or "—"))
                route_table.setItem(row, 3, QTableWidgetItem(entry.interface or "—"))
                route_table.setItem(row, 4, QTableWidgetItem(str(entry.metric) if entry.metric else "—"))
                route_table.setItem(row, 5, QTableWidgetItem(entry.flags or "—"))
            
            status_label.setText(f"✅ {len(result.entries)} routing entries")
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
                print(f"\n🛣️  Routing Table")
                print("=" * 100)
                print(f"{'Destination':<20} {'Gateway':<18} {'Netmask':<18} {'Interface':<15} {'Metric':<8} {'Flags'}")
                print("-" * 100)
                
                for entry in result.entries:
                    destination = entry.destination
                    gateway = entry.gateway
                    netmask = entry.netmask or "—"
                    interface = entry.interface or "—"
                    metric = str(entry.metric) if entry.metric else "—"
                    flags = entry.flags or "—"
                    
                    print(f"{destination:<20} {gateway:<18} {netmask:<18} {interface:<15} {metric:<8} {flags}")
                
                print(f"\nTotal: {len(result.entries)} routes")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"Route collection failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return RouteTool()
