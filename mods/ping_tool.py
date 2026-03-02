"""
Ping Tool - ICMP echo test with statistics.

Cross-platform ping implementation with output parsing for Windows, Linux, and macOS.
Provides latency statistics, packet loss calculation, and live output display.
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
        QLineEdit, QSpinBox, QTextEdit, QGroupBox, QMessageBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== DATA MODEL ====================

@dataclass
class PingResult:
    """Ping test result."""
    host: str
    count: int
    sent: int = 0
    received: int = 0
    lost: int = 0
    loss_percent: float = 0.0
    min_ms: Optional[float] = None
    max_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    output_lines: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== PING EXECUTOR ====================

class PingExecutor:
    """Cross-platform ping execution and parsing."""
    
    @staticmethod
    def execute(host: str, count: int = 4, timeout: int = 30) -> PingResult:
        """Execute ping command and parse results."""
        result = PingResult(
            host=host,
            count=count,
            timestamp=time.time()
        )
        
        system = platform.system()
        
        try:
            # Build command based on platform
            if system == "Windows":
                cmd = ["ping", "-n", str(count), host]
            else:  # Linux, macOS
                cmd = ["ping", "-c", str(count), host]
            
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
                    result.output_lines.append(line)
                    stdout_lines.append(line)
            
            proc.wait(timeout=timeout)
            
            # Parse output
            if proc.returncode == 0:
                result.success = True
                PingExecutor._parse_output(result, stdout_lines, system)
            else:
                stderr_output = proc.stderr.read()
                result.error = stderr_output or "Ping failed"
                result.success = False
        
        except subprocess.TimeoutExpired:
            result.error = "Ping timeout"
            result.success = False
        except FileNotFoundError:
            result.error = "Ping command not found"
            result.success = False
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        return result
    
    @staticmethod
    def _parse_output(result: PingResult, lines: List[str], system: str):
        """Parse ping output for statistics."""
        if system == "Windows":
            PingExecutor._parse_windows(result, lines)
        else:
            PingExecutor._parse_unix(result, lines)
    
    @staticmethod
    def _parse_windows(result: PingResult, lines: List[str]):
        """Parse Windows ping output."""
        # Look for: "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)"
        for line in lines:
            if "Packets:" in line or "Sent =" in line:
                match = re.search(r"Sent\s*=\s*(\d+)", line)
                if match:
                    result.sent = int(match.group(1))
                
                match = re.search(r"Received\s*=\s*(\d+)", line)
                if match:
                    result.received = int(match.group(1))
                
                match = re.search(r"Lost\s*=\s*(\d+)", line)
                if match:
                    result.lost = int(match.group(1))
                
                match = re.search(r"(\d+)%\s*loss", line)
                if match:
                    result.loss_percent = float(match.group(1))
        
        # Look for: "Minimum = 1ms, Maximum = 2ms, Average = 1ms"
        for line in lines:
            if "Minimum" in line or "Average" in line:
                match = re.search(r"Minimum\s*=\s*(\d+)ms", line)
                if match:
                    result.min_ms = float(match.group(1))
                
                match = re.search(r"Maximum\s*=\s*(\d+)ms", line)
                if match:
                    result.max_ms = float(match.group(1))
                
                match = re.search(r"Average\s*=\s*(\d+)ms", line)
                if match:
                    result.avg_ms = float(match.group(1))
    
    @staticmethod
    def _parse_unix(result: PingResult, lines: List[str]):
        """Parse Unix/Linux/macOS ping output."""
        # Look for: "4 packets transmitted, 4 received, 0% packet loss"
        for line in lines:
            match = re.search(r"(\d+)\s+packets\s+transmitted", line)
            if match:
                result.sent = int(match.group(1))
            
            match = re.search(r"(\d+)\s+received", line)
            if match:
                result.received = int(match.group(1))
            
            match = re.search(r"(\d+(?:\.\d+)?)%\s+packet\s+loss", line)
            if match:
                result.loss_percent = float(match.group(1))
        
        result.lost = result.sent - result.received
        
        # Look for: "round-trip min/avg/max/stddev = 1.2/1.5/1.8/0.2 ms"
        for line in lines:
            match = re.search(r"min/avg/max(?:/\w+)?\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)", line)
            if match:
                result.min_ms = float(match.group(1))
                result.avg_ms = float(match.group(2))
                result.max_ms = float(match.group(3))


# ==================== BACKGROUND PING THREAD ====================

if HAS_PYQT6:
    class PingThread(QThread):
        """Background ping thread."""
        ping_complete = pyqtSignal(object)
        ping_error = pyqtSignal(str)
        ping_output = pyqtSignal(str)
        
        def __init__(self, host: str, count: int):
            super().__init__()
            self.host = host
            self.count = count
        
        def run(self):
            """Run ping in background."""
            try:
                result = PingExecutor.execute(self.host, self.count)
                
                # Emit output lines
                for line in result.output_lines:
                    self.ping_output.emit(line)
                
                self.ping_complete.emit(result)
            except Exception as e:
                self.ping_error.emit(str(e))


# ==================== TOOL CLASS ====================

class PingTool:
    """
    ICMP ping tool with statistics.
    
    Features:
    - Cross-platform (Windows, Linux, macOS)
    - Configurable packet count
    - Live output display in GUI
    - Statistics: min/max/avg latency, packet loss
    - CLI and GUI support
    """
    
    NAME = "Ping"
    DESCRIPTION = "ICMP echo test with packet loss and latency statistics"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
        self.ping_thread = None  # Keep reference to prevent garbage collection
    
    def run(self, params: Dict[str, Any]) -> PingResult:
        """Execute ping test."""
        host = params.get("host", "")
        count = params.get("count", 4)
        
        if not host:
            raise ValueError("Host is required")
        
        if self.logger:
            self.logger.info(f"Ping: {host} (count={count})")
        
        result = PingExecutor.execute(host, count)
        
        if self.logger:
            if result.success:
                self.logger.info(f"  Sent={result.sent}, Received={result.received}, "
                               f"Loss={result.loss_percent}%, Avg={result.avg_ms}ms")
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
        input_group = QGroupBox("Ping Configuration")
        input_layout = QHBoxLayout()
        
        input_layout.addWidget(QLabel("Host:"))
        host_input = QLineEdit()
        host_input.setPlaceholderText("8.8.8.8 or example.com")
        input_layout.addWidget(host_input, 1)
        
        input_layout.addWidget(QLabel("Count:"))
        count_spin = QSpinBox()
        count_spin.setRange(1, 100)
        count_spin.setValue(4)
        input_layout.addWidget(count_spin)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Ping button
        btn_ping = QPushButton("📡 Ping")
        btn_ping.clicked.connect(lambda: self._on_ping_clicked(
            host_input, count_spin, output_text, stats_label, btn_ping
        ))
        layout.addWidget(btn_ping)
        
        # Output text
        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setFont(QFont("Courier New", 9))
        output_text.setPlaceholderText("Live ping output will appear here...")
        layout.addWidget(output_text, 1)
        
        # Statistics label
        stats_label = QLabel()
        stats_label.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        layout.addWidget(stats_label)
        
        return widget
    
    def _on_ping_clicked(self, host_input, count_spin, output_text, stats_label, btn_ping):
        """Handle GUI ping button click."""
        host = host_input.text().strip()
        if not host:
            QMessageBox.warning(None, "Input Required", "Please enter a host.")
            return
        
        count = count_spin.value()
        
        # Disable button
        btn_ping.setEnabled(False)
        btn_ping.setText("Pinging...")
        
        # Clear output
        output_text.clear()
        stats_label.clear()
        
        # Start ping thread (keep reference to prevent garbage collection)
        self.ping_thread = PingThread(host, count)
        self.ping_thread.ping_output.connect(output_text.append)
        self.ping_thread.ping_complete.connect(lambda result: self._on_ping_complete(
            result, stats_label, btn_ping
        ))
        self.ping_thread.ping_error.connect(lambda error: self._on_ping_error(
            error, stats_label, btn_ping
        ))
        self.ping_thread.finished.connect(self.ping_thread.deleteLater)
        self.ping_thread.start()
    
    def _on_ping_complete(self, result: PingResult, stats_label, btn_ping):
        """Handle ping completion."""
        if result.success:
            stats_text = f"""
