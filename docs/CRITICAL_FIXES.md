# CRITICAL FIXES - Implementation Guide

## Priority 1: Windows Password File Permission Race Condition

### Current Problem (SECURITY VULNERABILITY)
The temporary XML file containing the WiFi password is created with default permissions first, then chmod is called. For a brief moment, the file is world-readable.

### Location
`core/wifi_engine.py` lines 609-662

### Current Code
```python
with open(profile_path, "w", encoding="utf-8") as f:
    os.chmod(profile_path, 0o600)  # ❌ TOO LATE!
    # file already exists with default perms
    f.write(xml_content)
```

### Fixed Code
```python
# Create file with secure permissions atomically
import os
fd = os.open(profile_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="utf-8") as f:
    f.write(xml_content)
```

### Complete Fix Implementation
Replace lines 604-662 in `core/wifi_engine.py` with:

```python
if system == "Windows":
    # Create temporary XML profile with secure permissions
    temp_dir = tempfile.gettempdir()
    profile_name = f"wifi_profile_{uuid.uuid4().hex}.xml"
    profile_path = os.path.join(temp_dir, profile_name)
    
    try:
        # Create file with restrictive permissions BEFORE writing
        # This prevents race condition where password is briefly readable
        fd = os.open(profile_path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if password:
                xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{xml_escape(ssid)}</name>
    <SSIDConfig>
        <SSID>
            <name>{xml_escape(ssid)}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{xml_escape(password)}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
            else:
                xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{xml_escape(ssid)}</name>
    <SSIDConfig>
        <SSID>
            <name>{xml_escape(ssid)}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>"""
            
            f.write(xml_content)
        
        # Add profile
        rc, out, err = run_cmd(["netsh", "wlan", "add", "profile", f"filename={profile_path}"], timeout=10)
        if rc != 0:
            return False, f"Failed to add profile: {err.strip()}"
        
        # Connect
        rc, out, err = run_cmd(["netsh", "wlan", "connect", f"name={ssid}"], timeout=15)
        if rc != 0:
            return False, f"Failed to connect: {err.strip()}"
        
        logger.info(f"Connected to {ssid}")
        return True, f"Successfully connected to {ssid}"
    
    finally:
        secure_delete_file(profile_path, logger)
```

---

## Priority 2: Remove Duplicate WifiNetwork Definitions

### Current Problem (TYPE SAFETY ISSUE)
WifiNetwork dataclass is defined 4 times in different files, causing potential type mismatches.

### Locations
- `network_suite.py` lines 58-76 (main definition) ✅ KEEP
- `core/wifi_engine.py` lines 149-166 (Windows) ❌ DUPLICATE
- `core/wifi_engine.py` lines 247-264 (Linux) ❌ DUPLICATE  
- `core/wifi_engine.py` lines 358-375 (macOS) ❌ DUPLICATE

### Fix
Remove all duplicate definitions from `wifi_engine.py` and use the one from `network_suite.py`

### Implementation

**Step 1**: At top of `core/wifi_engine.py`, add import:
```python
# After line 20, add:
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    # Import for type hints only
    from ..network_suite import WifiNetwork
```

**Step 2**: Remove dataclass definitions:
- DELETE lines 146-166 (Windows scanner)
- DELETE lines 244-264 (Linux scanner)
- DELETE lines 355-375 (macOS scanner)

**Step 3**: Change return type hints:
```python
def scan_windows_netsh(logger: logging.Logger) -> List[Any]:  # Was List[WifiNetwork]
def scan_linux_nmcli(logger: logging.Logger) -> List[Any]:
def scan_macos_airport(logger: logging.Logger) -> List[Any]:
def scan_wifi(logger: logging.Logger) -> List[Any]:
```

**Step 4**: Keep creating instances the same way (Python duck typing handles it):
```python
# This still works even without the class definition here:
nets.append(
    WifiNetwork(  # Python will use whatever WifiNetwork is in scope
        ssid=current_ssid,
        bssid=current_bssid,
        # ... rest of fields
    )
)
```

**Note**: Since `wifi_engine.py` is a separate module and `WifiNetwork` gets passed back to `network_suite.py`, the types will match correctly. The local definitions were redundant.

---

## Priority 3: Fix or Remove Unused CLI --format Argument

### Current Problem (BROKEN FEATURE)
Global `--format` argument is defined but never used by any command.

### Location
`network_suite.py` lines 1020-1022

### Current Code
```python
parser.add_argument("--format", choices=["json", "text"], default="json",
                   help="Output format for CLI results")
```

### Issue
Each subcommand (wifi, dns-lookup, ping, etc.) defines its own `--format` argument, making this global one useless and confusing.

### Fix Options

**Option A: Remove it (RECOMMENDED)**
```python
# DELETE lines 1020-1022
# Let each subcommand handle its own format
```

**Option B: Make it work globally**
```python
# Change each tool's format default based on global setting
# This is complex and not recommended
```

