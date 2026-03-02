# 📁 Network Suite - Directory Structure

**Version**: 2.2.9  
**Last Updated**: 2026-03-02

---

## 📂 Root Directory Structure

```
wifi_scout/
├── 📄 network_suite.py          # Main application (GUI + CLI)
├── 📄 README.md                 # Main documentation
├── 📄 GETTING_STARTED.md        # Installation & usage guide
├── 📄 requirements.txt          # Python dependencies
│
├── 🔧 install.bat              # Windows installer
├── 🔧 install.sh               # Linux/macOS installer
├── 🚀 run_wifi_scout.bat       # Windows launcher
├── 🚀 run_wifi_scout.sh        # Linux/macOS launcher
│
├── 📁 core/                    # Core WiFi engine
│   ├── wifi_engine.py          # WiFi scanning & connection
│   └── utilities.py            # Shared utilities
│
├── 📁 mods/                    # Modular diagnostic tools
│   ├── __init__.py
│   ├── example_tool.py         # Template for new mods
│   ├── dns_tool.py             # DNS lookup
│   ├── ping_tool.py            # ICMP ping test
│   ├── traceroute_tool.py      # Route tracing
│   ├── http_tool.py            # HTTP/HTTPS testing
│   ├── interfaces_tool.py      # Network interfaces viewer
│   ├── arp_tool.py             # ARP table viewer
│   ├── route_tool.py           # Routing table viewer
│   └── lan_scan_tool.py        # LAN scanner
│
├── 📁 docs/                    # Documentation
│   ├── AUDIT_REPORT.md         # Security audit (25 issues)
│   ├── CRITICAL_FIXES.md       # Critical fix guide
│   ├── CRITICAL_CRASH_FIX.md   # Thread crash fix
│   ├── FIXES_APPLIED.md        # Quick fix reference
│   ├── CHANGELOG_v3.0.1.md     # Version 3.0.1 changes
│   ├── TESTING_GUIDE.md        # Testing procedures
│   ├── LAN_SCANNER_TEST_GUIDE.md # LAN scanner testing
│   ├── SECURITY_REFERENCE.md   # Security features
│   ├── QUICK_REFERENCE.md      # Quick reference card
│   ├── SECURITY_FIXES.md       # Security fix details
│   ├── SECURITY_AUDIT_REPORT.md # Full audit report
│   ├── CHANGELOG.md            # Version history
│   ├── CLEANUP_SUMMARY.md      # Cleanup notes
│   ├── PROJECT_COMPLETE.md     # Project completion summary
│   ├── PROJECT_STRUCTURE.txt   # Old structure file
│   ├── MODULAR_ARCHITECTURE.md # Architecture plan
│   ├── IMPLEMENTATION_LOG.md   # Implementation progress
│   ├── PROMPT1_COMPLETE.md     # Phase 1 completion
│   ├── PROMPT2_COMPLETE.md     # Phase 2 completion
│   ├── PROMPT3_COMPLETE.md     # Phase 3 completion
│   └── PROMPT4_COMPLETE.md     # Phase 4 completion
│
├── 📁 archive/                 # Archived old files
│   ├── wa.py                   # Original monolithic version
│   ├── test_wa.py              # Old tests
│   └── test_security.py        # Old security tests
│
└── 📁 venv/                    # Python virtual environment (git ignored)
```

---

## 📋 File Descriptions

### Main Files

| File | Purpose |
|------|---------|
| `network_suite.py` | Main application entry point (1,216 lines) |
| `README.md` | Primary documentation with features, installation, usage |
| `GETTING_STARTED.md` | Comprehensive getting started guide |
| `requirements.txt` | Python package dependencies |

### Installers & Launchers

| File | Platform | Purpose |
|------|----------|---------|
| `install.bat` | Windows | Creates venv, installs dependencies |
| `install.sh` | Linux/macOS | Creates venv, installs dependencies |
| `run_wifi_scout.bat` | Windows | Activates venv and runs app |
| `run_wifi_scout.sh` | Linux/macOS | Activates venv and runs app |

### Core Modules

| File | Lines | Purpose |
|------|-------|---------|
| `core/wifi_engine.py` | 748 | WiFi scanning, scoring, connection logic |
| `core/utilities.py` | 202 | Shared utilities, validation, security |

### Diagnostic Mods

