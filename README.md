# 🛡️ MCP-Watchdog

<p align="center">
  <strong>Real-time Anomaly Detection for MCP (Model Context Protocol) Communications</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Beta-yellow" alt="Beta Status">
  <img src="https://img.shields.io/badge/Production-Not%20Ready-red" alt="Not Production Ready">
</p>

<p align="center">
  <a href="#overview">Overview</a> •
  <a href="#background">Background</a> •
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#contributing">Contributing</a>
</p>

---

## ⚠️ Important Notice

**MCP-Watchdog is currently in BETA status and is NOT suitable for production use.** This tool is:
- 🧪 Experimental and under active development
- 🐛 May contain bugs and unexpected behaviors
- 📊 Not thoroughly tested in all environments
- 🔄 Subject to breaking changes without notice

**Use at your own risk** and only in development/testing environments. Do not rely on this tool for critical security monitoring in production systems.

---

## 🎯 Overview

MCP-Watchdog is a lightweight security monitoring tool that captures and analyzes communications between Claude Desktop and MCP servers, detecting anomalous patterns in real-time without requiring complex policy definitions.

## 📖 Background

While several MCP traffic monitoring tools exist, most rely on predefined policies and keyword-based detection for sensitive information monitoring. However, the definition of "sensitive information" varies greatly across industries and organizations, making generic detection rules insufficient.

Traditional DLP (Data Loss Prevention) approaches require:
- 📋 Extensive mapping of business workflows
- 🔍 Identification of all sensitive data types
- ⚙️ Custom policy creation and maintenance
- ⏱️ Significant time and effort investment

**MCP-Watchdog takes a different approach**: Instead of predefined rules, it learns normal usage patterns from legitimate users and detects anomalies based on behavioral deviations. This is the first known attempt at applying anomaly detection to MCP traffic.

## ✨ Features

- 🚀 **Zero-configuration anomaly detection** - No need to define sensitive data patterns
- 📊 **Automatic baseline learning** - Learns from your normal usage patterns
- ⚡ **Real-time monitoring** - Instant alerts for suspicious activities
- 🎨 **Color-coded alerts** - Easy-to-read severity indicators
- 📝 **Comprehensive logging** - Full audit trail of all detections
- 🔄 **Transparent proxy** - No impact on Claude Desktop functionality

## 🔧 System Requirements

- Python 3.8+
- Windows 10/11
- Node.js (for npx)
- Claude Desktop

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/MCP-Watchdog.git
cd MCP-Watchdog

# Install dependencies
pip install -r requirements.txt
```

## 🔧 Proxy Configuration

### Understanding the Proxy Setup

MCP-Watchdog works by intercepting communication between Claude Desktop and MCP servers. It does this by inserting a transparent proxy (`mcp_proxy.py`) that:
- Captures all MCP protocol messages
- Logs them for analysis
- Forwards them unchanged to maintain functionality

### Configuration Process

The `setup_proxy.py` script automatically modifies your Claude Desktop configuration to route traffic through the proxy:

**Before (Original Configuration):**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"]
    }
  }
}
```

**After (With MCP-Watchdog Proxy):**
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "python",
      "args": [
        "C:\\path\\to\\MCP-Watchdog\\mcp_proxy.py",
        "filesystem",
        "npx",
        "-y",
        "@modelcontextprotocol/server-filesystem"
      ]
    }
  }
}
```

### Setup Commands

```bash
# Standard setup
python setup_proxy.py

# Setup with administrator privileges (if permission errors)
python setup_proxy.py --admin

# Restore original configuration from backup
python setup_proxy.py --restore

# Remove proxy configuration (reset to original)
python setup_proxy.py --reset
```

### Configuration File Location

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Backup**: `%APPDATA%\Claude\claude_desktop_config.backup`

### Troubleshooting Proxy Setup

<details>
<summary><b>❌ "Config file may not be writable"</b></summary>

Run with administrator privileges:
```bash
python setup_proxy.py --admin
```
</details>

<details>
<summary><b>❌ "Claude Desktop appears to be running"</b></summary>

1. Close Claude Desktop completely
2. Check Task Manager for any `Claude.exe` processes
3. Run setup again
</details>

<details>
<summary><b>❌ Proxy not capturing data</b></summary>

1. Verify proxy is in config: Check `claude_desktop_config.json`
2. Restart Claude Desktop
3. Check proxy log: `type mcp_proxy_minimal.log`
4. Ensure Python is in PATH: `python --version`
</details>

<details>
<summary><b>❌ Want to remove MCP-Watchdog</b></summary>

To completely remove MCP-Watchdog and restore original configuration:
```bash
# Option 1: Reset configuration
python setup_proxy.py --reset

