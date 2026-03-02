# Wi-Fi Scout Pro - Quick Start Guide

## Installation

### Windows

1. **Run the installer:**
   ```cmd
   install.bat
   ```
   Or double-click `install.bat`

2. **Launch the application:**
   ```cmd
   run_wifi_scout.bat
   ```
   Or double-click `run_wifi_scout.bat`

### Linux / macOS

1. **Make scripts executable:**
   ```bash
   chmod +x install.sh run_wifi_scout.sh
   ```

2. **Run the installer:**
   ```bash
   ./install.sh
   ```

3. **Launch the application:**
   ```bash
   ./run_wifi_scout.sh
   ```

### Manual Installation

```bash
pip install PyQt6 matplotlib
python network_suite.py  # Current version
# python archive/wa.py   # Legacy version (v2.3)
```

## First-Time Setup

When you first run Wi-Fi Scout Pro:

1. The main window opens showing the **Scanner** tab
2. Click **"🔍 Scan Now"** or press **F5** to scan for networks
3. Networks appear in the table with all details
4. Explore other tabs for more features

## Common Tasks

### Scan for Networks

**Method 1:** Click the **"🔍 Scan Now"** button

**Method 2:** Press **F5**

**Method 3:** Enable **"Auto-refresh"** for continuous scanning

### Find the Best Network

1. Run a scan first
2. Click **"⭐ Find Best"** or press **Ctrl+B**
3. The recommended network is highlighted
4. A detailed explanation appears

### Connect to a Network

**Method 1: From Table**
1. Select a network in the table
2. Click **"🔗 Connect"** or press **Ctrl+C**
3. Enter password if required
4. Wait for connection confirmation

**Method 2: From Details Tab**
1. Select a network in the Scanner tab
2. Switch to **Details** tab (or double-click the row)
3. Click **"Connect to This Network"**
4. Enter password if required

### Monitor Signal Quality Over Time

1. Enable **"Auto-refresh every"** checkbox
2. Set interval (recommended: 10-30 seconds)
3. Let it run for 5-10 minutes
4. Switch to **"Signal History"** tab
5. View the line chart showing signal trends

### Filter Networks

**By Text:**
- Type in the **"Search SSID or BSSID..."** box
- Results filter in real-time

**By Band:**
- Use the **band filter dropdown**
- Options: All Bands, 2.4GHz, 5GHz, 6GHz

**Hide Open Networks:**
- Check **"Hide OPEN networks"**
- Insecure networks are hidden

### View Detailed Information

**Method 1:**
- Select a network in the table
- The **Details** tab updates automatically

**Method 2:**
- Double-click any network row
- Automatically switches to Details tab

### Export Data

1. Run a scan first
2. Click **"💾 Export"** or press **Ctrl+E**
3. Choose format:
   - **CSV**: For Excel/spreadsheets
   - **JSON**: For programmatic use
4. Choose save location
5. File is saved with timestamp

### Export HTML Report

1. Menu → **File** → **Export HTML Report**
2. Choose save location
3. Open in web browser for formatted view

## Interface Features

### Scanner Tab

**Control Panel:**
- Scan Now: Perform immediate scan
- Find Best: Identify optimal network
- Connect: Join selected network
- Export: Save scan results

**Auto-Refresh:**
- Enable for continuous monitoring
- Set interval (5-300 seconds)
- Progress bar shows scan status

**Filters:**
- Search box for text filtering
- Band selector for frequency filtering
- Hide Open option for security

**Statistics Bar:**
- Total network count
- Unique SSID count
- Average signal strength
- Strongest network
- Currently connected network

**Network Table:**
- Click column headers to sort
- Color-coded signal strength:
  - 🟢 Green: Excellent (-50 dBm or better)
  - 🟡 Yellow: Good (-50 to -65 dBm)
  - 🟠 Orange: Fair (-65 to -75 dBm)
  - 🔴 Red: Poor (below -75 dBm)
