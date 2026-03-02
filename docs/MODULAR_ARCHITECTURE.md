# Network Suite - Modular Architecture Plan

## New Architecture: Core + Mods System

### Overview
- **Core System** (`network_suite.py`): ~1,500-2,000 lines
  - WiFi functionality (preserved from wa.py)
  - Plugin loader and registry
  - GUI framework with dynamic tab creation
  - CLI dispatcher
  - Shared utilities
  
- **Mods** (`/mods/` directory): Separate files, hot-loadable
  - Each mod = 200-400 lines
  - Self-contained: data models, logic, GUI panel, CLI handler
  - Registered via decorator pattern
  - Appears as tab in GUI under "Mods" section

### Benefits
- ✅ Core system stays stable
- ✅ Easy to add/remove features
- ✅ Community can contribute mods
- ✅ Each mod independently testable
- ✅ No code changes to core for new features
- ✅ Cleaner separation of concerns

---

## File Structure

```
wifi_scout/
├── network_suite.py          # Core system (~1,800 lines)
├── mods/                      # Plugin modules
│   ├── __init__.py           # Mod discovery
│   ├── dns_tool.py           # DNS lookup mod (~300 lines)
│   ├── ping_tool.py          # Ping mod (~250 lines)
│   ├── traceroute_tool.py    # Traceroute mod (~300 lines)
│   ├── http_tool.py          # HTTP checker mod (~350 lines)
│   ├── interfaces_tool.py    # Interface viewer (~300 lines)
│   ├── arp_tool.py           # ARP viewer (~200 lines)
│   ├── route_tool.py         # Routing table (~250 lines)
│   └── lan_scan_tool.py      # LAN discovery (~400 lines)
├── requirements.txt
└── README.md
```

---

## Implementation Strategy: 4 Prompts

### 🔵 PROMPT 1: Core System Foundation
**Goal**: Create fully working core system with WiFi + plugin framework  
**Deliverables**:
- `network_suite.py` (~1,800 lines)
  - Complete WiFi functionality from wa.py
  - Incremental table updates
  - Plugin loader with discovery
  - GUI framework with dynamic tab creation
  - CLI framework with subcommand routing
  - QSettings persistence
  - Shared utilities (logging, command runner, parsers)
  - Example "Hello World" mod for testing
  
- `mods/__init__.py` - Mod discovery and registration

**Testing**: Core app runs, WiFi works, empty "Mods" menu ready

---

### 🟢 PROMPT 2: Network Diagnostic Mods (Part 1)
**Goal**: Add DNS and Ping tools as separate mods  
**Deliverables**:
- `mods/dns_tool.py` (~300 lines)
  - DNSResult data model
  - Query logic (dnspython + fallback)
  - GUI panel with inputs/results
  - CLI handler
  - Self-tests
  
- `mods/ping_tool.py` (~250 lines)
  - PingResult data model
  - Cross-platform ping execution
  - Output parsing (Win/Linux/Mac)
  - GUI panel with live output
  - CLI handler
  - Self-tests

**Testing**: `python network_suite.py` shows DNS and Ping tabs under Mods. CLI works: `python network_suite.py dns example.com`, `python network_suite.py ping 8.8.8.8`

---

### 🟡 PROMPT 3: Network Diagnostic Mods (Part 2)
**Goal**: Add Traceroute, HTTP, and Interface viewer  
**Deliverables**:
- `mods/traceroute_tool.py` (~300 lines)
  - TracerouteResult with hop data
  - Cross-platform traceroute parsing
  - GUI panel with hop table
  - CLI handler
  
- `mods/http_tool.py` (~350 lines)
  - HTTPResult with timing breakdown
  - urllib implementation with hooks
  - Certificate extraction for HTTPS
  - GUI panel with timing visualization
  - CLI handler
  
- `mods/interfaces_tool.py` (~300 lines)
  - InterfaceInfo data model
  - psutil + OS command fallback
  - Gateway/DNS detection
  - GUI panel with interface list
  - CLI handler

**Testing**: All 5 core mods working in GUI and CLI

---

### 🔴 PROMPT 4: Advanced Mods + Polish
**Goal**: Add ARP, Routing, LAN scan, and finalize  
**Deliverables**:
- `mods/arp_tool.py` (~200 lines)
  - ARP table parsing
  - GUI panel
  - CLI handler
  
- `mods/route_tool.py` (~250 lines)
  - Routing table parsing
  - GUI panel
  - CLI handler
  
- `mods/lan_scan_tool.py` (~400 lines)
  - CIDR validation (RFC1918 only)
  - Rate-limited ping sweep
  - Safety warnings
  - GUI panel with confirmation
  - CLI handler
  
- Final polish:
  - Update README with mod development guide
  - Add mod template file
  - Complete all self-tests
  - Performance testing
  - Bug fixes

**Testing**: Complete suite with 8 mods, all tests passing

---

## Mod API Design

### Mod Structure Template

