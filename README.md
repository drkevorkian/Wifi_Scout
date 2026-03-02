# 📡 Network Scout v2.2.9

**A secure, cross-platform network diagnostic suite with modular architecture**

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Security](https://img.shields.io/badge/security-audited-brightgreen)

---

## ✨ Features

### Core WiFi Features
- 🔍 **Cross-Platform WiFi Scanning** - Works on Windows, Linux, and macOS
- 📊 **Smart Network Scoring** - Intelligent recommendation algorithm
- 📈 **Signal History Tracking** - Real-time signal strength graphs with matplotlib
- 🔐 **Secure Connections** - Connect to networks with secure password handling
- 📱 **Modern GUI** - Clean, responsive PyQt6 interface with dark/light themes
- 📤 **Export Options** - CSV, JSON, and HTML reports

### Modular Diagnostic Tools
- 🌐 **DNS Lookup** - Query A, AAAA, CNAME, MX, TXT, NS records with latency
- 📡 **Ping Tool** - ICMP echo test with statistics (min/max/avg, packet loss)
- 🛣️ **Traceroute** - Network route tracing with hop-by-hop details
- 🌍 **HTTP Checker** - HTTP/HTTPS testing with timing breakdown* and certificates
- 💻 **Network Interfaces** - View all interfaces with IP/MAC/MTU/status
- 🔗 **ARP Table** - Display ARP cache with IP-to-MAC mappings
- 🗺️ **Routing Table** - View system routing table with metrics
- 🔍 **LAN Scanner** - Safe local network discovery (RFC1918 only)

*Note: HTTP timing breakdown is approximate - see [Known Limitations](#-known-limitations)

### Advanced WiFi Features
- ⚡ **Auto-Refresh** - Continuous network monitoring with configurable intervals
- 🎯 **Best Network Finder** - Automatic recommendation engine with scoring breakdown
- 🔒 **Security Analysis** - Detailed security assessment per network (WPA3/WPA2/WPA/WEP/OPEN)
- 📉 **RF Metrics** - Signal, noise, SNR, channel analysis with congestion detection
- 🔄 **Network History** - Track signal strength over time with persistent storage
- 🎨 **Customizable Interface** - Persistent settings, window geometry, themes

---

## 🚀 Quick Start

### Installation

**Recommended: Modern Install with pip**
```bash
# Install with all features (recommended)
pip install -e ".[full]"

# Or install minimal (CLI only, no GUI)
pip install -e .

# Or install specific feature sets
pip install -e ".[gui]"      # GUI support only
pip install -e ".[network]"  # Enhanced network tools only
```

**Legacy: Manual Install**

#### Windows
```batch
# Run the installer (creates venv, installs dependencies)
install.bat

# Or manually:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

#### Linux / macOS
```bash
# Run the installer
chmod +x install.sh
./install.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running the Application

**Using Console Commands (After pip install)**
```bash
# Main command
network-scout              # Launch GUI
network-scout --help       # Show CLI help
network-scout wifi scan    # Scan WiFi networks

# Alternative commands
wifi-scout --version       # Same as network-scout
ns wifi best              # Short alias
```

**Using Python directly**

#### Windows
```batch
# Use the launcher
run_wifi_scout.bat

# Or manually:
venv\Scripts\activate
python network_suite.py
```

#### Linux / macOS
```bash
# Use the launcher
./run_wifi_scout.sh

# Or manually:
source venv/bin/activate
python network_suite.py
```

---

## 📋 Requirements

### System Requirements
- **Python**: 3.10 or higher
- **OS**: Windows 10+, Linux (with NetworkManager), macOS 10.14+
- **Admin/Root**: Required for Wi-Fi operations on some systems

### Python Dependencies
- `PyQt6` - GUI framework
- `matplotlib` - Signal history charts (optional but recommended)

All dependencies are listed in `requirements.txt` and installed automatically by the installers.

---

## 🎯 Usage Guide

### Basic Workflow
1. **Scan** - Click "Scan Now" to discover networks
2. **Analyze** - View signal strength, security, and recommendations
3. **Connect** - Select a network and click "Connect"
4. **Export** - Save results to CSV, JSON, or HTML

### Key Features Explained

#### Network Scoring
The app uses a sophisticated algorithm to score networks based on:
- **Security** (WPA3 > WPA2 > WPA > WEP > OPEN)
- **Signal Strength** (-50 dBm = excellent, -75 dBm = weak)
- **Band** (5GHz/6GHz preferred for speed, 2.4GHz for range)
- **Channel Congestion** (fewer networks = better)
- **Channel Optimization** (1, 6, 11 are optimal for 2.4GHz)
- **SNR (Signal-to-Noise Ratio)** (higher = better)

#### Auto-Refresh
Enable "Auto-refresh" to continuously monitor networks:
- Updates every 5-300 seconds (configurable)
- Builds signal history for graphing
- Tracks connection status changes

#### Filters
- **Search** - Filter by SSID or BSSID
- **Band** - Show only 2.4GHz, 5GHz, or 6GHz networks
- **Hide OPEN** - Exclude unsecured networks
- **Allow OPEN in scoring** - Consider open networks in recommendations

---

## 🔐 Security

### Version 2.2.9 Security Features
✅ **Comprehensive Security Implementation**
- Thread garbage collection bug fixed (all mods)
- Windows password file permission race condition fixed
- Duplicate type definitions eliminated
- Input validation hardened across all components
- Settings validation with range checking

#### Password Security
- **Never stored** - Passwords are transient only
- **Never logged** - No password disclosure in logs
- **Secure temp files** - Created with restricted permissions (0o600) from the start
- **Secure deletion** - Files overwritten with random data before removal
- **Rate limiting** - 5-second cooldown prevents connection spam

⚠️ **Known Limitation on Linux/macOS**
When connecting to WiFi networks on Linux and macOS, the password is passed as a 
command-line argument to system utilities (`nmcli`, `networksetup`) and may be 
briefly visible in the process list. This is a limitation of the underlying system 
commands and affects all similar tools on these platforms.

**Mitigation**: The password is only visible during the connection attempt (typically 
< 1 second) and is not logged to files.

**Recommendation**: Only use on trusted systems where you control access. For 
production environments, consider using OS-native credential managers.

#### Injection Prevention
- **XML injection** - All user input escaped
- **XSS prevention** - HTML reports sanitized
- **Command injection** - Prevented via safe subprocess calls

#### Data Protection
- **Input validation** - SSID and password requirements enforced
- **Secure file operations** - Restrictive permissions, atomic creation
- **No information disclosure** - Error messages don't leak paths

For detailed security information, see:
- `docs/SECURITY_FIXES.md` - Technical vulnerability details
- `docs/SECURITY_AUDIT_REPORT.md` - Executive security summary
- `SECURITY_REFERENCE.md` - Quick security reference

---

## 🧪 Testing

### Run Test Suite
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test file
pytest tests/test_plugin_loader.py -v
```

### Test Categories
- **test_plugin_loader.py** - Plugin architecture tests
- **test_cli.py** - Command-line interface tests  
- **test_wifi_engine.py** - Core WiFi functionality tests
- **test_integration.py** - End-to-end integration tests

---

## 📁 Project Structure

```
Wifi_Scout/
├── network_suite.py            # Main application
├── pyproject.toml              # Modern Python packaging config
├── requirements.txt            # Legacy dependency list
├── README.md                   # This file
├── GETTING_STARTED.md          # Detailed installation guide
├── CHANGELOG.md                # Version history
├── SECURITY_REFERENCE.md       # Security quick reference
├── install.bat/sh              # Legacy installation scripts
├── run_wifi_scout.bat/sh       # Legacy launch scripts
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI/CD
├── tests/                      # Test suite
│   ├── test_plugin_loader.py  # Plugin system tests
│   ├── test_cli.py             # CLI tests
│   ├── test_wifi_engine.py    # Core functionality tests
│   └── test_integration.py    # Integration tests
├── core/                       # Core modules
│   ├── wifi_engine.py          # WiFi scanning & connection
│   └── utilities.py            # Shared utilities
├── mods/                       # Diagnostic tool plugins
│   ├── dns_tool.py
│   ├── ping_tool.py
│   ├── traceroute_tool.py
│   ├── http_tool.py
│   ├── interfaces_tool.py
│   ├── arp_tool.py
│   ├── route_tool.py
│   └── lan_scan_tool.py
├── docs/                       # Documentation
│   ├── QUICKSTART.md
│   ├── QUICK_REFERENCE.md
│   ├── SECURITY_FIXES.md
│   └── SECURITY_AUDIT_REPORT.md
└── venv/                       # Virtual environment (created by installer)
```

---

## 🎨 Screenshots

### Main Scanner Tab
- Network table with sortable columns
- Real-time signal strength indicators
- Color-coded security levels
- Selected network dashboard cards

### Details Tab
- Comprehensive network information
- Quality assessment with scoring breakdown
- Connection management
- Security recommendations

### Signal History Tab
- Interactive matplotlib charts
- Multi-network comparison
- Time-series signal tracking
- Automatic updates during auto-scan

### Logs Tab
- Real-time application logs
- Filter by log level
- Copy log path
- Open log folder

---

## 🌐 Platform-Specific Notes

### Windows
- Uses `netsh` for scanning and connections
- **Best security** - no argv password exposure
- May require Administrator for some operations
- Supports all features

### Linux
- Uses `nmcli` (NetworkManager)
- Requires NetworkManager running
- Password visible in `ps aux` (OS limitation)
- Install: `sudo apt install network-manager`

### macOS
- Uses `airport` and `networksetup`
- Dynamically detects Wi-Fi interface
- Password visible in `ps aux` (OS limitation)
- SIP restrictions may limit some features

---

## 🔧 Troubleshooting

### "No Wi-Fi networks found"
- **Windows**: Enable Wi-Fi adapter, start WLAN AutoConfig service
- **Linux**: Ensure NetworkManager is running: `sudo systemctl start NetworkManager`
- **macOS**: Enable Wi-Fi in System Preferences
- Run as Administrator/root if needed

### "Connection failed"
- Verify correct password
- Check network is in range
- Ensure no VPN or firewall blocking
- Wait 5 seconds between connection attempts (rate limiting)

### "matplotlib not available"
- Charts disabled but app works fine
- Install with: `pip install matplotlib`
- Or re-run `install.bat/sh`

### Permission Errors
- **Windows**: Run as Administrator (right-click → Run as administrator)
- **Linux**: Use `sudo` or add user to `netdev` group
- **macOS**: Grant Terminal full disk access in Security & Privacy

---

## 📚 Documentation

- **README.md** (this file) - Overview and quick start
- **CHANGELOG.md** - Version history and changes
- **SECURITY_REFERENCE.md** - Security features and best practices
- **docs/QUICKSTART.md** - Detailed usage guide with examples
- **docs/QUICK_REFERENCE.md** - Command and feature reference
- **docs/SECURITY_FIXES.md** - Technical security vulnerability details
- **docs/SECURITY_AUDIT_REPORT.md** - Security audit executive summary

---

## ⚠️ Known Limitations

### HTTP Timing Methodology
The HTTP Checker tool's timing breakdown (DNS/connect/TLS) is measured on a preliminary connection that is then closed. The actual HTTP request is performed via a separate connection.

**What this means**:
- Timing values are **approximations**, not exact measurements
- Useful for identifying slow DNS, TLS handshake issues, and relative performance
- For precise end-to-end timing, use external tools like `curl --write-out` or dedicated HTTP benchmarking tools

**Why**: This approach allows the tool to measure individual phases while still handling the full HTTP request/response cycle properly.

---

## 🤝 Contributing

### Code Guidelines
- Follow existing code style
- Add security comments for critical sections
- Update tests for new features
- Run `test_security.py` before committing
- Never commit real passwords in test data

### Security
- Mark critical code with `SECURITY` comments
- Validate all user input
- Use provided escape functions (xml_escape, html_escape)
- Never log sensitive data
- Always cleanup temp files in `finally` blocks

---

## 📜 License

MIT License - See LICENSE file for details.

---

## 🙏 Acknowledgments

Built with:
- **PyQt6** - Modern GUI framework
- **matplotlib** - Data visualization
- **Python** - The language that powers it all

Inspired by the need for a secure, user-friendly, cross-platform Wi-Fi management tool.

---

## 📞 Support

### Getting Help
1. Check the documentation in `docs/`
2. Run tests to verify installation
3. Review logs at `~/.network_suite/`
4. Check GitHub issues (if applicable)

### Security Issues
For security concerns:
1. Review `SECURITY_REFERENCE.md`
2. Run `test_security.py` to verify fixes
3. Check `docs/SECURITY_FIXES.md` for known issues
4. Report responsibly with reproduction steps

---

## 🗺️ Roadmap

### Future Enhancements
- [ ] Native API support (D-Bus for Linux, CoreWLAN for macOS)
- [ ] OS credential storage integration
- [ ] WPA3-Enterprise support
- [ ] Network speed testing
- [ ] QR code generation for sharing networks
- [ ] Export/import network profiles

---

## 📊 Project Stats

- **Version**: 2.2.9
- **Release Date**: 2026-03-02
- **Lines of Code**: ~6,800
- **Test Coverage**: Core modules with unit tests
- **Platforms**: Windows, Linux, macOS
- **Security Audits**: 1 (all issues resolved)
- **CI/CD**: GitHub Actions (Win/Linux/macOS matrix)
- **Package Format**: Modern pyproject.toml with extras

---

## 🔄 CI/CD Status

![CI Status](https://github.com/yourusername/Wifi_Scout/actions/workflows/ci.yml/badge.svg)

Automated testing on every push:
- ✅ Lint checks (flake8, black)
- ✅ Unit tests on Python 3.10, 3.11, 3.12
- ✅ Platform tests on Windows, Linux, macOS
- ✅ Security scans (bandit, safety)
- ✅ Build and distribution tests
- ✅ Installation verification

---

**Made with ❤️ and a focus on security**

*Last Updated: 2026-03-02 - Network Scout v2.2.9*
