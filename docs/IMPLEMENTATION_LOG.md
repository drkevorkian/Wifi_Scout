# Network Suite Implementation Log

## Project Overview
**Goal**: Refactor wa.py into a comprehensive single-file "Network Suite"  
**Target Size**: ~4,000-5,000 lines (focused subset)  
**Status**: In Progress

---

## Implementation Phases

### ✅ Phase 1: Foundation & Core Infrastructure (Lines 1-1000)
- [ ] **1.1** Imports with feature detection (PyQt6, matplotlib, psutil, dnspython)
- [ ] **1.2** Global constants and feature flags
- [ ] **1.3** Data models: WifiNetwork, NetworkHistory, ToolResult base
- [ ] **1.4** Tool-specific result models: DNSResult, PingResult, TracerouteResult, HTTPResult, InterfaceInfo
- [ ] **1.5** Logging utilities (make_logger, QtLogHandler)
- [ ] **1.6** Command runner with validation
- [ ] **1.7** HTML/XML escape utilities
- [ ] **1.8** SSID/Password validators
- [ ] **1.9** Secure file deletion
- [ ] **1.10** Text sanitizer for logs

### ✅ Phase 2: WiFi Core (Preserved & Enhanced) (Lines 1001-2200)
- [ ] **2.1** WiFi helper functions (infer_band, percent_to_dbm, compute_snr, normalize_security)
- [ ] **2.2** Windows netsh scanner
- [ ] **2.3** Linux nmcli scanner
- [ ] **2.4** macOS airport scanner
- [ ] **2.5** Connected BSSID detection (all platforms)
- [ ] **2.6** Link metrics enrichment
- [ ] **2.7** Scoring algorithm with breakdown
- [ ] **2.8** Channel congestion calculation
- [ ] **2.9** Pick best network
- [ ] **2.10** Secure connection management (all platforms)
- [ ] **2.11** ScanThread for async scanning
- [ ] **2.12** Score caching decorator

### ✅ Phase 3: Plugin System & Network Tools (Lines 2201-3300)
- [ ] **3.1** DiagnosticTool base class (ABC)
- [ ] **3.2** Tool registry system
- [ ] **3.3** **DNSTool**: Query A/AAAA/CNAME/MX/TXT/NS records
  - [ ] Backend: dnspython with nslookup/dig fallback
  - [ ] GUI panel: hostname input, record type checkboxes, results table
  - [ ] CLI: `dns lookup example.com --types A AAAA`
- [ ] **3.4** **PingTool**: ICMP echo test with statistics
  - [ ] Backend: Cross-platform ping parsing (Windows/Linux/macOS)
  - [ ] GUI panel: host input, count spinner, live output, stats display
  - [ ] CLI: `ping 8.8.8.8 -c 4`
- [ ] **3.5** **TracerouteTool**: Route tracing with hop details
  - [ ] Backend: tracert/traceroute parsing
  - [ ] GUI panel: host input, max hops, hop-by-hop table
  - [ ] CLI: `traceroute example.com`
- [ ] **3.6** **HTTPTool**: HTTP/HTTPS with timing breakdown
  - [ ] Backend: urllib with timing hooks, cert extraction
  - [ ] GUI panel: URL input, method selector, timing chart, headers viewer
  - [ ] CLI: `http get https://example.com`
- [ ] **3.7** **InterfaceViewerTool**: Show local interfaces
  - [ ] Backend: psutil with ifconfig/ipconfig fallback
  - [ ] GUI panel: Interface list with IP/MAC/MTU, gateway/DNS info
  - [ ] CLI: `interfaces list`

### ✅ Phase 4: Task Runner (Lines 3301-3500)
- [ ] **4.1** QRunnable wrapper for tool tasks
- [ ] **4.2** TaskRunner class with QThreadPool
- [ ] **4.3** Progress signal handling
- [ ] **4.4** Cancellation support
- [ ] **4.5** Max worker limit configuration

