"""
DNS Tool - DNS lookup and diagnostics mod.

Supports A, AAAA, CNAME, MX, TXT, NS record queries.
Uses dnspython library with fallback to system nslookup/dig commands.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging
import platform
import subprocess
import time

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
        QLineEdit, QTableWidget, QTableWidgetItem, QCheckBox, QGroupBox,
        QMessageBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False

# Try to import dnspython
try:
    import dns.resolver
    import dns.exception
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


# ==================== DATA MODEL ====================

@dataclass
class DNSResult:
    """DNS lookup result."""
    hostname: str
    record_type: str
    records: List[str] = field(default_factory=list)
    timestamp: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


# ==================== DNS RESOLVER ====================

class DNSResolver:
    """DNS resolution with dnspython and fallback."""
    
    @staticmethod
    def query_with_dnspython(hostname: str, record_type: str) -> DNSResult:
        """Query using dnspython library."""
        start = time.time()
        result = DNSResult(
            hostname=hostname,
            record_type=record_type,
            timestamp=time.time()
        )
        
        try:
            answers = dns.resolver.resolve(hostname, record_type)
            result.records = [str(rdata) for rdata in answers]
            result.latency_ms = (time.time() - start) * 1000
            result.success = True
        except dns.exception.DNSException as e:
            result.error = str(e)
            result.success = False
        
        return result
    
    @staticmethod
    def query_with_system_command(hostname: str, record_type: str) -> DNSResult:
        """Query using system nslookup or dig command."""
        start = time.time()
        result = DNSResult(
            hostname=hostname,
            record_type=record_type,
            timestamp=time.time()
        )
        
        system = platform.system()
        
        try:
            if system == "Windows":
                # Use nslookup
                cmd = ["nslookup", "-type=" + record_type.lower(), hostname]
            else:
                # Use dig
                cmd = ["dig", "+short", hostname, record_type.upper()]
            
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            
            if proc.returncode == 0:
                output = proc.stdout.strip()
                if output:
                    # Parse output
                    lines = [line.strip() for line in output.splitlines() if line.strip()]
                    
                    if system == "Windows":
                        # Parse nslookup output
                        records = []
                        for line in lines:
                            if "Address:" in line or "mail exchanger" in line or "nameserver" in line:
                                parts = line.split(":", 1) if ":" in line else line.split("=", 1)
                                if len(parts) > 1:
                                    records.append(parts[1].strip())
                        result.records = records if records else lines
                    else:
                        # dig output is already clean
                        result.records = lines
                    
                    result.success = True
                else:
                    result.error = "No records found"
                    result.success = False
            else:
                result.error = proc.stderr.strip() or "Query failed"
                result.success = False
            
            result.latency_ms = (time.time() - start) * 1000
        
        except subprocess.TimeoutExpired:
            result.error = "Query timeout"
            result.success = False
        except FileNotFoundError:
            result.error = "DNS command not found (install dnsutils or bind-tools)"
            result.success = False
        except Exception as e:
            result.error = str(e)
            result.success = False
        
        return result
    
    @classmethod
    def query(cls, hostname: str, record_type: str) -> DNSResult:
        """Query DNS with automatic fallback."""
        if HAS_DNSPYTHON:
            return cls.query_with_dnspython(hostname, record_type)
        else:
            return cls.query_with_system_command(hostname, record_type)


# ==================== BACKGROUND QUERY THREAD ====================

if HAS_PYQT6:
    class DNSQueryThread(QThread):
        """Background DNS query thread."""
        query_complete = pyqtSignal(object)
        query_error = pyqtSignal(str)
        
        def __init__(self, hostname: str, record_types: List[str]):
            super().__init__()
            self.hostname = hostname
            self.record_types = record_types
        
        def run(self):
            """Run queries in background."""
            try:
                results = []
                for record_type in self.record_types:
                    result = DNSResolver.query(self.hostname, record_type)
                    results.append(result)
                
                self.query_complete.emit(results)
            except Exception as e:
                self.query_error.emit(str(e))


# ==================== TOOL CLASS ====================

class DNSTool:
    """
    DNS lookup and diagnostics tool.
    
    Features:
    - Query multiple record types (A, AAAA, CNAME, MX, TXT, NS)
    - Uses dnspython with system command fallback
    - Latency measurement
    - GUI and CLI support
    """
    
    NAME = "DNS Lookup"
    DESCRIPTION = "Query DNS records (A, AAAA, CNAME, MX, TXT, NS)"
    CATEGORY = "network"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
        self.query_thread = None  # Keep reference to prevent garbage collection
    
    def run(self, params: Dict[str, Any]) -> List[DNSResult]:
        """Execute DNS queries."""
        hostname = params.get("hostname", "")
        record_types = params.get("record_types", ["A"])
        
        if not hostname:
            raise ValueError("Hostname is required")
        
        if self.logger:
            self.logger.info(f"DNS query: {hostname} ({', '.join(record_types)})")
        
        results = []
        for record_type in record_types:
            result = DNSResolver.query(hostname, record_type)
            results.append(result)
            
            if self.logger:
                if result.success:
                    self.logger.debug(f"  {record_type}: {len(result.records)} records, {result.latency_ms:.1f}ms")
                else:
                    self.logger.debug(f"  {record_type}: FAILED - {result.error}")
        
        return results
    
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
        input_group = QGroupBox("Query")
        input_layout = QVBoxLayout()
        
        hostname_layout = QHBoxLayout()
        hostname_layout.addWidget(QLabel("Hostname:"))
        hostname_input = QLineEdit()
        hostname_input.setPlaceholderText("example.com")
        hostname_layout.addWidget(hostname_input, 1)
        input_layout.addLayout(hostname_layout)
        
        # Record type checkboxes
        types_layout = QHBoxLayout()
        types_layout.addWidget(QLabel("Record Types:"))
        
        checkboxes = {}
        for rtype in ["A", "AAAA", "CNAME", "MX", "TXT", "NS"]:
            cb = QCheckBox(rtype)
            cb.setChecked(rtype == "A")
            checkboxes[rtype] = cb
            types_layout.addWidget(cb)
        
        types_layout.addStretch()
        input_layout.addLayout(types_layout)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Query button
        btn_query = QPushButton("🔍 Query DNS")
        btn_query.clicked.connect(lambda: self._on_query_clicked(
            hostname_input, checkboxes, results_table, btn_query
        ))
        layout.addWidget(btn_query)
        
        # Results table
        results_table = QTableWidget(0, 4)
        results_table.setHorizontalHeaderLabels(["Type", "Records", "Latency", "Status"])
        results_table.horizontalHeader().setStretchLastSection(False)
        results_table.setColumnWidth(0, 80)
        results_table.setColumnWidth(1, 400)
        results_table.setColumnWidth(2, 100)
        results_table.setColumnWidth(3, 100)
        layout.addWidget(results_table, 1)
        
        # Store references
        widget._hostname_input = hostname_input
        widget._checkboxes = checkboxes
        widget._results_table = results_table
        widget._btn_query = btn_query
        
        return widget
    
    def _on_query_clicked(self, hostname_input, checkboxes, results_table, btn_query):
        """Handle GUI query button click."""
        hostname = hostname_input.text().strip()
        if not hostname:
            QMessageBox.warning(None, "Input Required", "Please enter a hostname.")
            return
        
        # Get selected record types
        record_types = [rtype for rtype, cb in checkboxes.items() if cb.isChecked()]
        if not record_types:
            QMessageBox.warning(None, "Input Required", "Please select at least one record type.")
            return
        
        # Disable button
        btn_query.setEnabled(False)
        btn_query.setText("Querying...")
        
        # Clear table
        results_table.setRowCount(0)
        
        # Start query thread (keep reference to prevent garbage collection)
        self.query_thread = DNSQueryThread(hostname, record_types)
        self.query_thread.query_complete.connect(lambda results: self._on_query_complete(
            results, results_table, btn_query
        ))
        self.query_thread.query_error.connect(lambda error: self._on_query_error(
            error, btn_query
        ))
        self.query_thread.finished.connect(self.query_thread.deleteLater)
        self.query_thread.start()
    
    def _on_query_complete(self, results: List[DNSResult], results_table, btn_query):
        """Handle query completion."""
        for result in results:
            row = results_table.rowCount()
            results_table.insertRow(row)
            
            # Type
            results_table.setItem(row, 0, QTableWidgetItem(result.record_type))
            
            # Records
            if result.success and result.records:
                records_text = "\n".join(result.records[:5])  # Show first 5
                if len(result.records) > 5:
                    records_text += f"\n... ({len(result.records) - 5} more)"
            else:
                records_text = result.error or "No records"
            
            results_table.setItem(row, 1, QTableWidgetItem(records_text))
            
            # Latency
            latency_text = f"{result.latency_ms:.1f} ms" if result.success else "—"
            results_table.setItem(row, 2, QTableWidgetItem(latency_text))
            
            # Status
            status_text = "✓ Success" if result.success else "✗ Failed"
            results_table.setItem(row, 3, QTableWidgetItem(status_text))
        
        # Re-enable button
        btn_query.setEnabled(True)
        btn_query.setText("🔍 Query DNS")
    
    def _on_query_error(self, error: str, btn_query):
        """Handle query error."""
        QMessageBox.critical(None, "Query Failed", f"DNS query failed:\n{error}")
        btn_query.setEnabled(True)
        btn_query.setText("🔍 Query DNS")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "hostname",
            help="Hostname to query (e.g., example.com)"
        )
        subparser.add_argument(
            "--types", "-t",
            nargs="+",
            default=["A"],
            choices=["A", "AAAA", "CNAME", "MX", "TXT", "NS"],
            help="DNS record types to query (default: A)"
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
            results = self.run({
                "hostname": args.hostname,
                "record_types": args.types
            })
            
            if args.format == "json":
                import json
                from dataclasses import asdict
                output = [asdict(r) for r in results]
                print(json.dumps(output, indent=2))
            else:
                print(f"\n🔍 DNS Lookup: {args.hostname}")
                print("=" * 70)
                
                for result in results:
                    print(f"\n{result.record_type} Records:")
                    if result.success and result.records:
                        for record in result.records:
                            print(f"  • {record}")
                        print(f"  Latency: {result.latency_ms:.1f} ms")
                    else:
                        print(f"  ✗ {result.error}")
                
                # Summary
                total = len(results)
                successful = sum(1 for r in results if r.success)
                print(f"\n{successful}/{total} queries successful")
            
            return 0
        
        except Exception as e:
            logger.error(f"DNS query failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """Called by core to register this mod."""
    return DNSTool()
