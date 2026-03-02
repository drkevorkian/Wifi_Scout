# Wi-Fi Scout Pro - Changelog

## [2.3] - 2026-03-02

### 🔐 CRITICAL SECURITY FIXES
- **Fixed password exposure in plaintext XML files**
  - Passwords now securely deleted using random data overwrite
  - Unique temp files with UUID prevent race conditions
  - Restrictive file permissions (0o600) on Windows
  - Cleanup guaranteed via `finally` blocks
  
- **Fixed password exposure in exception logs**
  - Removed `logger.exception()` calls that could leak passwords
  - Generic error messages prevent information disclosure
  
- **Fixed XML injection vulnerability**
  - All SSIDs and passwords now XML-escaped
  - Prevents malicious SSID injection attacks

### 🛡️ HIGH SEVERITY FIXES
- **Improved temporary file security**
  - Changed from silent `try/except` to guaranteed `finally` cleanup
  - Added secure deletion function with overwrite
  
### 🐛 MEDIUM SEVERITY FIXES
- **Fixed macOS interface detection**
  - Dynamically detects Wi-Fi interface (was hardcoded to "en0")
  - Works on Macs with en1, en2, etc.
  
- **Fixed UI thread blocking**
  - Replaced `time.sleep(2)` with `QTimer.singleShot()`
  - UI remains responsive after connection attempts
  
- **Added comprehensive input validation**
  - SSID validation: length (32 bytes max), control characters
  - Password validation: WPA/WPA2/WPA3 requirements (8-63 chars)
  
- **Fixed race condition in temp file creation**
  - Using `tempfile.mkstemp()` for atomic creation
  - UUID-based unique filenames

### 📋 LOW SEVERITY FIXES
- **Reduced information disclosure**
  - Removed log file paths from error dialogs
  - More secure error messages
  
- **Added rate limiting for connections**
  - 5-second cooldown between connection attempts
  - Prevents Wi-Fi adapter lockouts
  
- **Added ANSI escape protection**
  - Log sanitization function for control characters
  - Prevents terminal escape sequence injection
  
- **Improved command validation**
  - `run_cmd()` validates non-empty arguments
  - Better error messages

### 🎨 UI IMPROVEMENTS
- Fixed table column widths (text now fully visible)
- Light mode is now the default theme
- Improved metric card contrast in both themes

### 📚 DOCUMENTATION
- New `SECURITY_FIXES.md` with detailed vulnerability analysis
- Code comments marked with `SECURITY` for critical sections
- Enhanced inline documentation

---

## [2.2] - 2026-03-01

### Features
- Enhanced UI with tabbed interface
- Score breakdown transparency
- Signal history tracking with matplotlib charts
- Better RF metrics and enrichment
- HTML report export with styling
- Auto-refresh scanning

### Bug Fixes
- Fixed HTML export f-string formatting
- Fixed connected BSSID parsing on Windows
- Fixed strongest-network selection with null values
- Fixed CSV export column mismatch
- Fixed matplotlib backend compatibility with PyQt6

---

## [2.1] - 2026-02-28

### Features
- Initial cross-platform Wi-Fi scanner
- Windows (netsh), Linux (nmcli), macOS (airport) support
- Basic scoring algorithm
- CSV/JSON export

---

## Security Advisories

### Critical (Fixed in 2.3)
- **CVE-NONE-001**: Password exposure in plaintext temp files
- **CVE-NONE-002**: XML injection via malicious SSID
- **CVE-NONE-003**: Password leakage in exception logs

All critical vulnerabilities have been resolved. See `SECURITY_FIXES.md` for details.

---

## Upgrade Guide

### From 2.2 to 2.3
- **Breaking Changes**: None
- **New Behavior**: 
  - 5-second rate limit on connection attempts
  - macOS will auto-detect Wi-Fi interface
- **Action Required**: None - upgrade is seamless

### From 2.1 to 2.2
- Improved UI may require screen resize
- New dependencies: matplotlib (optional)

---

## Contributing

When contributing security fixes:
1. Mark code comments with `SECURITY` for critical sections
2. Update `SECURITY_FIXES.md` with details
3. Add tests for validation functions
4. Never commit with real passwords in test data

---

**Current Version**: 2.3  
**Release Date**: 2026-03-02  
**Status**: Stable