- Color-coded security:
  - 🟢 Green: WPA3
  - 🔵 Blue: WPA2
  - 🔴 Red: OPEN/WEP
- Connected networks highlighted in green

### Details Tab

**Network Information:**
- All available metrics in detail
- Select-able text for copying

**Quality Assessment:**
- Signal strength analysis
- Security evaluation
- Channel/frequency recommendations
- Overall score interpretation

**Connection Management:**
- Direct connect button
- Refresh connection status
- Current connection info

### Signal History Tab

**Chart Display:**
- Line graph of signal strength over time
- X-axis: Time in seconds (relative)
- Y-axis: Signal strength in dBm
- Multiple networks shown in different colors

**Network Selector:**
- "All (top 5)": Shows 5 strongest networks
- Individual networks: Select specific network

**Chart Controls:**
- Clear History: Reset all collected data

### Logs Tab

**Log Display:**
- Real-time logging of all events
- Scan results and errors
- Connection attempts
- Export operations

**Log Controls:**
- Clear Log: Clear display (doesn't delete file)
- Copy Log File Path: Copy to clipboard
- Open Log Folder: Open in file explorer

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **F5** | Refresh Scan |
| **Ctrl+B** | Find Best Network |
| **Ctrl+C** | Connect to Selected |
| **Ctrl+E** | Export Results |
| **Ctrl+T** | Toggle Dark/Light Theme |
| **Ctrl+Q** | Exit Application |

## Tips & Tricks

### Best Practices for Monitoring

1. **Enable auto-refresh** with 15-30 second intervals
2. Let it run during problem times
3. Check **Signal History** for patterns
4. Look for:
   - Sudden drops (interference)
   - Consistent weakness (distance)
   - Periodic spikes (other devices)

### Choosing the Best Network

The scoring algorithm considers:
- **Security**: WPA3 > WPA2 > WPA > WEP > OPEN
- **Signal**: Stronger is better
- **Band**: 5GHz preferred if signal good
- **Congestion**: Fewer nearby APs better
- **Channel**: Non-overlapping preferred (1, 6, 11 for 2.4GHz)

Don't just pick the strongest signal - security matters!

### Understanding Signal Strength

| dBm Range | Quality | Expected Performance |
|-----------|---------|---------------------|
| -30 to -50 | Excellent | Maximum speed, very reliable |
| -50 to -65 | Good | High speed, reliable |
| -65 to -75 | Fair | Medium speed, occasional issues |
| -75 to -85 | Poor | Low speed, frequent drops |
| Below -85 | Very Poor | Unusable |

### Channel Selection (2.4GHz)

**Non-Overlapping Channels:**
- Channel 1
- Channel 6
- Channel 11

**Why it matters:**
- Other channels overlap and interfere
- Use channel scan to find least congested
- If channel 6 is crowded, try 1 or 11

### 2.4GHz vs 5GHz

**2.4GHz:**
- ✓ Better range/penetration
- ✓ Works with all devices
- ✗ More interference
- ✗ Lower maximum speed
- ✗ Only 3 non-overlapping channels

**5GHz:**
- ✓ Much faster maximum speed
- ✓ Less interference
- ✓ Many non-overlapping channels
- ✗ Shorter range
- ✗ Doesn't penetrate walls as well

**Recommendation:** Use 5GHz if you're close to router, 2.4GHz if you need range.

## Troubleshooting

### Application Won't Start

**Windows:**
- Right-click `run_wifi_scout.bat` → Run as Administrator
- Check Python is in PATH

**Linux:**
- Check permissions: `chmod +x run_wifi_scout.sh`
- Install required packages: `sudo apt install python3-pyqt6`

**macOS:**
- Grant terminal location permissions
- System Preferences → Security & Privacy → Privacy

### Scan Returns No Results

**Windows:**
- Enable Wi-Fi adapter
- Run as Administrator

**Linux:**
- Check NetworkManager: `systemctl status NetworkManager`
- Ensure user in netdev group: `groups $USER`

**macOS:**
- Check Wi-Fi is enabled
- Grant location permissions

### Can't Connect to Networks

**Windows:**
- Run as Administrator
- Check Wi-Fi adapter settings

**Linux:**
- Add user to netdev: `sudo usermod -a -G netdev $USER`
- Logout and login again

**macOS:**
- Check system password is correct
- May need to manually approve in System Preferences

### Signal History Chart Not Showing

- Install matplotlib: `pip install matplotlib`
- Restart application
- Enable auto-refresh to collect data
- Wait a few minutes for data to accumulate

### Inaccurate Signal Readings

- Different platforms report differently
- dBm converted from % is approximate
- Some platforms don't provide noise data
- Readings are comparative, not absolute

## Advanced Features

### Exporting for Analysis

**CSV Format:**
```csv
SSID,BSSID,Signal (dBm),Channel,Band,Security,Score
MyNetwork,aa:bb:cc:dd:ee:ff,-65,6,2.4GHz,WPA2,45.3
```

Use for:
- Spreadsheet analysis
- Graphing in Excel
- Long-term tracking

**JSON Format:**
```json
[
  {
    "ssid": "MyNetwork",
    "bssid": "aa:bb:cc:dd:ee:ff",
    "signal_dbm": -65,
    "channel": 6,
    "security": "WPA2"
  }
]
```

Use for:
- Programmatic processing
- Integration with other tools
- Automated analysis

**HTML Format:**
- Professional-looking reports
- Color-coded for easy reading
- Shareable with non-technical users
- Print-friendly

### Finding Channel Interference

1. Run scan
2. Sort by **Channel** column
3. Look for clusters of networks
4. Count networks on same channel
5. Choose least crowded channel for your router

### Comparing Network Quality

1. Enable auto-refresh (10 second interval)
2. Run for 10 minutes
3. Switch to Signal History tab
4. Select "All (top 5)"
5. Compare stability:
   - Flat line = stable
   - Spiky = interference
   - Declining = moving away

## Getting Help

### Log Files

Logs are in `~/.wifi_scout/` directory:
- Windows: `C:\Users\<username>\.wifi_scout\`
- Linux/Mac: `/home/<username>/.wifi_scout/`

Files named: `wifi_scout_YYYYMMDD_HHMMSS.log`

### Common Issues

1. **Scan fails repeatedly**
   - Check Wi-Fi adapter is working
   - Try running with elevated privileges
   - Check logs for specific error

2. **Connection fails**
   - Verify password is correct
   - Check network is in range
   - Try manual connection first

3. **Application crashes**
   - Check Python version (3.8+ required)
   - Verify dependencies installed
   - Check logs for error details

### Reporting Issues

When reporting problems, include:
1. Operating System and version
2. Python version (`python --version`)
3. Error message
4. Log file content
5. Steps to reproduce

## Performance Tips

### For Best Performance

1. **Disable auto-refresh when not needed**
   - Only enable for active monitoring
   - Use longer intervals (30+ seconds)

2. **Clear signal history periodically**
   - Tools → Clear Signal History
   - Keeps memory usage low

3. **Filter networks**
   - Use band filter to reduce displayed rows
   - Hide OPEN networks if not needed

4. **Close unused tabs**
   - Stay on Scanner tab for fastest scans
   - Charts use more resources

## Security Notes

### Safe Practices

1. **Don't connect to OPEN networks**
   - Traffic can be intercepted
   - Passwords can be stolen
   - Use VPN if you must

2. **Prefer WPA3 or WPA2**
   - WPA3 is most secure
   - WPA2 is acceptable
   - Avoid WPA and WEP

3. **Use strong passwords**
   - 12+ characters
   - Mix of letters, numbers, symbols
   - Unique per network

4. **Check certificates**
   - For WPA2-Enterprise
   - Don't ignore warnings
   - Verify with IT department

### Privacy

- Application doesn't send data anywhere
- Passwords not logged
- Scan results stay local
- Exports are under your control

---

**Need more help? Check README.md for detailed documentation.**
