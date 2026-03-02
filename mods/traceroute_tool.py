"""
Traceroute Tool - Route tracing with hop-by-hop analysis.

Cross-platform traceroute implementation with output parsing for Windows (tracert),
Linux, and macOS (traceroute). Displays each hop with latency measurements.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import platform
import re
import subprocess
import time

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem, 
        QGroupBox, QMessageBox, QHeaderView
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== DATA MODEL ====================

@dataclass
class TracerouteHop:
    """Single hop in traceroute."""
    hop_num: int
    ip_address: Optional[str] = None
    hostname: Optional[str] = None
    rtt1_ms: Optional[float] = None
    rtt2_ms: Optional[float] = None
    rtt3_ms: Optional[float] = None
    timeout: bool = False


@dataclass
class TracerouteResult:
    """Traceroute result."""
    host: str
    max_hops: int
    hops: List[TracerouteHop] = field(default_factory=list)
    reached_target: bool = False
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== TRACEROUTE EXECUTOR ====================

class TracerouteExecutor:
    """Cross-platform traceroute execution and parsing."""
    
    @staticmethod
    def execute(host: str, max_hops: int = 30, timeout: int = 60) -> TracerouteResult:
        """Execute traceroute command and parse results."""
        result = TracerouteResult(
            host=host,
            max_hops=max_hops,
            timestamp=time.time()
        )
        
        system = platform.system()
        
        try:
            # Build command based on platform
            if system == "Windows":
                cmd = ["tracert", "-h", str(max_hops), "-w", "3000", host]
            else:  # Linux, macOS
                cmd = ["traceroute", "-m", str(max_hops), "-w", "3", host]
            
            # Execute
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Collect output
            stdout_lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    stdout_lines.append(line)
            
            proc.wait(timeout=timeout)
            
            # Parse output
            if proc.returncode == 0 or stdout_lines:  # traceroute may return non-zero even on success
                result.success = True
                TracerouteExecutor._parse_output(result, stdout_lines, system)
            else:
                stderr_output = proc.stderr.read()
                result.error = stderr_output or "Traceroute failed"
                result.success = False
        
        except subprocess.TimeoutExpired:
            result.error = "Traceroute timeout"
            result.success = False
        except FileNotFoundError:
            result.error = f"Traceroute command not found. Install: {TracerouteExecutor._get_install_hint(system)}"
            result.success = False
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        return result
    
    @staticmethod
    def _get_install_hint(system: str) -> str:
        """Get installation hint for traceroute."""
        if system == "Linux":
            return "apt install traceroute or yum install traceroute"
        elif system == "Darwin":
            return "traceroute (should be pre-installed)"
        else:
            return "tracert (should be pre-installed)"
    
    @staticmethod
    def _parse_output(result: TracerouteResult, lines: List[str], system: str):
        """Parse traceroute output."""
        if system == "Windows":
            TracerouteExecutor._parse_windows(result, lines)
        else:
            TracerouteExecutor._parse_unix(result, lines)
    
    @staticmethod
    def _parse_windows(result: TracerouteResult, lines: List[str]):
        """Parse Windows tracert output."""
        # Skip header lines
        parsing = False
        
        for line in lines:
            # Start parsing after header
            if not parsing:
                if "Tracing route" in line or line.strip().startswith("1 "):
                    parsing = True
                    if not line.strip().startswith("1 "):
                        continue
                else:
                    continue
            
            # Parse hop line: "  1    <1 ms    <1 ms    <1 ms  192.168.1.1"
            # or: "  2     *        *        *     Request timed out."
            match = re.match(r'\s*(\d+)\s+(.+)$', line)
            if not match:
                continue
            
            hop_num = int(match.group(1))
            rest = match.group(2).strip()
            
            hop = TracerouteHop(hop_num=hop_num)
            
            # Check for timeout
            if "*" in rest or "Request timed out" in rest:
                hop.timeout = True
            else:
                # Extract RTT values and IP/hostname
                # Pattern: "<1 ms    <1 ms    <1 ms  192.168.1.1" or "1 ms     2 ms     1 ms  example.com [1.2.3.4]"
                rtt_pattern = r'(\d+|<\d+)\s*ms'
                rtts = re.findall(rtt_pattern, rest)
                
                if rtts:
                    try:
                        hop.rtt1_ms = float(rtts[0].replace('<', '')) if len(rtts) > 0 else None
                        hop.rtt2_ms = float(rtts[1].replace('<', '')) if len(rtts) > 1 else None
                        hop.rtt3_ms = float(rtts[2].replace('<', '')) if len(rtts) > 2 else None
                    except ValueError:
                        pass
                
                # Extract IP/hostname (last part after RTTs)
                # Look for IP address pattern
                ip_match = re.search(r'\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b', rest)
                if ip_match:
                    hop.ip_address = ip_match.group(1)
                    
                    # Check for hostname before IP
                    hostname_match = re.search(r'(\S+)\s+\[' + re.escape(hop.ip_address) + r'\]', rest)
                    if hostname_match:
                        hop.hostname = hostname_match.group(1)
            
            result.hops.append(hop)
            
            # Check if reached target
            if hop.ip_address and hop.ip_address in result.host:
                result.reached_target = True
    
    @staticmethod
    def _parse_unix(result: TracerouteResult, lines: List[str]):
        """Parse Unix/Linux/macOS traceroute output."""
        for line in lines:
            # Parse hop line: " 1  192.168.1.1 (192.168.1.1)  0.5 ms  0.4 ms  0.3 ms"
            # or: " 2  * * *"
            match = re.match(r'\s*(\d+)\s+(.+)$', line)
            if not match:
                continue
            
            hop_num = int(match.group(1))
            rest = match.group(2).strip()
            
            hop = TracerouteHop(hop_num=hop_num)
            
            # Check for timeout
            if rest.strip() == "* * *" or rest.count('*') >= 3:
                hop.timeout = True
            else:
                # Extract hostname/IP
                # Pattern: "hostname (1.2.3.4)" or "1.2.3.4"
                host_match = re.match(r'(\S+)\s+\(([^)]+)\)', rest)
                if host_match:
                    hop.hostname = host_match.group(1)
                    hop.ip_address = host_match.group(2)
                else:
                    ip_match = re.match(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', rest)
                    if ip_match:
                        hop.ip_address = ip_match.group(1)
                
                # Extract RTT values
                rtt_pattern = r'([\d.]+)\s*ms'
                rtts = re.findall(rtt_pattern, rest)
                
                try:
                    hop.rtt1_ms = float(rtts[0]) if len(rtts) > 0 else None
                    hop.rtt2_ms = float(rtts[1]) if len(rtts) > 1 else None
                    hop.rtt3_ms = float(rtts[2]) if len(rtts) > 2 else None
                except (ValueError, IndexError):
                    pass
            
            result.hops.append(hop)
            
            # Check if reached target
            if hop.ip_address and hop.ip_address in result.host:
                result.reached_target = True
            elif hop.hostname and hop.hostname in result.host:
                result.reached_target = True


# ==================== BACKGROUND TRACEROUTE THREAD ====================

if HAS_PYQT6:
    class TracerouteThread(QThread):
        """Background traceroute thread."""
        traceroute_complete = pyqtSignal(object)
        traceroute_error = pyqtSignal(str)
        
        def __init__(self, host: str, max_hops: int):
            super().__init__()
            self.host = host
            self.max_hops = max_hops
        
        def run(self):
            """Run traceroute in background."""
            try:
                result = TracerouteExecutor.execute(self.host, self.max_hops)
                self.traceroute_complete.emit(result)
            except Exception as e:
                self.traceroute_error.emit(str(e))


# ==================== TOOL CLASS ====================

class TracerouteTool:
    """
    Network route tracing tool.
    
    Features:
    - Cross-platform (Windows tracert, Unix traceroute)
    - Hop-by-hop display with latency
    - Configurable max hops
    - Timeout handling for unresponsive hops
    - CLI and GUI support
    """
    
    NAME = "Traceroute"
    DESCRIPTION = "Trace network route to destination with hop-by-hop analysis"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
        self.traceroute_thread = None  # Keep reference to prevent garbage collection
    
    def run(self, params: Dict[str, Any]) -> TracerouteResult:
        """Execute traceroute."""
        host = params.get("host", "")
        max_hops = params.get("max_hops", 30)
        
        if not host:
            raise ValueError("Host is required")
        
        if self.logger:
            self.logger.info(f"Traceroute: {host} (max_hops={max_hops})")
        
        result = TracerouteExecutor.execute(host, max_hops)
        
        if self.logger:
            if result.success:
                self.logger.info(f"  Traced {len(result.hops)} hops, "
                               f"reached_target={result.reached_target}")
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
        
        # Input section
        input_group = QGroupBox("Traceroute Configuration")
        input_layout = QHBoxLayout()
        
        input_layout.addWidget(QLabel("Host:"))
        host_input = QLineEdit()
        host_input.setPlaceholderText("8.8.8.8 or example.com")
        input_layout.addWidget(host_input, 1)
        
        input_layout.addWidget(QLabel("Max Hops:"))
        hops_spin = QSpinBox()
        hops_spin.setRange(1, 64)
        hops_spin.setValue(30)
        input_layout.addWidget(hops_spin)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Traceroute button
        btn_trace = QPushButton("🔍 Trace Route")
        btn_trace.clicked.connect(lambda: self._on_trace_clicked(
            host_input, hops_spin, hops_table, status_label, btn_trace
        ))
        layout.addWidget(btn_trace)
        
        # Status label
        status_label = QLabel()
        status_label.setStyleSheet("padding: 5px;")
        layout.addWidget(status_label)
        
        # Hops table
        hops_table = QTableWidget(0, 6)
        hops_table.setHorizontalHeaderLabels(["Hop", "IP Address", "Hostname", "RTT1", "RTT2", "RTT3"])
        hops_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        hops_table.setColumnWidth(0, 60)
        hops_table.setColumnWidth(3, 80)
        hops_table.setColumnWidth(4, 80)
        hops_table.setColumnWidth(5, 80)
        layout.addWidget(hops_table, 1)
        
        return widget
    
    def _on_trace_clicked(self, host_input, hops_spin, hops_table, status_label, btn_trace):
        """Handle GUI trace button click."""
        host = host_input.text().strip()
        if not host:
            QMessageBox.warning(None, "Input Required", "Please enter a host.")
            return
        
        max_hops = hops_spin.value()
        
        # Disable button
        btn_trace.setEnabled(False)
        btn_trace.setText("Tracing...")
        
        # Clear table and status
        hops_table.setRowCount(0)
        status_label.setText("⏳ Running traceroute...")
        
        # Start traceroute thread (keep reference to prevent garbage collection)
        self.traceroute_thread = TracerouteThread(host, max_hops)
        self.traceroute_thread.traceroute_complete.connect(lambda result: self._on_trace_complete(
            result, hops_table, status_label, btn_trace
        ))
        self.traceroute_thread.traceroute_error.connect(lambda error: self._on_trace_error(
            error, status_label, btn_trace
        ))
        self.traceroute_thread.finished.connect(self.traceroute_thread.deleteLater)
        self.traceroute_thread.start()
    
    def _on_trace_complete(self, result: TracerouteResult, hops_table, status_label, btn_trace):
        """Handle traceroute completion."""
        if result.success:
            # Populate table
            for hop in result.hops:
                row = hops_table.rowCount()
                hops_table.insertRow(row)
                
                # Hop number
                hops_table.setItem(row, 0, QTableWidgetItem(str(hop.hop_num)))
                
                # IP address
                ip_text = hop.ip_address or ("*" if hop.timeout else "—")
                hops_table.setItem(row, 1, QTableWidgetItem(ip_text))
                
                # Hostname
                hostname_text = hop.hostname or "—"
                hops_table.setItem(row, 2, QTableWidgetItem(hostname_text))
                
                # RTTs
                rtt1_text = f"{hop.rtt1_ms:.1f} ms" if hop.rtt1_ms is not None else ("*" if hop.timeout else "—")
                rtt2_text = f"{hop.rtt2_ms:.1f} ms" if hop.rtt2_ms is not None else ("*" if hop.timeout else "—")
                rtt3_text = f"{hop.rtt3_ms:.1f} ms" if hop.rtt3_ms is not None else ("*" if hop.timeout else "—")
                
                hops_table.setItem(row, 3, QTableWidgetItem(rtt1_text))
                hops_table.setItem(row, 4, QTableWidgetItem(rtt2_text))
                hops_table.setItem(row, 5, QTableWidgetItem(rtt3_text))
            
            # Status
            status_text = f"✅ Traced {len(result.hops)} hops"
            if result.reached_target:
                status_text += " - Target reached"
            else:
                status_text += " - Target not reached"
            
            status_label.setText(status_text)
        else:
            status_label.setText(f"❌ Traceroute failed: {result.error}")
        
        # Re-enable button
        btn_trace.setEnabled(True)
        btn_trace.setText("🔍 Trace Route")
    
    def _on_trace_error(self, error: str, status_label, btn_trace):
        """Handle traceroute error."""
        status_label.setText(f"❌ Error: {error}")
        btn_trace.setEnabled(True)
        btn_trace.setText("🔍 Trace Route")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "host",
            help="Destination host (IP address or hostname)"
        )
        subparser.add_argument(
            "--max-hops", "-m",
            type=int,
            default=30,
            help="Maximum number of hops (default: 30)"
        )
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
            result = self.run({
                "host": args.host,
                "max_hops": args.max_hops
            })
            
            if args.format == "json":
                import json
                from dataclasses import asdict
                print(json.dumps(asdict(result), indent=2, default=str))
            else:
                print(f"\n🔍 Traceroute to {args.host} (max {args.max_hops} hops):")
                print("=" * 80)
                print(f"{'Hop':<5} {'IP Address':<18} {'Hostname':<25} {'RTT1':>10} {'RTT2':>10} {'RTT3':>10}")
                print("-" * 80)
                
                for hop in result.hops:
                    ip = hop.ip_address or "*"
                    hostname = hop.hostname or "—"
                    rtt1 = f"{hop.rtt1_ms:.1f}ms" if hop.rtt1_ms else "*"
                    rtt2 = f"{hop.rtt2_ms:.1f}ms" if hop.rtt2_ms else "*"
                    rtt3 = f"{hop.rtt3_ms:.1f}ms" if hop.rtt3_ms else "*"
                    
                    print(f"{hop.hop_num:<5} {ip:<18} {hostname:<25} {rtt1:>10} {rtt2:>10} {rtt3:>10}")
                
                print()
                if result.reached_target:
                    print("✅ Target reached")
                else:
                    print("⚠️  Target not reached")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"Traceroute failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return TracerouteTool()
