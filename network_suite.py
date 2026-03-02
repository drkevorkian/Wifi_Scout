#!/usr/bin/env python3
"""
network_suite.py - Modular Network Diagnostic Suite
Core system with WiFi functionality and plugin architecture.

Mods are loaded from ./mods/ directory and appear as tabs.
Each mod is self-contained with GUI, CLI, and testing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import platform
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ==================== FEATURE DETECTION ====================

HAS_PYQT6 = False
HAS_MATPLOTLIB = False

try:
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QSettings
    from PyQt6.QtGui import QAction, QColor, QBrush, QFont
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QLabel,
        QFileDialog, QMessageBox, QCheckBox, QLineEdit, QComboBox,
        QSpinBox, QGroupBox, QProgressBar, QTabWidget, QGridLayout,
        QScrollArea, QFrame, QInputDialog
    )
    HAS_PYQT6 = True
except ImportError:
    pass

try:
    import matplotlib
    matplotlib.use("QtAgg")
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    pass

APP_NAME = "Network Scout"
APP_VERSION = "2.2.9"

# ==================== DATA MODELS ====================

@dataclass
class WifiNetwork:
    """WiFi network information."""
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
    """Signal history for a WiFi network."""
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


# ==================== TOOL REGISTRY ====================

TOOL_REGISTRY: Dict[str, Any] = {}


def register_tool(tool_instance: Any) -> None:
    """Register a mod tool instance."""
    TOOL_REGISTRY[tool_instance.NAME] = tool_instance


# ==================== PLUGIN LOADER ====================

def load_mods(logger: logging.Logger) -> None:
    """Discover and load all mods from ./mods/ directory."""
    mods_dir = Path(__file__).parent / "mods"
    
    if not mods_dir.exists():
        logger.warning("Mods directory not found: %s", mods_dir)
        return
    
    # Load all *_tool.py or *_mod.py files
    for mod_file in mods_dir.glob("*_tool.py"):
        try:
            mod_name = mod_file.stem
            spec = importlib.util.spec_from_file_location(mod_name, mod_file)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Call register() function if it exists
                if hasattr(module, 'register'):
                    tool = module.register()
                    tool.logger = logger
                    register_tool(tool)
                    logger.info("Loaded mod: %s", tool.NAME)
        except Exception as e:
            logger.error("Failed to load mod %s: %s", mod_file.name, e)
    
    logger.info("Loaded %d mods", len(TOOL_REGISTRY))


# ==================== LOGGING ====================

def make_logger(log_path: str) -> logging.Logger:
    """Create logger that writes to file and stdout."""
    logger = logging.getLogger("network_suite")
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


if HAS_PYQT6:
    class QtLogHandler(logging.Handler):
        """Log handler that outputs to QTextEdit widget."""
        def __init__(self, widget: QTextEdit):
            super().__init__()
            self.widget = widget
            self.setLevel(logging.DEBUG)
            self.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

        def emit(self, record: logging.LogRecord) -> None:
            self.widget.append(self.format(record))


# ==================== INCREMENTAL TABLE MANAGER ====================

if HAS_PYQT6:
    class IncrementalTableManager:
        """Manages QTableWidget with keyed row tracking for incremental updates."""
        
        def __init__(self, table: QTableWidget, key_column: int = 1):
            self.table = table
            self.key_column = key_column
            self.row_map: Dict[str, int] = {}  # key -> row_index
            self.network_cache: Dict[str, WifiNetwork] = {}  # key -> network
        
        def update_networks(self, networks: List[WifiNetwork], 
                           value_formatter, color_applier) -> None:
            """Incrementally update table with new network list."""
            # Disable sorting during update
            was_sorting = self.table.isSortingEnabled()
            self.table.setSortingEnabled(False)
            
            current_keys = {n.bssid: n for n in networks}
            
            # Remove networks that disappeared
            for key in list(self.row_map.keys()):
                if key not in current_keys:
                    row = self.row_map[key]
                    self.table.removeRow(row)
                    del self.row_map[key]
                    del self.network_cache[key]
                    # Update row indices for rows below deleted row
                    for k, v in list(self.row_map.items()):
                        if v > row:
                            self.row_map[k] = v - 1
            
            # Add new or update existing networks
            for network in networks:
                key = network.bssid
                if key in self.row_map:
                    # Update existing row only if changed
                    if self._network_changed(network, self.network_cache.get(key)):
                        self._update_row(self.row_map[key], network, value_formatter, color_applier)
                        self.network_cache[key] = network
                else:
                    # Add new row
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    self._populate_row(row, network, value_formatter, color_applier)
                    self.row_map[key] = row
                    self.network_cache[key] = network
            
            # Re-enable sorting
            self.table.setSortingEnabled(was_sorting)
        
        def _network_changed(self, new: WifiNetwork, old: Optional[WifiNetwork]) -> bool:
            """Check if network data has changed."""
            if old is None:
                return True
            # Compare key fields that would affect display
            return (new.signal_dbm != old.signal_dbm or
                    new.security != old.security or
                    new.score != old.score or
                    new.is_connected != old.is_connected)
        
        def _update_row(self, row: int, network: WifiNetwork, 
                       value_formatter, color_applier) -> None:
            """Update existing row with new values."""
            values = value_formatter(network)
            for col, value in enumerate(values):
                item = self.table.item(row, col)
                if item and item.text() != value:
                    item.setText(value)
                    color_applier(item, col, network)
        
        def _populate_row(self, row: int, network: WifiNetwork,
                         value_formatter, color_applier) -> None:
            """Populate new row with all data."""
            values = value_formatter(network)
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                color_applier(item, col, network)
                self.table.setItem(row, col, item)
        
        def clear(self) -> None:
            """Clear all tracking."""
            self.row_map.clear()
            self.network_cache.clear()
            self.table.setRowCount(0)


# ==================== GUI COMPONENTS ====================

if HAS_PYQT6:
    class MetricCard(QFrame):
        """Display card for a single metric value."""
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


if HAS_PYQT6 and HAS_MATPLOTLIB:
    class SignalChart(FigureCanvasQTAgg):
        """Matplotlib chart for WiFi signal history."""
        def __init__(self, parent=None, width=8, height=4, dpi=100):
            fig = Figure(figsize=(width, height), dpi=dpi)
            self.axes = fig.add_subplot(111)
            super().__init__(fig)
            self.setParent(parent)

        def plot_history(self, histories: Dict[str, NetworkHistory], 
                        selected_bssids: Optional[List[str]] = None):
            self.axes.clear()

            if not histories:
                self.axes.text(0.5, 0.5, "No historical data available", 
                             ha="center", va="center", transform=self.axes.transAxes)
                self.draw()
                return

            if selected_bssids is None:
                selected_bssids = list(histories.keys())[:5]

            plotted_any = False
            for bssid in selected_bssids:
                hist = histories.get(bssid)
                if not hist or not hist.timestamps:
                    continue
                start_time = min(hist.timestamps)
                times = [(t - start_time) for t in hist.timestamps]
                label = f"{hist.ssid} ({bssid[-8:]})"
                self.axes.plot(times, hist.signals, marker="o", linestyle="-", 
                             label=label, linewidth=2, markersize=4)
                plotted_any = True

            self.axes.set_xlabel("Time (seconds)")
            self.axes.set_ylabel("Signal Strength (dBm)")
            self.axes.set_title("Wi-Fi Signal History", fontweight="bold")
            self.axes.grid(True, alpha=0.3)
            
            if plotted_any:
                self.axes.legend(loc="best", fontsize=8)
            
            self.axes.set_ylim(-100, -20)
            self.figure.tight_layout()
            self.draw()


# ==================== IMPORT WIFI ENGINE ====================

# Import WiFi-specific functionality from separate module
sys.path.insert(0, str(Path(__file__).parent / "core"))

try:
    from wifi_engine import (
        scan_wifi, get_connected_bssid, mark_connected_and_enrich,
        score_network, pick_best, connect_to_network,
        ScanThread, COLUMNS
    )
except ImportError:
    # Fallback: will create wifi_engine.py in next step
    print("Warning: wifi_engine.py not found. Will be created.")
    COLUMNS = []
    
    if HAS_PYQT6:
        class ScanThread(QThread):
            scan_complete = pyqtSignal(list)
            scan_error = pyqtSignal(str)
            
            def __init__(self, logger):
                super().__init__()
                self.logger = logger
            
            def run(self):
                self.scan_error.emit("WiFi engine not loaded")


# ==================== MAIN WINDOW ====================

if HAS_PYQT6:
    class MainWindow(QMainWindow):
        """Main application window."""
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
            
            # Setup logging
            base = Path.home() / ".network_suite"
            base.mkdir(exist_ok=True)
            self.log_path = base / f"network_suite_{time.strftime('%Y%m%d_%H%M%S')}.log"
            self.logger = make_logger(str(self.log_path))
            
            # Load mods
            load_mods(self.logger)
            
            # State
            self.networks: List[WifiNetwork] = []
            self.network_history: Dict[str, NetworkHistory] = {}
            self.dark_mode = False
            self.scan_thread: Optional[ScanThread] = None
            self.connected_bssid: Optional[str] = None
            self.last_connection_attempt: float = 0.0
            self.connection_rate_limit_seconds: float = 5.0
            
            # Timers
            self.scan_timer = QTimer()
            self.scan_timer.timeout.connect(self.do_scan)
            
            # Build UI
            self.init_ui()
            self.restore_settings()
            self.apply_theme()
            
            self.logger.info("%s started. Log: %s", APP_NAME, self.log_path)
        
        def init_ui(self) -> None:
            """Initialize user interface."""
            root = QWidget()
            self.setCentralWidget(root)
            main_layout = QVBoxLayout(root)
            
            self.tabs = QTabWidget()
            main_layout.addWidget(self.tabs)
            
            # WiFi Scanner Tab
            self.scanner_tab = QWidget()
            self.init_scanner_tab()
            self.tabs.addTab(self.scanner_tab, "📡 WiFi")
            
            # Details Tab
            self.details_tab = QWidget()
            self.init_details_tab()
            self.tabs.addTab(self.details_tab, "📋 Details")
            
            # Signal History Tab
            if HAS_MATPLOTLIB:
                self.chart_tab = QWidget()
                self.init_chart_tab()
                self.tabs.addTab(self.chart_tab, "📈 History")
            
            # Mods Tab (container for all loaded mods)
            self.mods_tab = QTabWidget()
            self.init_mods_tabs()
            self.tabs.addTab(self.mods_tab, "🔧 Mods")
            
            # Logs Tab
            self.log_tab = QWidget()
            self.init_log_tab()
            self.tabs.addTab(self.log_tab, "📝 Logs")
            
            self.statusBar().showMessage("Ready")
            self.init_menu_bar()
        
        def init_mods_tabs(self) -> None:
            """Create tabs for each loaded mod."""
            if not TOOL_REGISTRY:
                empty_label = QLabel("No mods loaded.\n\nPlace *_tool.py files in ./mods/ directory.")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.mods_tab.addTab(empty_label, "Welcome")
                return
            
            for tool_name, tool in TOOL_REGISTRY.items():
                try:
                    if hasattr(tool, 'get_gui_panel'):
                        panel = tool.get_gui_panel(self)
                        self.mods_tab.addTab(panel, tool_name)
                except Exception as e:
                    self.logger.error("Failed to create panel for %s: %s", tool_name, e)
        
        def init_menu_bar(self) -> None:
            """Initialize menu bar."""
            menubar = self.menuBar()
            
            # File menu
            file_menu = menubar.addMenu("File")
            export_action = QAction("Export Results…", self)
            export_action.setShortcut("Ctrl+E")
            export_action.triggered.connect(self.do_export)
            file_menu.addAction(export_action)
            
            file_menu.addSeparator()
            exit_action = QAction("Exit", self)
            exit_action.setShortcut("Ctrl+Q")
            exit_action.triggered.connect(self.close)
            file_menu.addAction(exit_action)
            
            # View menu
            view_menu = menubar.addMenu("View")
            theme_action = QAction("Toggle Dark/Light Theme", self)
            theme_action.setShortcut("Ctrl+T")
            theme_action.triggered.connect(self.toggle_theme)
            view_menu.addAction(theme_action)
            
            refresh_action = QAction("Refresh Scan", self)
            refresh_action.setShortcut("F5")
            refresh_action.triggered.connect(self.do_scan)
            view_menu.addAction(refresh_action)
            
            # Tools menu
            tools_menu = menubar.addMenu("Tools")
            best_action = QAction("Find Best Network", self)
            best_action.setShortcut("Ctrl+B")
            best_action.triggered.connect(self.do_best)
            tools_menu.addAction(best_action)
            
            # Help menu
            help_menu = menubar.addMenu("Help")
            about_action = QAction("About", self)
            about_action.triggered.connect(self.show_about)
            help_menu.addAction(about_action)
        
        def init_scanner_tab(self) -> None:
            """Initialize WiFi scanner tab."""
            layout = QVBoxLayout(self.scanner_tab)
            
            # Controls panel
            control_panel = QGroupBox("Controls")
            control_layout = QGridLayout()
            
            self.btn_scan = QPushButton("🔍 Scan Now")
            self.btn_scan.clicked.connect(self.do_scan)
            control_layout.addWidget(self.btn_scan, 0, 0)
            
            self.btn_best = QPushButton("⭐ Find Best")
            self.btn_best.clicked.connect(self.do_best)
            control_layout.addWidget(self.btn_best, 0, 1)
            
            self.btn_connect = QPushButton("🔗 Connect")
            self.btn_connect.clicked.connect(self.connect_to_selected)
            control_layout.addWidget(self.btn_connect, 0, 2)
            
            self.btn_export = QPushButton("💾 Export")
            self.btn_export.clicked.connect(self.do_export)
            control_layout.addWidget(self.btn_export, 0, 3)
            
            self.chk_auto_scan = QCheckBox("Auto-refresh every")
            self.chk_auto_scan.toggled.connect(self.toggle_auto_scan)
            control_layout.addWidget(self.chk_auto_scan, 1, 0)
            
            self.spin_interval = QSpinBox()
            self.spin_interval.setRange(5, 300)
            self.spin_interval.setValue(10)
            self.spin_interval.setSuffix(" sec")
            control_layout.addWidget(self.spin_interval, 1, 1)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setMaximum(0)
            control_layout.addWidget(self.progress_bar, 1, 2, 1, 2)
            
            control_panel.setLayout(control_layout)
            layout.addWidget(control_panel)
            
            # Statistics panel
            stats_panel = QGroupBox("Statistics")
            stats_layout = QHBoxLayout()
            
            self.lbl_total = QLabel("Networks: 0")
            stats_layout.addWidget(self.lbl_total)
            
            self.lbl_connected = QLabel("Connected: None")
            stats_layout.addWidget(self.lbl_connected)
            
            stats_layout.addStretch()
            stats_panel.setLayout(stats_layout)
            layout.addWidget(stats_panel)
            
            # Selected network dashboard
            dash = QGroupBox("Selected Network")
            dash_layout = QHBoxLayout()
            
            self.card_ssid = MetricCard("SSID")
            self.card_signal = MetricCard("Signal", "-50 great • -75 weak")
            self.card_security = MetricCard("Security")
            self.card_score = MetricCard("Score")
            
            for card in (self.card_ssid, self.card_signal, self.card_security, self.card_score):
                dash_layout.addWidget(card, 1)
            
            dash.setLayout(dash_layout)
            layout.addWidget(dash)
            
            # WiFi networks table
            self.table = QTableWidget(0, len(COLUMNS) if COLUMNS else 7)
            self.table.setSortingEnabled(True)
            self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            self.table.verticalHeader().setVisible(False)
            self.table.setAlternatingRowColors(True)
            self.table.itemSelectionChanged.connect(self.on_selection_changed)
            
            if COLUMNS:
                for i, (name, tip) in enumerate(COLUMNS):
                    self.table.setHorizontalHeaderItem(i, QTableWidgetItem(name))
                    self.table.horizontalHeaderItem(i).setToolTip(tip)
            
            # Initialize incremental table manager
            self.table_manager = IncrementalTableManager(self.table, key_column=1)
            
            layout.addWidget(self.table, 1)
        
        def init_details_tab(self) -> None:
            """Initialize details tab."""
            layout = QVBoxLayout(self.details_tab)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            w = QWidget()
            wl = QVBoxLayout(w)
            
            details_group = QGroupBox("Selected Network Details")
            details_layout = QGridLayout()
            
            self.detail_labels: Dict[str, QLabel] = {}
            fields = [
                ("ssid", "SSID:"), ("bssid", "BSSID:"), ("signal_dbm", "Signal (dBm):"),
                ("security", "Security:"), ("channel", "Channel:"), ("band", "Band:"),
                ("score", "Score:")
            ]
            
            for r, (key, label_text) in enumerate(fields):
                lab = QLabel(label_text)
                lab.setStyleSheet("font-weight: bold;")
                val = QLabel("—")
                val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                details_layout.addWidget(lab, r, 0, Qt.AlignmentFlag.AlignRight)
                details_layout.addWidget(val, r, 1)
                self.detail_labels[key] = val
            
            details_group.setLayout(details_layout)
            wl.addWidget(details_group)
            wl.addStretch()
            
            scroll.setWidget(w)
            layout.addWidget(scroll)
        
        def init_chart_tab(self) -> None:
            """Initialize signal history chart tab."""
            layout = QVBoxLayout(self.chart_tab)
            
            controls = QHBoxLayout()
            controls.addWidget(QLabel("Show networks:"))
            
            self.chart_selector = QComboBox()
            self.chart_selector.addItem("All (top 5)")
            self.chart_selector.currentTextChanged.connect(self.update_chart)
            controls.addWidget(self.chart_selector, 1)
            
            layout.addLayout(controls)
            
            self.chart = SignalChart(self.chart_tab, width=10, height=6)
            layout.addWidget(self.chart, 1)
        
        def init_log_tab(self) -> None:
            """Initialize logs tab."""
            layout = QVBoxLayout(self.log_tab)
            
            controls = QHBoxLayout()
            btn_clear = QPushButton("Clear Log")
            btn_clear.clicked.connect(lambda: self.log_view.clear())
            controls.addWidget(btn_clear)
            
            btn_copy = QPushButton("Copy Log Path")
            btn_copy.clicked.connect(self.copy_log_path)
            controls.addWidget(btn_copy)
            
            controls.addStretch()
            layout.addLayout(controls)
            
            self.log_view = QTextEdit()
            self.log_view.setReadOnly(True)
            self.log_view.setFont(QFont("Courier New", 9))
            layout.addWidget(self.log_view, 1)
            
            self.logger.addHandler(QtLogHandler(self.log_view))
        
        # ==================== WiFi Actions ====================
        
        def do_scan(self) -> None:
            """Start WiFi scan."""
            if self.scan_thread and self.scan_thread.isRunning():
                return
            
            self.statusBar().showMessage("Scanning…")
            self.logger.info("==== SCAN START ====")
            self.set_busy(True)
            
            self.scan_thread = ScanThread(self.logger)
            self.scan_thread.scan_complete.connect(self.on_scan_complete)
            self.scan_thread.scan_error.connect(self.on_scan_error)
            self.scan_thread.start()
        
        def on_scan_complete(self, networks: list) -> None:
            """Handle scan completion."""
            try:
                self.networks = list(networks)
                self.connected_bssid = mark_connected_and_enrich(self.logger, self.networks)
                
                # Score networks
                for n in self.networks:
                    n.score = score_network(self.networks, n)
                    
                    # Update history
                    if n.signal_dbm is not None:
                        if n.bssid not in self.network_history:
                            self.network_history[n.bssid] = NetworkHistory(
                                bssid=n.bssid, ssid=n.ssid, timestamps=[], signals=[]
                            )
                        self.network_history[n.bssid].add_reading(
                            n.timestamp or time.time(), n.signal_dbm
                        )
                
                # Incremental table update
                self.table_manager.update_networks(
                    self.networks,
                    self.format_network_row,
                    self.apply_row_colors
                )
                
                self.update_statistics()
                self.statusBar().showMessage(f"Found {len(self.networks)} networks", 5000)
                self.logger.info("Scan complete. Networks=%d", len(self.networks))
            finally:
                self.set_busy(False)
        
        def on_scan_error(self, msg: str) -> None:
            """Handle scan error."""
            self.set_busy(False)
            self.logger.error("Scan failed: %s", msg)
            
            # Clear old data to avoid confusion
            self.networks.clear()
            self.table_manager.clear()
            self.update_statistics()
            
            # Clear selected network dashboard
            self.card_ssid.set_value("—")
            self.card_signal.set_value("—")
            self.card_security.set_value("—")
            self.card_score.set_value("—")
            
            QMessageBox.critical(self, "Scan Failed", f"{msg}\n\nSee logs for details.")
        
        def do_best(self) -> None:
            """Find and highlight best network."""
            if not self.networks:
                QMessageBox.information(self, "No Data", "Run a scan first.")
                return
            
            best = pick_best(self.networks)
            if best:
                # Find row and select
                for row in range(self.table.rowCount()):
                    bssid_item = self.table.item(row, 1)
                    if bssid_item and bssid_item.text().lower() == best.bssid.lower():
                        self.table.selectRow(row)
                        self.table.scrollToItem(bssid_item)
                        break
                
                msg = f"Best: {best.ssid}\nSignal: {best.signal_dbm} dBm\nSecurity: {best.security}\nScore: {best.score:.1f}"
                QMessageBox.information(self, "Best Network", msg)
        
        def connect_to_selected(self) -> None:
            """Connect to selected WiFi network."""
            selected = self.table.selectedItems()
            if not selected:
                QMessageBox.information(self, "No Selection", "Select a network first.")
                return
            
            # Rate limiting
            current_time = time.time()
            if current_time - self.last_connection_attempt < self.connection_rate_limit_seconds:
                remaining = self.connection_rate_limit_seconds - (current_time - self.last_connection_attempt)
                QMessageBox.warning(self, "Rate Limited", f"Wait {remaining:.1f}s before connecting again.")
                return
            
            row = selected[0].row()
            ssid_item = self.table.item(row, 0)
            
            if not ssid_item:
                return
            
            ssid = ssid_item.text()
            
            # Prompt for password
            password, ok = QInputDialog.getText(
                self, "Network Password", f"Enter password for '{ssid}':",
                QLineEdit.EchoMode.Password
            )
            
            if not ok:
                return
            
            self.last_connection_attempt = current_time
            self.statusBar().showMessage(f"Connecting to {ssid}…")
            
            success, message = connect_to_network(ssid, password if password else None, self.logger)
            
            if success:
                QMessageBox.information(self, "Success", message)
                QTimer.singleShot(2000, self.do_scan)
            else:
                QMessageBox.warning(self, "Failed", message)
        
        def do_export(self) -> None:
            """Export WiFi scan results."""
            if not self.networks:
                QMessageBox.information(self, "No Data", "Run a scan first.")
                return
            
            path, _ = QFileDialog.getSaveFileName(
                self, "Export", "", "JSON (*.json);;CSV (*.csv)"
            )
            
            if not path:
                return
            
            try:
                import csv
                if path.lower().endswith(".json"):
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump([asdict(n) for n in self.networks], f, indent=2, default=str)
                else:
                    with open(path, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["SSID", "BSSID", "Signal", "Security", "Channel", "Band", "Score"])
                        for n in self.networks:
                            writer.writerow([n.ssid, n.bssid, n.signal_dbm, n.security, 
                                           n.channel, n.band, n.score])
                
                QMessageBox.information(self, "Success", f"Exported to {path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        
        # ==================== UI Helpers ====================
        
        def format_network_row(self, network: WifiNetwork) -> List[str]:
            """Format network data for table row."""
            return [
                network.ssid,
                network.bssid,
                "" if network.signal_dbm is None else str(network.signal_dbm),
                "" if network.signal_percent is None else str(network.signal_percent),
                "" if network.channel is None else str(network.channel),
                "" if network.band is None else network.band,
                network.security,
                "" if network.score is None else f"{network.score:.1f}",
                "●" if network.is_connected else ""
            ][:len(COLUMNS) if COLUMNS else 7]
        
        def apply_row_colors(self, item: QTableWidgetItem, col: int, network: WifiNetwork) -> None:
            """Apply colors to table cells."""
            # Numeric alignment
            if col in (2, 3, 4, 7):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Signal coloring
            if col == 2 and network.signal_dbm is not None:
                if network.signal_dbm >= -50:
                    item.setForeground(QBrush(QColor(0, 200, 0)))
                elif network.signal_dbm >= -65:
                    item.setForeground(QBrush(QColor(200, 200, 0)))
                else:
                    item.setForeground(QBrush(QColor(200, 0, 0)))
            
            # Connected highlight
            if network.is_connected:
                item.setBackground(QBrush(QColor(200, 255, 200) if not self.dark_mode else QColor(0, 80, 0)))
        
        def on_selection_changed(self) -> None:
            """Handle table selection change."""
            selected = self.table.selectedItems()
            if not selected:
                return
            
            row = selected[0].row()
            bssid_item = self.table.item(row, 1)
            
            if not bssid_item:
                return
            
            bssid = bssid_item.text().lower()
            network = next((n for n in self.networks if n.bssid.lower() == bssid), None)
            
            if network:
                self.update_selected_dashboard(network)
                self.update_detail_labels(network)
        
        def update_selected_dashboard(self, net: WifiNetwork) -> None:
            """Update selected network dashboard cards."""
            self.card_ssid.set_value(net.ssid or "—")
            self.card_signal.set_value(f"{net.signal_dbm} dBm" if net.signal_dbm else "—")
            self.card_security.set_value(net.security or "—")
            self.card_score.set_value(f"{net.score:.1f}" if net.score else "—")
        
        def update_detail_labels(self, net: WifiNetwork) -> None:
            """Update details tab labels."""
            self.detail_labels["ssid"].setText(net.ssid or "—")
            self.detail_labels["bssid"].setText(net.bssid or "—")
            self.detail_labels["signal_dbm"].setText(f"{net.signal_dbm} dBm" if net.signal_dbm else "—")
            self.detail_labels["security"].setText(net.security or "—")
            self.detail_labels["channel"].setText(str(net.channel) if net.channel else "—")
            self.detail_labels["band"].setText(net.band or "—")
            self.detail_labels["score"].setText(f"{net.score:.2f}" if net.score else "—")
        
        def update_statistics(self) -> None:
            """Update statistics panel."""
            self.lbl_total.setText(f"Networks: {len(self.networks)}")
            
            connected = next((n for n in self.networks if n.is_connected), None)
            if connected:
                self.lbl_connected.setText(f"Connected: {connected.ssid}")
            else:
                self.lbl_connected.setText("Connected: None")
        
        def update_chart(self) -> None:
            """Update signal history chart."""
            if not HAS_MATPLOTLIB:
                return
            
            selection = self.chart_selector.currentText()
            if selection == "All (top 5)":
                sorted_nets = sorted(self.networks, 
                                   key=lambda n: n.signal_dbm if n.signal_dbm else -999, 
                                   reverse=True)
                bssids = [n.bssid for n in sorted_nets[:5]]
            else:
                bssid = self.chart_selector.currentData()
                bssids = [bssid] if bssid else []
            
            self.chart.plot_history(self.network_history, bssids)
        
        def set_busy(self, busy: bool) -> None:
            """Set busy state for UI controls."""
            self.progress_bar.setVisible(busy)
            self.btn_scan.setEnabled(not busy)
            self.btn_best.setEnabled(not busy)
            self.btn_connect.setEnabled(not busy)
            self.btn_export.setEnabled(not busy)
        
        def toggle_auto_scan(self, enabled: bool) -> None:
            """Toggle auto-scan timer."""
            if enabled:
                interval = self.spin_interval.value()
                self.scan_timer.start(interval * 1000)
                self.logger.info("Auto-scan enabled: every %ds", interval)
                self.do_scan()
            else:
                self.scan_timer.stop()
                self.logger.info("Auto-scan disabled")
        
        # ==================== Theme & Settings ====================
        
        def apply_theme(self) -> None:
            """Apply dark or light theme."""
            if self.dark_mode:
                self.setStyleSheet("""
                    QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
                    QTableWidget { background-color: #3c3c3c; alternate-background-color: #454545; }
                    QPushButton { background-color: #0d7377; color: white; border: none; 
                                 padding: 8px 16px; border-radius: 6px; font-weight: bold; }
                    QPushButton:hover { background-color: #14a085; }
                    #MetricCard { background: #3a3a3a; border: 2px solid #555; border-radius: 12px; }
                    #MetricValue { font-size: 20px; font-weight: 700; color: #14a085; }
                """)
            else:
                self.setStyleSheet("""
                    QPushButton { background-color: #0d7377; color: white; border: none; 
                                 padding: 8px 16px; border-radius: 6px; font-weight: bold; }
                    QPushButton:hover { background-color: #14a085; }
                    #MetricCard { background: #f8f8f8; border: 2px solid #d0d0d0; border-radius: 12px; }
                    #MetricValue { font-size: 20px; font-weight: 700; color: #0d7377; }
                """)
        
        def toggle_theme(self) -> None:
            """Toggle between dark and light theme."""
            self.dark_mode = not self.dark_mode
            self.apply_theme()
            self.logger.info("Theme: %s", "dark" if self.dark_mode else "light")
        
        def restore_settings(self) -> None:
            """Restore settings from QSettings."""
            settings = QSettings("NetworkSuite", "WiFiScout")
            
            # Theme (already safe - bool type)
            self.dark_mode = settings.value("theme/dark_mode", False, type=bool)
            
            # Scan interval - validate range to prevent corrupted settings from crashing
            interval = settings.value("wifi/scan_interval", 10, type=int)
            interval = max(5, min(300, interval))  # Clamp to valid range (5-300 seconds)
            self.spin_interval.setValue(interval)
            
            # Window geometry - validate before restoring
            geometry = settings.value("window/geometry")
            if geometry:
                try:
                    self.restoreGeometry(geometry)
                except Exception as e:
                    self.logger.warning("Failed to restore window geometry: %s", e)
        
        def save_settings(self) -> None:
            """Save settings to QSettings."""
            settings = QSettings("NetworkSuite", "WiFiScout")
            settings.setValue("theme/dark_mode", self.dark_mode)
            settings.setValue("wifi/scan_interval", self.spin_interval.value())
            settings.setValue("window/geometry", self.saveGeometry())
        
        def closeEvent(self, event) -> None:
            """Handle window close event."""
            # Stop any running scans
            if self.scan_thread and self.scan_thread.isRunning():
                self.scan_thread.quit()
                self.scan_thread.wait(1000)
            
            # Stop auto-scan timer
            if self.scan_timer:
                self.scan_timer.stop()
            
            self.save_settings()
            event.accept()
        
        # ==================== Misc ====================
        
        def show_about(self) -> None:
            """Show about dialog."""
            about_text = f"<h2>{APP_NAME} v{APP_VERSION}</h2>"
            about_text += "<p>Modular network diagnostic suite</p>"
            about_text += f"<p>Platform: {platform.system()}</p>"
            about_text += f"<p>Loaded mods: {len(TOOL_REGISTRY)}</p>"
            QMessageBox.about(self, f"About {APP_NAME}", about_text)
        
        def copy_log_path(self) -> None:
            """Copy log path to clipboard."""
            QApplication.clipboard().setText(str(self.log_path))
            self.statusBar().showMessage("Log path copied", 3000)


# ==================== CLI INTERFACE ====================

def create_cli_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser with mod subcommands."""
    parser = argparse.ArgumentParser(
        prog="network_suite",
        description=f"{APP_NAME} v{APP_VERSION} - Modular Network Diagnostics",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # WiFi subcommand
    wifi_parser = subparsers.add_parser("wifi", help="WiFi scanning and management")
    wifi_sub = wifi_parser.add_subparsers(dest="wifi_action")
    
    scan_parser = wifi_sub.add_parser("scan", help="Scan for WiFi networks")
    scan_parser.add_argument("--band", choices=["all", "2.4", "5", "6"], default="all")
    scan_parser.add_argument("--sort", choices=["signal", "ssid", "score"], default="score")
    
    connect_parser = wifi_sub.add_parser("connect", help="Connect to network")
    connect_parser.add_argument("ssid", help="Network SSID")
    connect_parser.add_argument("--password", "-p", help="Network password")
    
    best_parser = wifi_sub.add_parser("best", help="Find best network")
    
    # Add subcommands for each mod
    for tool_name, tool in TOOL_REGISTRY.items():
        try:
            if hasattr(tool, 'get_cli_parser'):
                tool_parser = subparsers.add_parser(
                    tool_name.lower().replace(" ", "-"),
                    help=getattr(tool, 'DESCRIPTION', tool_name)
                )
                tool.get_cli_parser(tool_parser)
        except Exception as e:
            print(f"Warning: Failed to register CLI for {tool_name}: {e}")
    
    return parser


def run_cli(args) -> int:
    """Execute CLI command and return exit code."""
    # Setup logging
    log_path = Path.home() / ".network_suite" / "cli.log"
    log_path.parent.mkdir(exist_ok=True)
    logger = make_logger(str(log_path))
    
    # Load mods
    load_mods(logger)
    
    if not args.command:
        print("No command specified. Use --help for options.")
        return 1
    
    # Route to appropriate handler
    if args.command == "wifi":
        return handle_wifi_cli(args, logger)
    else:
        # Check if it's a mod command
        for tool_name, tool in TOOL_REGISTRY.items():
            if args.command == tool_name.lower().replace(" ", "-"):
                if hasattr(tool, 'cli_handler'):
                    return tool.cli_handler(args, logger)
        
        print(f"Unknown command: {args.command}")
        return 1


def handle_wifi_cli(args, logger) -> int:
    """Handle WiFi CLI commands."""
    if args.wifi_action == "scan":
        try:
            networks = scan_wifi(logger)
            
            if not networks:
                print("No networks found.")
                return 1
            
            # Mark connected and enrich
            mark_connected_and_enrich(logger, networks)
            
            # Score networks
            for n in networks:
                n.score = score_network(networks, n)
            
            # Sort
            if hasattr(args, 'sort'):
                if args.sort == "signal":
                    networks.sort(key=lambda n: n.signal_dbm if n.signal_dbm else -999, reverse=True)
                elif args.sort == "ssid":
                    networks.sort(key=lambda n: n.ssid or "")
                else:  # score
                    networks.sort(key=lambda n: n.score if n.score else 0, reverse=True)
            
            if args.format == "json":
                print(json.dumps([asdict(n) for n in networks], indent=2, default=str))
            else:
                print(f"\n{'SSID':<30} {'Signal':<10} {'Security':<15} {'Score':<8} {'Connected'}")
                print("-" * 80)
                for n in networks:
                    conn = "●" if n.is_connected else ""
                    sig = f"{n.signal_dbm} dBm" if n.signal_dbm else "N/A"
                    score_str = f"{n.score:.1f}" if n.score else "N/A"
                    print(f"{n.ssid:<30} {sig:<10} {n.security:<15} {score_str:<8} {conn}")
                print(f"\nTotal: {len(networks)} networks")
            return 0
        except Exception as e:
            logger.error("Scan failed: %s", e, exc_info=True)
            print(f"Error: {e}")
            return 1
    
    elif args.wifi_action == "connect":
        try:
            success, message = connect_to_network(args.ssid, args.password, logger)
            print(message)
            return 0 if success else 1
        except Exception as e:
            logger.error("Connect failed: %s", e, exc_info=True)
            print(f"Error: {e}")
            return 1
    
    elif args.wifi_action == "best":
        try:
            networks = scan_wifi(logger)
            
            if not networks:
                print("No networks found.")
                return 1
            
            mark_connected_and_enrich(logger, networks)
            for n in networks:
                n.score = score_network(networks, n)
            
            best = pick_best(networks)
            if best:
                print(f"\n✅ Best Network:")
                print(f"  SSID:     {best.ssid}")
                print(f"  Signal:   {best.signal_dbm} dBm")
                print(f"  Security: {best.security}")
                print(f"  Channel:  {best.channel}")
                print(f"  Score:    {best.score:.1f}")
                return 0
            else:
                print("No suitable networks found.")
                return 1
        except Exception as e:
            logger.error("Best network search failed: %s", e, exc_info=True)
            print(f"Error: {e}")
            return 1
    
    print(f"Unknown WiFi action: {args.wifi_action}")
    return 1


# ==================== MAIN ENTRY POINT ====================

def main() -> int:
    """Main entry point - detect GUI or CLI mode."""
    
    # Check for CLI arguments
    if len(sys.argv) > 1:
        parser = create_cli_parser()
        args = parser.parse_args()
        return run_cli(args)
    
    # Launch GUI if PyQt6 available
    if HAS_PYQT6:
        app = QApplication(sys.argv)
        win = MainWindow()
        win.resize(1400, 900)
        win.show()
        return app.exec()
    else:
        print(f"{APP_NAME} v{APP_VERSION}")
        print("PyQt6 not installed. GUI mode unavailable.")
        print("Install: pip install PyQt6")
        print("\nUse CLI mode: python network_suite.py --help")
        return 1


def cli_main() -> None:
    """Console script entry point for setuptools."""
    sys.exit(main())


if __name__ == "__main__":
    sys.exit(main())