### ✅ Phase 5: GUI Components (Lines 3501-4000)
- [ ] **5.1** **IncrementalTableManager**: BSSID-keyed row tracking
  - [ ] Row map maintenance
  - [ ] Incremental add/update/remove
  - [ ] Cell-level diff checking
  - [ ] Selection preservation
- [ ] **5.2** **GenericToolPanel**: Reusable tool UI component
  - [ ] Input section (dynamic based on tool)
  - [ ] Run button with busy state
  - [ ] Output table/text display
  - [ ] Export button
- [ ] **5.3** Enhanced MetricCard (preserved from original)
- [ ] **5.4** Enhanced SignalChart (preserved from original)
- [ ] **5.5** QSettings integration helpers

### ✅ Phase 6: GUI Main Window (Lines 4001-5200)
- [ ] **6.1** MainWindow initialization with QSettings restore
- [ ] **6.2** Menu bar with all actions
- [ ] **6.3** **WiFi Scanner Tab** (enhanced with incremental updates)
  - [ ] Controls panel with persistence
  - [ ] Statistics panel
  - [ ] Selected network dashboard
  - [ ] Incremental table (IncrementalTableManager)
  - [ ] All existing features preserved
- [ ] **6.4** **Network Tools Tab** (new)
  - [ ] InterfaceViewer panel
  - [ ] Gateway/DNS display
  - [ ] Quick access to other tools
- [ ] **6.5** **DNS Tab** (new)
  - [ ] GenericToolPanel integration
  - [ ] Record type selection
  - [ ] Results display
- [ ] **6.6** **Ping/Traceroute Tab** (new)
  - [ ] Mode toggle (ping/traceroute)
  - [ ] Host input
  - [ ] Live output display
  - [ ] Statistics panel
- [ ] **6.7** **HTTP Tab** (new)
  - [ ] URL input with method selector
  - [ ] Timing visualization
  - [ ] Headers display
  - [ ] Certificate viewer
- [ ] **6.8** **Logs Tab** (enhanced)
  - [ ] Filter by level dropdown
  - [ ] Search box
  - [ ] Clear/copy/open folder buttons
- [ ] **6.9** Theme system (dark/light with persistence)
- [ ] **6.10** QSettings save on close

### ✅ Phase 7: CLI Interface (Lines 5201-5800)
- [ ] **7.1** argparse parser with subcommands
- [ ] **7.2** WiFi CLI: `wifi scan`, `wifi connect SSID`
- [ ] **7.3** DNS CLI: `dns lookup HOSTNAME --types A AAAA`
- [ ] **7.4** Ping CLI: `ping HOST -c COUNT`
- [ ] **7.5** Traceroute CLI: `traceroute HOST`
- [ ] **7.6** HTTP CLI: `http METHOD URL`
- [ ] **7.7** Interfaces CLI: `interfaces list`
- [ ] **7.8** JSON output formatter
- [ ] **7.9** Text table output formatter
- [ ] **7.10** CSV output formatter

### ✅ Phase 8: Self-Test Framework (Lines 5801-6200)
- [ ] **8.1** Embedded sample outputs (netsh, nmcli, airport, ping, traceroute, etc.)
- [ ] **8.2** Parser test for Windows netsh
- [ ] **8.3** Parser test for Linux nmcli
- [ ] **8.4** Parser test for macOS airport
- [ ] **8.5** Parser test for Windows ping
- [ ] **8.6** Parser test for Linux ping
- [ ] **8.7** Parser test for Windows tracert
- [ ] **8.8** Parser test for Linux traceroute
- [ ] **8.9** Test harness with reporting
- [ ] **8.10** `--self-test` CLI flag

### ✅ Phase 9: Main Entry & Integration (Lines 6201-6400)
- [ ] **9.1** Entry point detection (GUI vs CLI)
- [ ] **9.2** Feature flag checks and graceful degradation
- [ ] **9.3** GUI launcher
- [ ] **9.4** CLI dispatcher
- [ ] **9.5** Self-test runner
- [ ] **9.6** Error handling and help messages
- [ ] **9.7** Version info and about

---

## Deferred Features (Future Enhancement)

