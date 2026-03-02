"""
LAN Scan Tool - Safe local network discovery.

Performs controlled ping sweeps of private network ranges to discover active hosts.
Includes safety warnings, rate limiting, and private network validation.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import ipaddress
import logging
import re
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QTableWidget, QTableWidgetItem, QTextEdit,
        QGroupBox, QMessageBox, QProgressBar, QHeaderView
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== DATA MODEL ====================

@dataclass
class HostInfo:
    """Discovered host information."""
    ip_address: str
    hostname: Optional[str] = None
    response_time_ms: Optional[float] = None
    is_responding: bool = False


@dataclass
class LANScanResult:
    """LAN scan result."""
    network: str
    hosts: List[HostInfo] = field(default_factory=list)
    total_scanned: int = 0
    total_responding: int = 0
    scan_time_seconds: float = 0.0
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== NETWORK VALIDATOR ====================

class NetworkValidator:
    """Validate network ranges for safety."""
    
    # RFC1918 private network ranges
    PRIVATE_NETWORKS = [
        ipaddress.ip_network('10.0.0.0/8'),
        ipaddress.ip_network('172.16.0.0/12'),
        ipaddress.ip_network('192.168.0.0/16'),
        ipaddress.ip_network('127.0.0.0/8'),  # Loopback
    ]
    
    @staticmethod
    def is_private_network(network_str: str) -> bool:
        """Check if network is in private ranges."""
        try:
            network = ipaddress.ip_network(network_str, strict=False)
            
            for private_net in NetworkValidator.PRIVATE_NETWORKS:
                if network.subnet_of(private_net):
                    return True
            
            return False
        
        except ValueError:
            return False
    
    @staticmethod
    def validate_network(network_str: str) -> tuple[bool, str]:
        """Validate network string."""
        try:
            network = ipaddress.ip_network(network_str, strict=False)
            
            # Check if private
            if not NetworkValidator.is_private_network(network_str):
                return False, "Only private networks (RFC1918) are allowed for safety"
            
            # Check size (limit to /24 or smaller for safety)
            if network.num_addresses > 256:
                return False, "Network too large. Use /24 or smaller (max 256 hosts)"
            
            return True, ""
        
        except ValueError as e:
            return False, f"Invalid network format: {e}"


# ==================== LAN SCANNER ====================

class LANScanner:
    """Safe LAN network scanner."""
    
    @staticmethod
    def ping_host(ip_str: str, timeout: float = 1.0) -> HostInfo:
        """Ping a single host."""
        host = HostInfo(ip_address=ip_str)
        
        try:
            start = time.time()
            
            # Try single ping
            import platform
            system = platform.system()
            
            if system == "Windows":
                cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip_str]
            else:
                cmd = ["ping", "-c", "1", "-W", str(int(timeout)), ip_str]
            
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout + 1
            )
            
            if proc.returncode == 0:
                host.is_responding = True
                host.response_time_ms = (time.time() - start) * 1000
                
                # Try to get hostname
                try:
                    host.hostname = socket.gethostbyaddr(ip_str)[0]
                except (socket.herror, socket.timeout):
                    pass
        
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        return host
    
    @staticmethod
    def scan_network(network_str: str, max_workers: int = 20, logger: Optional[logging.Logger] = None) -> LANScanResult:
        """Scan a network for active hosts."""
        result = LANScanResult(
            network=network_str,
            timestamp=time.time()
        )
        
        # Validate network
        valid, error = NetworkValidator.validate_network(network_str)
        if not valid:
            result.error = error
            result.success = False
            return result
        
        try:
            network = ipaddress.ip_network(network_str, strict=False)
            hosts_to_scan = list(network.hosts())
            
            if not hosts_to_scan:
                # Single host network
                hosts_to_scan = [network.network_address]
            
            result.total_scanned = len(hosts_to_scan)
            
            if logger:
                logger.info(f"Scanning {result.total_scanned} hosts in {network_str}...")
            
            start_time = time.time()
            
            # Scan with thread pool
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(LANScanner.ping_host, str(ip)): ip 
                    for ip in hosts_to_scan
                }
                
                for future in as_completed(futures):
                    try:
                        host_info = future.result()
                        if host_info.is_responding:
                            result.hosts.append(host_info)
                            result.total_responding += 1
                    except Exception as e:
                        if logger:
                            logger.debug(f"Scan error: {e}")
            
            result.scan_time_seconds = time.time() - start_time
            result.success = True
            
            if logger:
                logger.info(f"Scan complete: {result.total_responding}/{result.total_scanned} hosts responding")
        
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        return result


# ==================== BACKGROUND SCAN THREAD ====================

if HAS_PYQT6:
    class LANScanThread(QThread):
        """Background LAN scan thread."""
        scan_complete = pyqtSignal(object)
        scan_error = pyqtSignal(str)
        scan_progress = pyqtSignal(int, int)  # current, total
        
        def __init__(self, network: str):
            super().__init__()
            self.network = network
        
        def run(self):
            """Run LAN scan in background."""
            try:
                result = LANScanner.scan_network(self.network)
                self.scan_complete.emit(result)
            except Exception as e:
                self.scan_error.emit(str(e))


# ==================== TOOL CLASS ====================

class LANScanTool:
    """
    LAN network discovery tool with safety features.
    
    Features:
    - Safe ping sweep of local networks
    - Private network validation (RFC1918 only)
    - Network size limits (/24 or smaller)
    - Rate-limited concurrent scanning
    - Hostname resolution for responding hosts
    - Response time measurement
    - Safety warnings in GUI
    - CLI and GUI support
    
    Safety:
    - Only scans private networks (10.x, 172.16-31.x, 192.168.x)
    - Limited to /24 or smaller (max 256 hosts)
    - Rate-limited to avoid network flooding
    - Requires explicit user confirmation in GUI
    """
    
    NAME = "LAN Scanner"
    DESCRIPTION = "Safe local network discovery (private networks only)"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
        self.scan_thread = None  # Keep reference to prevent garbage collection
    
    def run(self, params: Dict[str, Any]) -> LANScanResult:
        """Execute LAN scan."""
        network = params.get("network", "")
        
        if not network:
            raise ValueError("Network is required")
        
        if self.logger:
            self.logger.info(f"LAN Scan: {network}")
        
        result = LANScanner.scan_network(network, logger=self.logger)
        
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
        
        # Warning box
        warning_box = QGroupBox("⚠️ Safety Notice")
        warning_layout = QVBoxLayout()
        warning_text = QLabel(
            "• Only private networks (RFC1918) are allowed\n"
            "• Maximum scan size: /24 (256 hosts)\n"
            "• Rate-limited to avoid network flooding\n"
            "• Use responsibly on networks you own/control"
        )
        warning_text.setStyleSheet("color: #d97706; padding: 5px;")
        warning_layout.addWidget(warning_text)
        warning_box.setLayout(warning_layout)
        layout.addWidget(warning_box)
        
        # Input section
        input_group = QGroupBox("Network to Scan")
        input_layout = QVBoxLayout()
        
        network_layout = QHBoxLayout()
        network_layout.addWidget(QLabel("Network (CIDR):"))
        network_input = QLineEdit()
        network_input.setPlaceholderText("192.168.1.0/24")
        network_layout.addWidget(network_input, 1)
        input_layout.addLayout(network_layout)
        
        example_label = QLabel("Examples: 192.168.1.0/24, 10.0.0.0/24, 172.16.0.0/24")
        example_label.setStyleSheet("color: gray; font-size: 10px;")
        input_layout.addWidget(example_label)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Scan button
        btn_scan = QPushButton("🔍 Scan Network")
        btn_scan.clicked.connect(lambda: self._on_scan_clicked(
            network_input, hosts_table, status_label, btn_scan
        ))
        layout.addWidget(btn_scan)
        
        # Status and progress
        status_label = QLabel()
        status_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(status_label)
        
        # Results table
        hosts_table = QTableWidget(0, 3)
        hosts_table.setHorizontalHeaderLabels(["IP Address", "Hostname", "Response Time"])
        hosts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(hosts_table, 1)
        
        return widget
    
    def _on_scan_clicked(self, network_input, hosts_table, status_label, btn_scan):
        """Handle GUI scan button click."""
        network = network_input.text().strip()
        if not network:
            QMessageBox.warning(None, "Input Required", "Please enter a network in CIDR format (e.g., 192.168.1.0/24)")
            return
        
        # Validate before scanning
        valid, error = NetworkValidator.validate_network(network)
        if not valid:
            QMessageBox.critical(None, "Invalid Network", error)
            return
        
        # Confirmation dialog
        reply = QMessageBox.question(
            None,
            "Confirm Network Scan",
            f"Scan network {network}?\n\n"
            "This will send ping requests to all hosts in the network.\n"
            "Only proceed if you own/control this network.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable button
        btn_scan.setEnabled(False)
        btn_scan.setText("Scanning...")
        
        # Clear table
        hosts_table.setRowCount(0)
        status_label.setText("⏳ Scanning network...")
        
        # Start scan thread (keep reference to prevent garbage collection)
        self.scan_thread = LANScanThread(network)
        self.scan_thread.scan_complete.connect(lambda result: self._on_scan_complete(
            result, hosts_table, status_label, btn_scan
        ))
        self.scan_thread.scan_error.connect(lambda error: self._on_scan_error(
            error, status_label, btn_scan
        ))
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.start()
    
    def _on_scan_complete(self, result: LANScanResult, hosts_table, status_label, btn_scan):
        """Handle scan completion."""
        try:
            if result.success:
                # Populate table
                if result.hosts:
                    for host in sorted(result.hosts, key=lambda h: ipaddress.ip_address(h.ip_address)):
                        row = hosts_table.rowCount()
                        hosts_table.insertRow(row)
                        
                        hosts_table.setItem(row, 0, QTableWidgetItem(host.ip_address))
                        hosts_table.setItem(row, 1, QTableWidgetItem(host.hostname or "—"))
                        
                        response_time = f"{host.response_time_ms:.1f} ms" if host.response_time_ms else "—"
                        hosts_table.setItem(row, 2, QTableWidgetItem(response_time))
                
                status_label.setText(
                    f"✅ Scan complete: {result.total_responding}/{result.total_scanned} hosts responding "
                    f"({result.scan_time_seconds:.1f}s)"
                )
            else:
                status_label.setText(f"❌ Scan failed: {result.error}")
        except Exception as e:
            status_label.setText(f"❌ Error displaying results: {str(e)}")
            if self.logger:
                self.logger.error(f"Scan display error: {e}", exc_info=True)
        finally:
            # Always re-enable button
            btn_scan.setEnabled(True)
            btn_scan.setText("🔍 Scan Network")
    
    def _on_scan_error(self, error: str, status_label, btn_scan):
        """Handle scan error."""
        try:
            status_label.setText(f"❌ Error: {error}")
            if self.logger:
                self.logger.error(f"LAN scan error: {error}")
        finally:
            btn_scan.setEnabled(True)
            btn_scan.setText("🔍 Scan Network")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "network",
            help="Network to scan in CIDR format (e.g., 192.168.1.0/24)"
        )
        subparser.add_argument(
            "--format", "-f",
            choices=["text", "json"],
            default="text",
            help="Output format"
        )
        subparser.add_argument(
            "--confirm", "-y",
            action="store_true",
            help="Skip confirmation prompt (use with caution)"
        )
    
    def cli_handler(self, args, logger) -> int:
        """Handle CLI execution."""
        self.logger = logger
        
        try:
            # Validate network
            valid, error = NetworkValidator.validate_network(args.network)
            if not valid:
                print(f"❌ Invalid network: {error}")
                return 1
            
            # Confirmation (unless --confirm flag)
            if not args.confirm:
                print(f"\n⚠️  About to scan network: {args.network}")
                print("This will send ping requests to all hosts.")
                print("Only proceed if you own/control this network.")
                
                response = input("\nContinue? [y/N]: ").strip().lower()
                if response != 'y':
                    print("Scan cancelled.")
                    return 0
            
            # Run scan
            result = self.run({"network": args.network})
            
            if args.format == "json":
                import json
                from dataclasses import asdict
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"\n🔍 LAN Scan: {args.network}")
                print("=" * 80)
                print(f"{'IP Address':<18} {'Hostname':<30} {'Response Time'}")
                print("-" * 80)
                
                for host in sorted(result.hosts, key=lambda h: ipaddress.ip_address(h.ip_address)):
                    hostname = host.hostname or "—"
                    response_time = f"{host.response_time_ms:.1f} ms" if host.response_time_ms else "—"
                    
                    print(f"{host.ip_address:<18} {hostname:<30} {response_time}")
                
                print(f"\n📊 Summary:")
                print(f"  Total scanned:    {result.total_scanned}")
                print(f"  Responding hosts: {result.total_responding}")
                print(f"  Scan time:        {result.scan_time_seconds:.1f}s")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"LAN scan failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return LANScanTool()