```python
"""
Mod Name: Example Tool
Description: Brief description of what this tool does
Author: Your Name
Version: 1.0
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

# ========== DATA MODELS ==========

@dataclass
class ExampleResult:
    """Result data for this tool."""
    timestamp: float
    success: bool
    data: Any
    error: Optional[str] = None

# ========== TOOL IMPLEMENTATION ==========

class ExampleTool:
    """Main tool class - auto-discovered by core."""
    
    # Required metadata
    NAME = "Example Tool"
    DESCRIPTION = "Does something useful"
    CATEGORY = "network"  # network, system, security, etc.
    VERSION = "1.0"
    
    def __init__(self):
        self.logger = None  # Set by core
    
    def run(self, params: Dict[str, Any]) -> ExampleResult:
        """Execute the tool with given parameters."""
        # Implementation here
        pass
    
    def get_gui_panel(self, parent) -> "QWidget":
        """Return PyQt6 widget for this tool's GUI."""
        # Build and return widget
        pass
    
    def get_cli_parser(self, subparser):
        """Add CLI arguments to argparse subparser."""
        # Add arguments
        pass
    
    def cli_handler(self, args, logger) -> int:
        """Handle CLI execution, return exit code."""
        # Execute and output results
        pass
    
    def self_test(self) -> bool:
        """Run embedded tests, return True if pass."""
        # Test with sample data
        pass

# ========== REGISTRATION ==========

def register():
    """Called by core to register this mod."""
    return ExampleTool()
```

### Core Integration

The core system in `network_suite.py` will:

```python
# Auto-discover and load mods
def load_mods():
    mods_dir = Path(__file__).parent / "mods"
    for mod_file in mods_dir.glob("*_tool.py"):
        spec = importlib.util.spec_from_file_location(mod_file.stem, mod_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, 'register'):
            tool = module.register()
            TOOL_REGISTRY[tool.NAME] = tool

# Create GUI tabs dynamically
def create_mod_tabs(self):
    self.mods_tab = QTabWidget()
    self.tabs.addTab(self.mods_tab, "Mods")
    
    for name, tool in TOOL_REGISTRY.items():
        panel = tool.get_gui_panel(self)
        self.mods_tab.addTab(panel, name)

# Route CLI commands
def handle_cli():
    parser = create_parser()
    # Add subcommand for each mod
    for name, tool in TOOL_REGISTRY.items():
        subparser = parser.add_subparsers()
        tool_parser = subparser.add_parser(name.lower().replace(' ', '-'))
        tool.get_cli_parser(tool_parser)
```

---

## Prompt Execution Plan

### Before Starting
- [x] Create `IMPLEMENTATION_LOG.md` (done)
- [x] Create this architecture plan
- [ ] Review and approve approach
- [ ] Create `/mods/` directory

### Prompt 1 Checklist
- [✅] Core `network_suite.py` with WiFi (~1100 lines - complete)
- [✅] Plugin loader system
- [✅] GUI framework with Mods tab
- [✅] CLI framework (complete with WiFi subcommands)
- [✅] `core/wifi_engine.py` (WiFi scanning, scoring, connection logic - ~700 lines)
- [✅] `core/utilities.py` (Shared utilities, validators, parsers - ~180 lines)
- [✅] `mods/__init__.py`
- [✅] Example mod for testing (`mods/example_tool.py`)
- [ ] Test: Core runs, WiFi works

### Prompt 2 Checklist  
- [✅] `mods/dns_tool.py` complete (~450 lines)
- [✅] `mods/ping_tool.py` complete (~450 lines)
- [ ] Test: Both mods show in GUI
- [ ] Test: CLI commands work
- [ ] Update implementation log

### Prompt 3 Checklist
- [✅] `mods/traceroute_tool.py` complete (~550 lines)
- [✅] `mods/http_tool.py` complete (~550 lines)
- [✅] `mods/interfaces_tool.py` complete (~550 lines)
- [ ] Test: All 5 mods working in GUI and CLI
- [ ] Update implementation log

### Prompt 4 Checklist
- [✅] `mods/arp_tool.py` complete (~400 lines)
- [✅] `mods/route_tool.py` complete (~450 lines)
- [✅] `mods/lan_scan_tool.py` complete (~550 lines)
- [✅] Mod development template (example_tool.py)
- [✅] README updates (existing README.md is comprehensive)
- [ ] All self-tests passing
- [ ] Performance validation
- [ ] Final implementation log update

---

## Advantages of This Approach

1. **Manageable Scope**: Each prompt creates 400-600 lines of tested code
2. **Incremental Testing**: Each stage is fully functional
3. **Clean Separation**: Core never needs modification for new mods
4. **Community Ready**: Others can create mods following template
5. **Debugging**: Issues isolated to specific mod files
6. **Version Control**: Each mod can be versioned independently
7. **Dependencies**: Mods can have optional dependencies (checked at load time)

---

## Success Criteria

### Prompt 1 Complete When:
✅ Core app launches with WiFi tab  
✅ Empty "Mods" tab present  
✅ CLI shows `--help` with mod structure  
✅ Example mod loads and shows

### Prompt 2 Complete When:
✅ DNS mod: Can query records in GUI and CLI  
✅ Ping mod: Can ping hosts in GUI and CLI  
✅ Both mods appear in Mods tab  
✅ CLI routes to mod handlers

### Prompt 3 Complete When:
✅ Traceroute works on all platforms  
✅ HTTP tool shows timing breakdown  
✅ Interface viewer shows all network info  
✅ 5 total mods in Mods tab

### Prompt 4 Complete When:
✅ All 8 mods functional  
✅ LAN scan has safety warnings  
✅ Mod template documented  
✅ All self-tests pass  
✅ README complete

---

## Ready to Proceed?

**PROMPT 1 is ready to execute:** Create core system with WiFi + plugin framework.

Say "START PROMPT 1" to begin implementation.