These features are designed but not in the focused subset:

- [ ] **ARP Viewer Tool**: ARP table parsing and display
- [ ] **Routing Table Viewer**: Route table parsing
- [ ] **LAN Discovery Tool**: Ping sweep (with safety warnings and rate limiting)
- [ ] **Port Scanner Tool**: TCP connect scanning (opt-in, rate-limited)
- [ ] **Bandwidth Test**: Speed test functionality
- [ ] **Packet Capture**: Basic packet sniffing (requires elevated permissions)

---

## Testing Checklist

### WiFi Functionality
- [ ] Scan works on Windows
- [ ] Scan works on Linux
- [ ] Scan works on macOS
- [ ] Connect to network works
- [ ] Best network recommendation works
- [ ] Signal history chart works
- [ ] Filters work (search, band, hide open)
- [ ] Export works (CSV, JSON, HTML)
- [ ] Theme toggle works
- [ ] Auto-refresh works
- [ ] Incremental table updates (no flicker)
- [ ] Settings persistence works

### DNS Tool
- [ ] Query A record works
- [ ] Query AAAA record works
- [ ] Query MX record works
- [ ] Multiple record types work
- [ ] CLI mode works
- [ ] GUI panel works

### Ping Tool
- [ ] Ping works on Windows
- [ ] Ping works on Linux
- [ ] Ping works on macOS
- [ ] Statistics parsing correct
- [ ] CLI mode works
- [ ] GUI panel works

### Traceroute Tool
- [ ] Traceroute works on Windows
- [ ] Traceroute works on Linux
- [ ] Traceroute works on macOS
- [ ] Hop parsing correct
- [ ] CLI mode works
- [ ] GUI panel works

### HTTP Tool
- [ ] HTTP request works
- [ ] HTTPS request works
- [ ] Timing breakdown correct
- [ ] Certificate extraction works
- [ ] CLI mode works
- [ ] GUI panel works

### Interface Viewer
- [ ] Interface listing works on all platforms
- [ ] IP/MAC/MTU display correct
- [ ] Gateway detection works
- [ ] DNS detection works
- [ ] CLI mode works
- [ ] GUI panel works

### Self-Tests
- [ ] All parser tests pass
- [ ] `--self-test` flag works
- [ ] Exit codes correct

---

## Performance Metrics

### Target Goals
- [ ] WiFi table updates: <50ms per scan (vs ~200ms full rebuild)
- [ ] No visible flicker during updates
- [ ] Selection preserved during updates
- [ ] Scroll position maintained
- [ ] <100ms startup time (GUI)
- [ ] <50ms CLI command execution (non-network operations)

### Measurements
- Baseline (wa.py): Table rebuild time: ~200ms, flicker: yes
- Target (network_suite.py): Table update time: <50ms, flicker: no
- *Will measure after implementation*

---

## Code Quality Metrics

- [ ] All functions have docstrings
- [ ] All security fixes preserved from wa.py
- [ ] No shell=True anywhere
- [ ] No passwords in logs
- [ ] All user input validated
- [ ] All OS commands use list format
- [ ] Cross-platform compatibility maintained
- [ ] Graceful degradation for optional deps

---

## File Size Tracking

- Original wa.py: 2,127 lines
- Target network_suite.py: ~4,000-5,000 lines
- Actual: *TBD*

---

## Notes & Decisions

**2026-03-02**: Started implementation
- Chose focused subset approach: WiFi + 5 core tools
- Deferred LAN discovery, ARP viewer, routing table to future enhancement
- Full incremental table system included
- Equal GUI/CLI support for all implemented tools
- Self-test framework for all parsers

**Architecture Decisions**:
- Single file with clear section markers
- Plugin registry for extensibility
- BSSID-keyed row tracking for performance
- QSettings for persistence
- Feature flags for optional dependencies
- Cross-platform command abstraction

---

## Legend
- [ ] Not started
- [⚙] In progress
- [✅] Completed
- [⏸] Blocked/Deferred
- [❌] Failed/Skipped