<b>📊 Statistics:</b><br>
Packets: Sent={result.sent}, Received={result.received}, Lost={result.lost} ({result.loss_percent:.1f}% loss)<br>
"""
            if result.min_ms is not None:
                stats_text += f"Latency: Min={result.min_ms:.1f}ms, Avg={result.avg_ms:.1f}ms, Max={result.max_ms:.1f}ms"
            
            stats_label.setText(stats_text)
        else:
            stats_label.setText(f"<b>❌ Ping Failed:</b> {result.error}")
        
        # Re-enable button
        btn_ping.setEnabled(True)
        btn_ping.setText("📡 Ping")
    
    def _on_ping_error(self, error: str, stats_label, btn_ping):
        """Handle ping error."""
        stats_label.setText(f"<b>❌ Error:</b> {error}")
        btn_ping.setEnabled(True)
        btn_ping.setText("📡 Ping")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "host",
            help="Host to ping (IP address or hostname)"
        )
        subparser.add_argument(
            "--count", "-c",
            type=int,
            default=4,
            help="Number of packets to send (default: 4)"
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
                "count": args.count
            })
            
            if args.format == "json":
                import json
                from dataclasses import asdict
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"\n📡 Pinging {args.host}...")
                print("=" * 70)
                
                # Show output
                for line in result.output_lines:
                    print(line)
                
                # Show statistics
                if result.success:
                    print(f"\n📊 Statistics:")
                    print(f"  Packets: Sent={result.sent}, Received={result.received}, "
                          f"Lost={result.lost} ({result.loss_percent:.1f}% loss)")
                    
                    if result.min_ms is not None:
                        print(f"  Latency: Min={result.min_ms:.1f}ms, "
                              f"Avg={result.avg_ms:.1f}ms, Max={result.max_ms:.1f}ms")
                else:
                    print(f"\n❌ Ping failed: {result.error}")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"Ping failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return PingTool()
