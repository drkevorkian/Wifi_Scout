"""
HTTP Tool - HTTP/HTTPS checker with timing breakdown and certificate info.

Tests HTTP/HTTPS endpoints with detailed timing measurements including:
DNS lookup, TCP connect, TLS handshake, and data transfer times.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import ssl
import socket
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QLineEdit, QComboBox, QTextEdit, QGroupBox, QMessageBox, QTableWidget,
        QTableWidgetItem
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== DATA MODEL ====================

@dataclass
class HTTPResult:
    """HTTP request result with timing."""
    url: str
    method: str
    status_code: Optional[int] = None
    status_message: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    body_size: int = 0
    dns_time_ms: Optional[float] = None
    connect_time_ms: Optional[float] = None
    tls_time_ms: Optional[float] = None
    total_time_ms: float = 0.0
    ssl_version: Optional[str] = None
    ssl_cipher: Optional[str] = None
    cert_subject: Optional[str] = None
    cert_issuer: Optional[str] = None
    cert_expires: Optional[str] = None
    timestamp: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== HTTP EXECUTOR ====================

class HTTPExecutor:
    """HTTP/HTTPS request execution with timing."""
    
    @staticmethod
    def execute(url: str, method: str = "GET", timeout: int = 30) -> HTTPResult:
        """Execute HTTP request with detailed timing."""
        result = HTTPResult(
            url=url,
            method=method.upper(),
            timestamp=time.time()
        )
        
        try:
            # Parse URL
            parsed = urlparse(url)
            if not parsed.scheme:
                url = "http://" + url
                parsed = urlparse(url)
            
            is_https = parsed.scheme == "https"
            hostname = parsed.hostname
            port = parsed.port or (443 if is_https else 80)
            
            # Timing: DNS lookup
            dns_start = time.time()
            try:
                ip_address = socket.gethostbyname(hostname)
                result.dns_time_ms = (time.time() - dns_start) * 1000
            except socket.gaierror as e:
                result.error = f"DNS lookup failed: {e}"
                result.success = False
                return result
            
            # Timing: TCP connect
            connect_start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            
            try:
                sock.connect((ip_address, port))
                result.connect_time_ms = (time.time() - connect_start) * 1000
            except (socket.timeout, ConnectionRefusedError, OSError) as e:
                result.error = f"Connection failed: {e}"
                result.success = False
                sock.close()
                return result
            
            # Timing: TLS handshake (if HTTPS)
            if is_https:
                tls_start = time.time()
                context = ssl.create_default_context()
                
                try:
                    ssl_sock = context.wrap_socket(sock, server_hostname=hostname)
                    result.tls_time_ms = (time.time() - tls_start) * 1000
                    
                    # Get SSL info
                    result.ssl_version = ssl_sock.version()
                    result.ssl_cipher = ssl_sock.cipher()[0] if ssl_sock.cipher() else None
                    
                    # Get certificate info
                    cert = ssl_sock.getpeercert()
                    if cert:
                        result.cert_subject = dict(x[0] for x in cert.get('subject', []))
                        result.cert_issuer = dict(x[0] for x in cert.get('issuer', []))
                        result.cert_expires = cert.get('notAfter', '')
                    
                    ssl_sock.close()
                except ssl.SSLError as e:
                    result.error = f"TLS handshake failed: {e}"
                    result.success = False
                    return result
            
            sock.close()
            
            # Make full HTTP request
            request_start = time.time()
            
            req = Request(url, method=method.upper())
            req.add_header('User-Agent', 'NetworkSuite/1.0')
            
            try:
                with urlopen(req, timeout=timeout) as response:
                    result.status_code = response.status
                    result.status_message = response.reason
                    result.headers = dict(response.headers)
                    
                    # Read body
                    body = response.read()
                    result.body_size = len(body)
                    
                    result.total_time_ms = (time.time() - request_start) * 1000
                    result.success = True
            
            except HTTPError as e:
                result.status_code = e.code
                result.status_message = e.reason
                result.headers = dict(e.headers) if hasattr(e, 'headers') else {}
                result.total_time_ms = (time.time() - request_start) * 1000
                result.error = f"HTTP {e.code}: {e.reason}"
                result.success = False
            
            except URLError as e:
                result.error = f"Request failed: {e.reason}"
                result.success = False
        
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        return result


# ==================== BACKGROUND HTTP THREAD ====================

if HAS_PYQT6:
    class HTTPThread(QThread):
        """Background HTTP request thread."""
        http_complete = pyqtSignal(object)
        http_error = pyqtSignal(str)
        
        def __init__(self, url: str, method: str):
            super().__init__()
            self.url = url
            self.method = method
        
        def run(self):
            """Run HTTP request in background."""
            try:
                result = HTTPExecutor.execute(self.url, self.method)
                self.http_complete.emit(result)
            except Exception as e:
                self.http_error.emit(str(e))


# ==================== TOOL CLASS ====================

class HTTPTool:
    """
    HTTP/HTTPS testing tool with timing analysis.
    
    Features:
    - GET, POST, HEAD, OPTIONS support
    - Detailed timing breakdown (DNS, connect, TLS, total)
    - SSL/TLS certificate information
    - Response headers display
    - Status code and body size reporting
    - CLI and GUI support
    """
    
    NAME = "HTTP Checker"
    DESCRIPTION = "Test HTTP/HTTPS endpoints with timing and certificate info"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
        self.http_thread = None  # Keep reference to prevent garbage collection
    
    def run(self, params: Dict[str, Any]) -> HTTPResult:
        """Execute HTTP request."""
        url = params.get("url", "")
        method = params.get("method", "GET")
        
        if not url:
            raise ValueError("URL is required")
        
        if self.logger:
            self.logger.info(f"HTTP {method}: {url}")
        
        result = HTTPExecutor.execute(url, method)
        
        if self.logger:
            if result.success:
                self.logger.info(f"  Status={result.status_code}, "
                               f"Size={result.body_size}B, Time={result.total_time_ms:.0f}ms")
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
        input_group = QGroupBox("Request")
        input_layout = QVBoxLayout()
        
        url_layout = QHBoxLayout()
        method_combo = QComboBox()
        method_combo.addItems(["GET", "POST", "HEAD", "OPTIONS"])
        url_layout.addWidget(method_combo)
        
        url_input = QLineEdit()
        url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(url_input, 1)
        
        input_layout.addLayout(url_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Request button
        btn_request = QPushButton("🌐 Send Request")
        btn_request.clicked.connect(lambda: self._on_request_clicked(
            url_input, method_combo, timing_table, headers_text, status_label, btn_request
        ))
        layout.addWidget(btn_request)
        
        # Status label
        status_label = QLabel()
        status_label.setStyleSheet("padding: 5px; font-weight: bold;")
        layout.addWidget(status_label)
        
        # Timing table
        timing_group = QGroupBox("Timing Breakdown")
        timing_layout = QVBoxLayout()
        
        timing_table = QTableWidget(0, 2)
        timing_table.setHorizontalHeaderLabels(["Metric", "Value"])
        timing_table.horizontalHeader().setStretchLastSection(True)
        timing_table.setMaximumHeight(200)
        timing_layout.addWidget(timing_table)
        
        timing_group.setLayout(timing_layout)
        layout.addWidget(timing_group)
        
        # Headers display
        headers_group = QGroupBox("Response Headers & Certificate")
        headers_layout = QVBoxLayout()
        
        headers_text = QTextEdit()
        headers_text.setReadOnly(True)
        headers_text.setFont(QFont("Courier New", 9))
        headers_text.setMaximumHeight(200)
        headers_layout.addWidget(headers_text)
        
        headers_group.setLayout(headers_layout)
        layout.addWidget(headers_group)
        
        layout.addStretch()
        return widget
    
    def _on_request_clicked(self, url_input, method_combo, timing_table, headers_text, status_label, btn_request):
        """Handle GUI request button click."""
        url = url_input.text().strip()
        if not url:
            QMessageBox.warning(None, "Input Required", "Please enter a URL.")
            return
        
        method = method_combo.currentText()
        
        # Disable button
        btn_request.setEnabled(False)
        btn_request.setText("Requesting...")
        
        # Clear displays
        timing_table.setRowCount(0)
        headers_text.clear()
        status_label.setText("⏳ Sending request...")
        
        # Start HTTP thread (keep reference to prevent garbage collection)
        self.http_thread = HTTPThread(url, method)
        self.http_thread.http_complete.connect(lambda result: self._on_request_complete(
            result, timing_table, headers_text, status_label, btn_request
        ))
        self.http_thread.http_error.connect(lambda error: self._on_request_error(
            error, status_label, btn_request
        ))
        self.http_thread.finished.connect(self.http_thread.deleteLater)
        self.http_thread.start()
    
    def _on_request_complete(self, result: HTTPResult, timing_table, headers_text, status_label, btn_request):
        """Handle HTTP request completion."""
        if result.success or result.status_code:
            # Status
            if result.success:
                status_label.setText(f"✅ {result.status_code} {result.status_message} - {result.body_size} bytes")
            else:
                status_label.setText(f"⚠️ {result.error}")
            
            # Timing table
            timing_data = [
                ("DNS Lookup", f"{result.dns_time_ms:.1f} ms" if result.dns_time_ms else "—"),
                ("TCP Connect", f"{result.connect_time_ms:.1f} ms" if result.connect_time_ms else "—"),
                ("TLS Handshake", f"{result.tls_time_ms:.1f} ms" if result.tls_time_ms else "N/A (HTTP)"),
                ("Total Time", f"{result.total_time_ms:.1f} ms"),
                ("Body Size", f"{result.body_size} bytes"),
            ]
            
            for label, value in timing_data:
                row = timing_table.rowCount()
                timing_table.insertRow(row)
                timing_table.setItem(row, 0, QTableWidgetItem(label))
                timing_table.setItem(row, 1, QTableWidgetItem(value))
            
            # Headers and certificate
            output = []
            
            if result.headers:
                output.append("=== Response Headers ===")
                for key, value in result.headers.items():
                    output.append(f"{key}: {value}")
            
            if result.ssl_version:
                output.append("\n=== SSL/TLS Info ===")
                output.append(f"Version: {result.ssl_version}")
                output.append(f"Cipher: {result.ssl_cipher}")
                
                if result.cert_subject:
                    output.append(f"\n=== Certificate ===")
                    output.append(f"Subject: {result.cert_subject.get('commonName', 'N/A')}")
                    output.append(f"Issuer: {result.cert_issuer.get('commonName', 'N/A') if result.cert_issuer else 'N/A'}")
                    output.append(f"Expires: {result.cert_expires}")
            
            headers_text.setPlainText("\n".join(output))
        else:
            status_label.setText(f"❌ {result.error}")
        
        # Re-enable button
        btn_request.setEnabled(True)
        btn_request.setText("🌐 Send Request")
    
    def _on_request_error(self, error: str, status_label, btn_request):
        """Handle HTTP request error."""
        status_label.setText(f"❌ Error: {error}")
        btn_request.setEnabled(True)
        btn_request.setText("🌐 Send Request")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "url",
            help="URL to test (e.g., https://example.com)"
        )
        subparser.add_argument(
            "--method", "-m",
            choices=["GET", "POST", "HEAD", "OPTIONS"],
            default="GET",
            help="HTTP method (default: GET)"
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
                "url": args.url,
                "method": args.method
            })
            
            if args.format == "json":
                import json
                from dataclasses import asdict
                print(json.dumps(asdict(result), indent=2))
            else:
                print(f"\n🌐 {args.method} {args.url}")
                print("=" * 80)
                
                if result.success or result.status_code:
                    print(f"\nStatus: {result.status_code} {result.status_message}")
                    print(f"Body Size: {result.body_size} bytes")
                    
                    print(f"\n⏱️  Timing:")
                    if result.dns_time_ms:
                        print(f"  DNS Lookup:    {result.dns_time_ms:>8.1f} ms")
                    if result.connect_time_ms:
                        print(f"  TCP Connect:   {result.connect_time_ms:>8.1f} ms")
                    if result.tls_time_ms:
                        print(f"  TLS Handshake: {result.tls_time_ms:>8.1f} ms")
                    print(f"  Total:         {result.total_time_ms:>8.1f} ms")
                    
                    if result.ssl_version:
                        print(f"\n🔒 SSL/TLS:")
                        print(f"  Version: {result.ssl_version}")
                        print(f"  Cipher:  {result.ssl_cipher}")
                        
                        if result.cert_subject:
                            print(f"\n📜 Certificate:")
                            print(f"  Subject: {result.cert_subject.get('commonName', 'N/A')}")
                            if result.cert_issuer:
                                print(f"  Issuer:  {result.cert_issuer.get('commonName', 'N/A')}")
                            print(f"  Expires: {result.cert_expires}")
                    
                    if not result.success:
                        print(f"\n⚠️  {result.error}")
                else:
                    print(f"\n❌ Request failed: {result.error}")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"HTTP request failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return HTTPTool()
