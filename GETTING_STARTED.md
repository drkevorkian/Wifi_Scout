# Network Scout v2.2.9 - Installation & Usage

## 🚀 Quick Start

### Installation
```bash
# Clone or download this repository
cd Wifi_Scout

# Install with all features
pip install -e ".[full]"

# Or minimal install (GUI + core only)
pip install -e .

# Or use the legacy installer script
./install.sh      # Linux/macOS
install.bat       # Windows
```

### Launch
```bash
# GUI Mode (default)
python network_suite.py

# CLI Mode (add any command)
python network_suite.py --help
```

---

## 📦 What's Included

### Core System
- **network_suite.py** - Main application (1,197 lines)
- **core/wifi_engine.py** - WiFi scanning & connection logic
- **core/utilities.py** - Shared utility functions

### 9 Diagnostic Tools (Mods)
All tools have both GUI and CLI interfaces:

1. **WiFi Scanner** (built-in) - Scan, score, connect to networks
2. **DNS Lookup** - Query A/AAAA/CNAME/MX/TXT/NS records
3. **Ping** - ICMP testing with packet loss statistics
4. **Traceroute** - Hop-by-hop route analysis
5. **HTTP Checker** - Test endpoints with timing breakdown
6. **Network Interfaces** - View all interfaces with config
7. **ARP Table** - Display IP-to-MAC mappings
8. **Routing Table** - Show system routing table
9. **LAN Scanner** - Safe local network discovery

---

## 🎯 Features

### WiFi Management
- ✅ Cross-platform scanning (Windows/Linux/macOS)
- ✅ Intelligent network scoring algorithm
- ✅ One-click connection
- ✅ Signal strength history charts
- ✅ Auto-refresh scanning

### Network Diagnostics
- ✅ DNS resolution with latency
- ✅ Ping with statistics (loss %, RTT)
- ✅ Traceroute with hop details
- ✅ HTTP/HTTPS with SSL certificate info
- ✅ Complete interface configuration
- ✅ ARP cache display
- ✅ Routing table inspection
- ✅ Safe LAN scanning (RFC1918 only)

### User Experience
- ✅ Modern GUI with dark/light themes
- ✅ Powerful CLI for automation
- ✅ Background threading (non-blocking)
- ✅ Real-time status updates
- ✅ Settings persistence
- ✅ Export to JSON/CSV/HTML
- ✅ Comprehensive logging

---

## 💻 CLI Reference

### WiFi Commands
```bash
# Scan networks
python network_suite.py wifi scan --sort score

# Find best network
python network_suite.py wifi best

# Connect to network
python network_suite.py wifi connect "NetworkName" --password "pass"
```

### DNS Commands
```bash
# Query multiple record types
python network_suite.py dns-lookup example.com --types A AAAA MX

# JSON output
python network_suite.py dns-lookup google.com --format json
```

### Connectivity Commands
```bash
# Ping test
python network_suite.py ping 8.8.8.8 --count 10

# Traceroute
python network_suite.py traceroute google.com --max-hops 20

# HTTP test
python network_suite.py http-checker https://example.com --method GET
```

### System Information
```bash
# Network interfaces
python network_suite.py network-interfaces

# ARP table
python network_suite.py arp-table

# Routing table
python network_suite.py routing-table
```

### LAN Scanner
```bash
# Scan local network (requires confirmation)
python network_suite.py lan-scanner 192.168.1.0/24

# Skip confirmation (use with caution)
python network_suite.py lan-scanner 10.0.0.0/24 --confirm
```

---

## 🔧 Dependencies

### Required
- Python 3.10+

### Optional (with graceful fallback)
- **PyQt6** - For GUI mode (CLI works without it)
- **matplotlib** - For signal history charts
- **dnspython** - Better DNS resolution (falls back to system commands)
- **psutil** - Better interface detection (falls back to system commands)

### Install All Optional (Full Feature Set)
```bash
# Install with all optional dependencies
pip install -e ".[full]"

# Or install individually
pip install PyQt6 matplotlib dnspython psutil
```

---

## 🏗️ Architecture

### Plugin System
The Network Suite uses a modular plugin architecture:

```
network_suite.py (Core)
    ↓ loads
mods/ (Plugins)
    ├── dns_tool.py
    ├── ping_tool.py
    ├── traceroute_tool.py
    └── ... (any new mods)
```

**Key Benefits:**
- Add new tools without modifying core
- Each mod is self-contained
- Automatic discovery and loading
- Consistent API across all mods

### Creating Custom Mods

1. Copy `mods/example_tool.py`
2. Implement your tool logic
3. Drop it in `mods/` directory
4. Restart Network Suite - it auto-loads!

See `mods/example_tool.py` for complete template with documentation.

---

## 🔒 Security Features

- ✅ **No shell=True** - All commands use safe list format
- ✅ **Input validation** - SSID, password, network ranges validated
- ✅ **Private networks only** - LAN scanner restricted to RFC1918
- ✅ **Rate limiting** - Connection and scan rate limits
- ✅ **Secure file handling** - Temporary files securely deleted
- ✅ **No secrets in logs** - Passwords never logged
- ✅ **Injection prevention** - XML/HTML escaping
- ✅ **User confirmation** - For potentially disruptive operations

---

## 📊 Platform Support

### Windows
- ✅ WiFi: `netsh wlan`
- ✅ Network commands: `ping`, `tracert`, `route`, `arp`, `ipconfig`
- ✅ All features tested on Windows 10/11

### Linux
- ✅ WiFi: `nmcli` or `iwconfig`
- ✅ Network commands: `ping`, `traceroute`, `ip`, `arp`
- ✅ Compatible with major distributions

