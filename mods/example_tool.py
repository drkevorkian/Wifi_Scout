"""
Example Tool - Template for creating Network Suite mods.

This is a minimal example showing the required structure for a mod.
Copy this file and modify it to create your own tools.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time

try:
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
    from PyQt6.QtCore import Qt
    HAS_PYQT6 = True
except ImportError:
    HAS_PYQT6 = False


# ==================== DATA MODEL ====================

@dataclass
class ExampleResult:
    """Result data for this example tool."""
    timestamp: float
    message: str
    success: bool = True


# ==================== TOOL CLASS ====================

class ExampleTool:
    """
    Example diagnostic tool demonstrating the mod API.
    
    Required attributes:
    - NAME: Display name for the tool
    - DESCRIPTION: Brief description
    - CATEGORY: Tool category (network, system, security, etc.)
    - VERSION: Tool version
    
    Required methods:
    - get_gui_panel(parent): Return PyQt6 widget for GUI
    - get_cli_parser(subparser): Add CLI arguments
    - cli_handler(args, logger): Handle CLI execution
    """
    
    NAME = "Example Tool"
    DESCRIPTION = "Demonstrates the mod plugin system"
    CATEGORY = "system"
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None
    
    def run(self, params: Dict[str, Any]) -> ExampleResult:
        """Execute the tool with given parameters."""
        message = params.get("message", "Hello from Example Tool!")
        
        if self.logger:
            self.logger.info(f"ExampleTool running: {message}")
        
        return ExampleResult(
            timestamp=time.time(),
            message=message,
            success=True
        )
    
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
        
        # Description
        desc = QLabel(self.DESCRIPTION)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(desc)
        
        # Action button
        btn = QPushButton("Run Example")
        btn.clicked.connect(lambda: self._on_run_clicked(output))
        layout.addWidget(btn)
        
        # Output area
        output = QTextEdit()
        output.setReadOnly(True)
        output.setPlaceholderText("Click 'Run Example' to test...")
        layout.addWidget(output, 1)
        
        layout.addStretch()
        return widget
    
    def _on_run_clicked(self, output_widget):
        """Handle GUI button click."""
        result = self.run({"message": "GUI execution successful!"})
        output_widget.append(f"\n[{time.strftime('%H:%M:%S')}]")
        output_widget.append(f"✅ {result.message}")
        output_widget.append(f"Timestamp: {result.timestamp}")
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        subparser.add_argument(
            "--message", "-m",
            default="Hello from CLI!",
            help="Custom message to display"
        )
    
    def cli_handler(self, args, logger) -> int:
        """Handle CLI execution, return exit code."""
        self.logger = logger
        
        try:
            result = self.run({"message": args.message})
            
            print(f"\n✅ {self.NAME} v{self.VERSION}")
            print(f"Message: {result.message}")
            print(f"Timestamp: {result.timestamp}")
            print(f"Status: {'Success' if result.success else 'Failed'}")
            
            return 0 if result.success else 1
        
        except Exception as e:
            logger.error(f"{self.NAME} failed: {e}", exc_info=True)
            print(f"❌ Error: {e}")
            return 1


# ==================== REGISTRATION ====================

def register():
    """
    Called by core to register this mod.
    Must return an instance of the tool class.
    """
    return ExampleTool()
