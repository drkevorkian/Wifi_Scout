# 🔄 Network Scout - Migration Guide

**From**: Legacy installation (requirements.txt + scripts)  
**To**: Modern pip installation with console commands  
**Version**: 2.2.9

---

## 🎯 Quick Migration (Recommended)

If you're already using Network Scout, here's how to upgrade to the modern installation:

```bash
# 1. Navigate to your Network Scout directory
cd Wifi_Scout

# 2. Pull latest changes (if using git)
git pull

# 3. Uninstall old method (if applicable)
# No action needed if you were using venv + requirements.txt

# 4. Install modern way
pip install -e ".[full]"

# 5. Test it works
network-scout --version

# 6. Done! Start using console commands
network-scout wifi scan
```

---

## 📚 What Changed?

### Installation Method

**Old Way (Still Works)**:
```bash
# Create venv manually
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run with Python
python network_suite.py
```

**New Way (Recommended)**:
```bash
# Install directly with pip (auto-handles dependencies)
pip install -e ".[full]"

# Run with console command (works from anywhere)
network-scout
```

### Running the Application

**Old Way**:
```bash
# Must be in the project directory
python network_suite.py

# Or use launcher scripts
./run_wifi_scout.sh
run_wifi_scout.bat
```

**New Way**:
```bash
# Works from any directory
network-scout

# Short aliases available
wifi-scout
ns

# CLI examples
network-scout wifi scan
network-scout dns-lookup google.com
ns ping 8.8.8.8
```

---

## 🎁 New Features You Get

### 1. Console Commands
After `pip install -e ".[full]"`, you get three commands:
- `network-scout` - Main command
- `wifi-scout` - Alternative name
- `ns` - Quick alias

### 2. Optional Dependencies
Install only what you need:
```bash
pip install -e .            # Minimal (CLI only, no GUI)
pip install -e ".[gui]"     # Add GUI support
pip install -e ".[full]"    # Everything (recommended)
pip install -e ".[dev]"     # Add development tools
```

### 3. Modern Testing
```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run test suite
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### 4. CI/CD
- Automated testing on every push
- Multi-platform verification (Win/Linux/macOS)
- Security scanning

---

## 🔄 Compatibility

### Backward Compatibility

✅ **All old methods still work**:
- `python network_suite.py` - Still works
- `install.bat` / `install.sh` - Still work
- `run_wifi_scout.bat` / `run_wifi_scout.sh` - Still work
- `requirements.txt` - Still exists

✅ **No breaking changes**:
- All CLI arguments unchanged
- All features work the same
- GUI unchanged
- Data formats unchanged

### What's Removed?

❌ Nothing! Everything is additive.

---

## 🆕 For New Users

**Just starting with Network Scout?**

### Quick Start (2 commands)
```bash
# 1. Install
pip install -e ".[full]"

# 2. Run
network-scout
```

That's it! No need to worry about venv, requirements.txt, or scripts.

---

## 🔧 Troubleshooting Migration

### "network-scout: command not found"

**Solution**: Make sure you installed with `-e`:
```bash
pip install -e ".[full]"
```

The `-e` (editable) flag is important for local development.

### "ModuleNotFoundError: No module named 'PyQt6'"

**Solution**: Install with the `[full]` extra:
```bash
pip install -e ".[full]"
```

Or just GUI:
```bash
pip install -e ".[gui]"
```

### "I want the old way back"

**Solution**: The old way still works! Just use:
```bash
python network_suite.py
```

Or the launcher scripts:
```bash
./run_wifi_scout.sh
```

---

## 📦 Extras Explained

| Extra | Includes | Use Case |
|-------|----------|----------|
| (none) | Core only | Minimal CLI-only install |
| `[gui]` | + PyQt6 | Add GUI support |
| `[viz]` | + matplotlib | Add signal history charts |
| `[network]` | + dnspython, psutil | Enhanced network tools |
| `[full]` | All above | **Recommended for users** |
| `[dev]` | + pytest, black, etc. | **For developers** |
| `[all]` | Everything | Development + all features |

### Examples
```bash
# Minimal (no GUI, basic tools only)
pip install -e .

# GUI + core (no enhanced networking)
pip install -e ".[gui]"

# Everything recommended for daily use
pip install -e ".[full]"

# Everything + development tools
pip install -e ".[all]"
```

---

## 🎓 Developer Migration

### Old Development Workflow
```bash
# Edit code
vim network_suite.py

# Test manually
python network_suite.py wifi scan

# Hope nothing broke
```

### New Development Workflow
```bash
# Install with dev tools
pip install -e ".[dev]"

# Edit code
vim network_suite.py

# Run tests
pytest tests/ -v

# Check formatting
black --check .

# Push (CI runs automatically)
git push
```

---

## 📊 Version Naming Clarification

**You may have seen these version numbers in old docs:**
- v2.2.9 ✅ **CURRENT** (this version)
- v3.0 ❌ Old draft/future reference (ignore)
- v3.0.1 ❌ Old draft/future reference (ignore)
- v3.0.2 ❌ Old draft/future reference (ignore)

**Official version**: **2.2.9**

All documentation has been updated to reflect this.

---

## ✅ Migration Checklist

For existing users upgrading:

- [ ] Backed up current installation (just in case)
- [ ] Pulled latest code (`git pull` if using git)
- [ ] Ran `pip install -e ".[full]"`
- [ ] Tested: `network-scout --version`
- [ ] Tested: `network-scout wifi scan`
- [ ] Verified GUI works: `network-scout`
- [ ] (Optional) Installed dev tools: `pip install -e ".[dev]"`
- [ ] (Optional) Ran tests: `pytest tests/ -v`
- [ ] Updated bookmarks to use `network-scout` command

---

## 🆘 Need Help?

### Resources
1. **README.md** - Full documentation
2. **GETTING_STARTED.md** - Detailed installation guide
3. **IMPROVEMENTS_COMPLETE.md** - What changed and why
4. **GitHub Issues** - Report problems or ask questions

### Still Using Old Method?

**That's totally fine!** The old installation and running methods still work:
```bash
./install.sh
./run_wifi_scout.sh
```

The new method is just more convenient and professional.

---

## 🎉 Benefits Summary

### Why Migrate?

| Benefit | Old Way | New Way |
|---------|---------|---------|
| Installation | 3-4 commands | 1 command |
| Running | Must be in directory | Works anywhere |
| Dependencies | Manual | Automatic |
| Optional features | All or nothing | Pick what you need |
| Testing | Manual/none | `pytest tests/` |
| Updates | Manual | `pip install --upgrade` |
| Professional? | Decent | ✅ Modern best practices |

---

**Ready to ship!** 🚀

*Last Updated: 2026-03-02 - Network Scout v2.2.9*