### macOS
- ✅ WiFi: `airport` utility
- ✅ Network commands: `ping`, `traceroute`, `route`, `arp`, `ifconfig`
- ✅ macOS 10.14+ compatible

---

## 🎨 GUI Features

### Tabs
1. **WiFi** - Network scanning and management
2. **Details** - Selected network information
3. **History** - Signal strength charts (matplotlib)
4. **Mods** - 9 diagnostic tool tabs
5. **Logs** - Application log viewer

### Controls
- **Dark/Light Theme** - Menu → View → Toggle Theme
- **Auto-Scan** - Checkbox for periodic WiFi scans
- **Export** - Save results to JSON/CSV/HTML
- **Settings** - Persists window size, theme, preferences

---

## 📁 File Structure

```
wifi_scout/
├── network_suite.py          # Main application
├── core/
│   ├── wifi_engine.py        # WiFi functionality
│   └── utilities.py          # Shared utilities
├── mods/
│   ├── __init__.py
│   ├── example_tool.py       # Template
│   ├── dns_tool.py
│   ├── ping_tool.py
│   ├── traceroute_tool.py
│   ├── http_tool.py
│   ├── interfaces_tool.py
│   ├── arp_tool.py
│   ├── route_tool.py
│   └── lan_scan_tool.py
├── docs/                     # Documentation
├── requirements.txt
├── install.bat / install.sh
├── run_wifi_scout.bat / .sh
├── README.md                 # Original guide
├── TESTING_GUIDE.md          # Testing instructions
├── PROJECT_COMPLETE.md       # Project summary
└── wa.py                     # Original WiFi Scout (preserved)
```

---

## 🐛 Troubleshooting

### WiFi Scan Fails
**Windows:**
- Enable WiFi adapter
- Run as Administrator
- Start "WLAN AutoConfig" service (services.msc)

**Linux:**
- Install `nmcli`: `sudo apt install network-manager`
- Or `iwconfig`: `sudo apt install wireless-tools`

**macOS:**
- WiFi should work out of the box
- Ensure WiFi is enabled in System Preferences

### GUI Won't Start
```bash
# Install PyQt6
pip install PyQt6

# Or use CLI mode
python network_suite.py --help
```

### Commands Not Found
- **Windows**: Should have all commands built-in
- **Linux**: `sudo apt install iputils-ping traceroute net-tools`
- **macOS**: Should have all commands built-in

### Performance Issues
- Disable auto-scan if CPU usage high
- Reduce scan interval
- Close unused tabs

---

## 📝 Logs

Application logs are saved to:
- **Windows**: `C:\Users\{username}\.network_suite\`
- **Linux/Mac**: `~/.network_suite/`

Log files include:
- Scan results
- Error messages
- Tool execution details
- Debug information

View logs in GUI: **Logs Tab** or copy path from status bar

---

## 🎓 Usage Examples

### Example 1: Quick Network Check
```bash
# Scan WiFi, check DNS, ping gateway
python network_suite.py wifi scan
python network_suite.py dns-lookup google.com
python network_suite.py ping 192.168.1.1
```

### Example 2: Troubleshoot Connection
```bash
# Check route to external host
python network_suite.py traceroute 8.8.8.8

# Test HTTP connectivity
python network_suite.py http-checker https://google.com

# View local network config
python network_suite.py network-interfaces
```

### Example 3: Discover LAN Devices
```bash
# View ARP cache
python network_suite.py arp-table

# Scan local network
python network_suite.py lan-scanner 192.168.1.0/24
```

### Example 4: Automation with JSON
```bash
# Get structured data for scripts
python network_suite.py wifi scan --format json > wifi_scan.json
python network_suite.py network-interfaces --format json > interfaces.json
```

---

## 🆘 Support

### Documentation
- `README.md` - Complete user guide (374 lines)
- `TESTING_GUIDE.md` - Feature testing instructions
- `PROJECT_COMPLETE.md` - Project overview
- `docs/QUICK_REFERENCE.md` - Quick reference
- Code comments and docstrings

### Common Issues
Check the log file for detailed error messages:
```bash
# Windows
type %USERPROFILE%\.network_suite\network_suite_*.log

# Linux/Mac
cat ~/.network_suite/network_suite_*.log
```

---

## 📊 Stats

- **Total Code**: ~6,111 lines
- **Python Files**: 13
- **Tools**: 9 (WiFi + 8 diagnostic mods)
- **Platforms**: 3 (Windows, Linux, macOS)
- **Interfaces**: 2 (GUI + CLI)
- **Documentation**: 14+ markdown files

---

## 🎉 What's New in v2.2.9

**Complete architectural rewrite with modular design:**

✅ Plugin system for easy extension  
✅ 8 new network diagnostic tools  
✅ Full CLI interface added  
✅ Cross-platform improvements  
✅ Enhanced security features  
✅ Better performance (incremental updates)  
✅ Modern UI with themes  
✅ Settings persistence  
✅ Comprehensive documentation

**vs v2.0 (wa.py - legacy):**
- 3x code size
- 9x more tools
- Modular vs monolithic
- GUI + CLI vs GUI only
- Plugin architecture vs single file

---

## 📄 License

See LICENSE file for details.

---

## 🙏 Credits

**Built with:**
- Python 3.10+
- PyQt6 (GUI framework)
- Matplotlib (charts)
- Standard library networking modules

**Architecture:**
- Modular plugin system
- Dataclass-based models
- Background threading
- Cross-platform command abstraction

---

**Network Scout v2.2.9** - Professional network diagnostics made easy.

For more information, see `PROJECT_COMPLETE.md` and `TESTING_GUIDE.md`.