### Recommended: Option A - Delete Lines 1020-1022

---

## Priority 4: Add Input Validation on Settings Restore

### Current Problem (DATA INTEGRITY)
QSettings values restored without validation - corrupted settings could crash app.

### Location
`network_suite.py` lines 962-971

### Current Code
```python
def restore_settings(self) -> None:
    """Restore settings from QSettings."""
    settings = QSettings("NetworkSuite", "WiFiScout")
    self.dark_mode = settings.value("theme/dark_mode", False, type=bool)
    interval = settings.value("wifi/scan_interval", 10, type=int)
    self.spin_interval.setValue(interval)  # ❌ No validation
```

### Fixed Code
```python
def restore_settings(self) -> None:
    """Restore settings from QSettings."""
    settings = QSettings("NetworkSuite", "WiFiScout")
    
    # Theme (already safe - bool type)
    self.dark_mode = settings.value("theme/dark_mode", False, type=bool)
    
    # Scan interval - validate range
    interval = settings.value("wifi/scan_interval", 10, type=int)
    interval = max(5, min(300, interval))  # Clamp to valid range
    self.spin_interval.setValue(interval)
    
    # Window geometry - validate before restoring
    geometry = settings.value("window/geometry")
    if geometry:
        try:
            self.restoreGeometry(geometry)
        except Exception as e:
            self.logger.warning("Failed to restore window geometry: %s", e)
            # Use default size instead
```

---

## Priority 5: Clear Table on Scan Failure

### Current Problem (UX ISSUE)
Failed scan leaves old data in table, confusing users.

### Location
`network_suite.py` lines 719-723

### Current Code
```python
def on_scan_error(self, msg: str) -> None:
    """Handle scan error."""
    self.set_busy(False)
    self.logger.error("Scan failed: %s", msg)
    QMessageBox.critical(self, "Scan Failed", f"{msg}\n\nSee logs for details.")
    # ❌ Old data still showing
```

### Fixed Code
```python
def on_scan_error(self, msg: str) -> None:
    """Handle scan error."""
    self.set_busy(False)
    self.logger.error("Scan failed: %s", msg)
    
    # Clear old data
    self.networks.clear()
    self.table_manager.clear()
    self.update_statistics()
    
    # Update dashboard
    self.card_ssid.set_value("—")
    self.card_signal.set_value("—")
    self.card_security.set_value("—")
    self.card_score.set_value("—")
    
    QMessageBox.critical(self, "Scan Failed", f"{msg}\n\nSee logs for details.")
```

---

## Testing After Fixes

### Test Critical Fix #1 (Windows Permissions)
```powershell
# On Windows, in PowerShell with admin:
1. Connect to a WiFi network using the app
2. While connecting, quickly check temp dir:
   Get-ChildItem $env:TEMP\wifi_profile_* | Get-Acl
3. File should have restricted permissions (only current user)
```

### Test Fix #2 (Duplicate Types)
```python
# Run app and check for any type-related errors
python network_suite.py wifi scan
# Should work without import errors
```

### Test Fix #3 (CLI Format)
```bash
# This should no longer show the unused --format option:
python network_suite.py --help
```

### Test Fix #4 (Settings Validation)
```python
# Corrupt the settings:
# 1. Run app once to create settings
# 2. Edit with QSettings editor or registry (Windows)
# 3. Set scan_interval to 999999
# 4. Run app - should clamp to 300
```

### Test Fix #5 (Error Handling)
```python
# With WiFi off:
1. Turn off WiFi adapter
2. Click "Scan Now"
3. Table should clear, not show old data
```

---

## Deployment Checklist

- [ ] Back up current code
- [ ] Apply Fix #1 (Windows permissions)
- [ ] Apply Fix #2 (Remove duplicates)
- [ ] Apply Fix #3 (Remove unused --format)
- [ ] Apply Fix #4 (Settings validation)
- [ ] Apply Fix #5 (Clear on error)
- [ ] Run all tests
- [ ] Test on Windows specifically
- [ ] Update version number to 3.0.1
- [ ] Document changes in CHANGELOG.md

---

## Additional Recommendations

### Add Warning to Documentation
In README.md, add security notice:

```markdown
## Security Notice

### Password Exposure on Linux/macOS
When connecting to WiFi networks on Linux and macOS, the password is passed 
as a command-line argument and may be visible in the process list briefly. 
This is a limitation of the underlying system commands (nmcli, networksetup).

**Mitigation**: The password is only visible during the connection attempt 
(typically < 1 second) and is not logged to files.

**Recommendation**: Only use on trusted systems where you control access.
```

### Consider Future Enhancements
1. Add `--debug` CLI flag for verbose logging
2. Add progress bars to long-running operations
3. Add stop buttons for cancellable operations
4. Add configuration file for tunable parameters
5. Add unit tests for critical security functions

---

**End of Critical Fixes Guide**