# Option 2: Restore from backup
python setup_proxy.py --restore
```
</details>

### Manual Configuration (Advanced)

If automatic setup fails, you can manually edit the configuration:

1. Close Claude Desktop
2. Open `%APPDATA%\Claude\claude_desktop_config.json`
3. For each MCP server, wrap the command:
   - Change `"command": "npx"` to `"command": "python"`
   - Prepend to args: `["C:\\path\\to\\mcp_proxy.py", "server_name", "npx"]`
4. Save and restart Claude Desktop

## 🚀 Quick Start

### 1️⃣ Configure Proxy
```bash
python setup_proxy.py
```
This will:
- Backup your current configuration
- Insert the monitoring proxy for all MCP servers
- Verify the configuration was updated correctly

⚠️ **Important**: Claude Desktop must be closed during configuration

### 2️⃣ Collect Normal Usage Data
**Important**: Before building a baseline, you need to collect data from normal usage.

1. **Restart Claude Desktop** after proxy configuration
2. **Use Claude normally** for several sessions:
   - Interact with various MCP tools
   - Perform your typical workflows
   - Use different features and commands
   - The more diverse your usage, the better the baseline

3. **Verify data collection**:
   ```bash
   # Check if data is being captured
   dir mcp_captured_data\
   
   # View proxy logs
   type mcp_proxy_minimal.log | more
   ```
   You should see session directories like:
   ```
   session_20250723_143022_filesystem/
   session_20250723_145512_brave-search/
   session_20250723_150234_memory/
   ```

4. **Monitor live capture** (optional):
   ```bash
   # Watch data being captured in real-time
   python realtime_monitor.py --capture-only
   ```

### 3️⃣ Build Baseline
Once you have collected sufficient data (recommended: at least 10-20 sessions):
```bash
python mcp_baseline_builder.py
```
This will analyze all captured sessions and create a baseline of normal behavior.

### 4️⃣ Start Monitoring
```bash
python realtime_monitor.py
```
Now the system will monitor in real-time and alert on anomalous activities.

## 📊 Data Collection Tips

For optimal baseline quality:

- **Diverse Usage**: Use different MCP tools and features
- **Regular Patterns**: Perform your typical daily workflows
- **Multiple Sessions**: Aim for at least 10-20 different sessions
- **Various Tools**: Interact with filesystem, search, database, and other MCP servers
- **Time Periods**: Collect data across different times of day

⚠️ **Note**: The baseline quality directly impacts detection accuracy. More diverse and representative data leads to better anomaly detection.

### Normal Activity
```
[14:23:45] ✅ → API-post-search: Customer Support Guidelines...
```

### 🚨 Anomaly Detection
```
============================================================
🔴 ANOMALY DETECTED - HIGH SEVERITY
============================================================
Time: 2025-07-23 14:23:46
Tool: API-post-search
Query: Database Password Reset
Confidence: 100.0%
New Topics: database, password, reset
Expected: customer, support, service
============================================================
```

## 📁 Project Structure

```
MCP-Watchdog/
├── 🔌 mcp_proxy.py              # Communication interceptor
├── 🧠 mcp_anomaly_detector.py   # ML-based detection engine
├── 📊 mcp_baseline_builder.py   # Pattern learning tool
├── 👁️ realtime_monitor.py       # Live monitoring interface
├── ⚙️ setup_proxy.py            # Auto-configuration script
├── 📂 mcp_captured_data/        # Session logs
│   └── session_*/               # Individual sessions
│       ├── requests.jsonl       # Captured requests
│       └── responses.jsonl      # Captured responses
├── 📄 mcp_proxy_minimal.log     # Proxy operation log
├── 🔐 mcp_baseline.pkl          # Trained baseline model
└── 📋 anomaly_log_*.json        # Detected anomalies
```

## 🎛️ Configuration

### Adjust Detection Sensitivity
```python
# Stricter detection
detector = SimpleTopicAnomalyDetector(sensitivity=0.9)

# More lenient
detector = SimpleTopicAnomalyDetector(sensitivity=0.5)
```

## 🐛 Troubleshooting

<details>
<summary><b>No Data Being Captured</b></summary>

1. Ensure proxy is configured: `python setup_proxy.py`
2. Restart Claude Desktop completely
3. Check proxy logs: `type mcp_proxy_minimal.log`
4. Verify `mcp_captured_data` directory exists
</details>

<details>
<summary><b>Insufficient Baseline Data</b></summary>

- Minimum recommended: 10-20 sessions
- Use various MCP tools during collection
- Check data quality: `python mcp_baseline_builder.py`
- The builder will show statistics of collected data
</details>

<details>
<summary><b>Proxy Issues</b></summary>

1. Exit Claude Desktop
2. Kill Python: `taskkill /F /IM python.exe`
3. Restart Claude Desktop
</details>

<details>
<summary><b>False Positives</b></summary>

- Lower sensitivity setting
- Rebuild baseline with more data
- Add patterns to whitelist
</details>

## 🔒 Security Notes

- 🔐 Captured data may contain sensitive information
- 🛡️ Secure the `mcp_captured_data` directory
- 📋 Review anomaly logs regularly
- ⚠️ **Beta software** - Not recommended for production security monitoring
- 🧪 Test thoroughly in isolated environments before wider deployment

## 🗺️ Roadmap

- [ ] 🌐 Web dashboard
- [ ] 📧 Email/Slack alerts
- [ ] 🤖 Advanced ML models
- [ ] 📈 Multi-session analytics
- [ ] ⚡ Automated responses

## 🤝 Contributing

Contributions are welcome! Please note that this is a beta project:
- 🐛 Bug reports and fixes are especially appreciated
- 💡 Feature suggestions should consider the experimental nature
- 🧪 All contributions should include appropriate tests
- 📝 Update documentation for any changes

Please open an issue to discuss major changes.

## 📄 License

MIT License

## 💬 Support

Found a bug? Have a question? Please [open an issue](https://github.com/yourusername/MCP-Watchdog/issues).

---

<p align="center">
  Made with ❤️ for the MCP community
</p>