| File | Lines | Category | Features |
|------|-------|----------|----------|
| `mods/example_tool.py` | ~200 | Template | Mod template for developers |
| `mods/dns_tool.py` | 427 | Network | DNS A/AAAA/CNAME/MX/TXT/NS queries |
| `mods/ping_tool.py` | 427 | Network | ICMP echo test with statistics |
| `mods/traceroute_tool.py` | 510 | Network | Route tracing with hop details |
| `mods/http_tool.py` | 475 | Network | HTTP/HTTPS testing with timing |
| `mods/interfaces_tool.py` | 550 | System | Network interface information |
| `mods/arp_tool.py` | 400 | System | ARP table viewer |
| `mods/route_tool.py` | 427 | System | Routing table viewer |
| `mods/lan_scan_tool.py` | 497 | Network | Safe LAN discovery (RFC1918) |

### Documentation

| File | Purpose |
|------|---------|
| `docs/AUDIT_REPORT.md` | Complete security & bug audit (25 issues) |
| `docs/CRITICAL_FIXES.md` | Implementation guide for critical fixes |
| `docs/CRITICAL_CRASH_FIX.md` | Thread garbage collection fix |
| `docs/FIXES_APPLIED.md` | Quick reference for applied fixes |
| `docs/CHANGELOG_v3.0.1.md` | Detailed v3.0.1 changelog |
| `docs/TESTING_GUIDE.md` | Comprehensive testing procedures |
| `docs/LAN_SCANNER_TEST_GUIDE.md` | LAN scanner specific tests |

### Archive

| File | Purpose | Lines |
|------|---------|-------|
| `archive/wa.py` | Original WiFi Scout Pro (monolithic) | 2,127 |
| `archive/test_wa.py` | Old unit tests | 186 |
| `archive/test_security.py` | Old security tests | 237 |

---

## 🎯 Key Directories

### `/core/` - WiFi Engine
Core functionality extracted from original `wa.py`:
- Cross-platform WiFi scanning (Windows, Linux, macOS)
- Network scoring algorithm
- Secure connection management
- Shared utilities and validation

### `/mods/` - Modular Tools
Pluggable diagnostic tools with consistent structure:
- Each mod is self-contained
- Automatic discovery and loading
- GUI and CLI integration
- Independent testing

### `/docs/` - Documentation
All project documentation organized by type:
- Security audits and fixes
- Testing guides
- Implementation logs
- Version changelogs

### `/archive/` - Legacy Code
Original files kept for reference:
- Original monolithic version
- Legacy test files
- Historical code

---

## 📊 Statistics

### Codebase Size
- **Total Lines**: ~6,800 (excluding tests & docs)
- **Core System**: 1,216 lines (network_suite.py)
- **WiFi Engine**: 950 lines (core/)
- **Mods**: 4,200+ lines (9 mods)

### File Counts
- **Python Files**: 13 (1 main + 2 core + 10 mods)
- **Documentation**: 20+ markdown files
- **Scripts**: 4 (2 installers + 2 launchers)

### Documentation Size
- **Total Documentation**: 100,000+ words
- **Code Comments**: Extensive inline documentation
- **API Documentation**: All public functions documented

---

## 🚀 Quick Start Paths

### For Users
1. **Start Here**: `README.md`
2. **Install**: `install.bat` or `install.sh`
3. **Run**: `run_wifi_scout.bat` or `run_wifi_scout.sh`
4. **Learn**: `GETTING_STARTED.md`

### For Developers
1. **Architecture**: `docs/MODULAR_ARCHITECTURE.md`
2. **Create Mod**: `mods/example_tool.py` (template)
3. **Security**: `docs/AUDIT_REPORT.md`
4. **Testing**: `docs/TESTING_GUIDE.md`

### For Troubleshooting
1. **Logs**: `~/.network_suite/network_suite_*.log`
2. **Test Guide**: `docs/TESTING_GUIDE.md`
3. **Known Issues**: `docs/AUDIT_REPORT.md`
4. **Fixes Applied**: `docs/FIXES_APPLIED.md`

---

## 🔄 Version History

| Version | Date | Description |
|---------|------|-------------|
| 3.0.2 | 2026-03-02 | Critical crash fix (thread GC) |
| 3.0.1 | 2026-03-01 | Security fixes |
| 3.0.0 | 2026-03-01 | Modular architecture |
| 2.3 | Earlier | WiFi Scout Pro (monolithic) |

---

## 📝 Notes

### Git Ignore
The following should be ignored:
- `venv/` - Virtual environment
- `__pycache__/` - Python bytecode
- `*.pyc` - Compiled Python files
- `*.log` - Log files
- `.pytest_cache/` - Test cache

### Data Directories
User data stored in:
- **Windows**: `C:\Users\<user>\.network_suite\`
- **Linux/macOS**: `~/.network_suite/`

Contains:
- Log files: `network_suite_YYYYMMDD_HHMMSS.log`
- CLI logs: `cli.log`
- Settings: Stored via QSettings (registry on Windows, config files on Unix)

---

**Clean, Organized, Production-Ready** ✅

*Last Updated: 2026-03-02*
