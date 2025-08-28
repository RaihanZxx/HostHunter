# HostHunter Usage Guide

This document provides detailed instructions for using **HostHunter**, a tool for checking host connectivity, Vmess/Trojan protocols, and quota bugs.

## Running the Tool

1. Ensure all prerequisites are installed (see [README.md](../README.md)).
2. Run the tool:
   ```bash
   python hosthunter.py
   ```
3. Follow the interactive menu to select an option.

## Menu Options

1. **Check Single Host**:
   - Input: Hostname (e.g., `cdn.udemy.com`), port (default: 443), timeout (default: 10s).
   - Output: HTTP/HTTPS status with response time.
   - Example: `cdn.udemy.com` on port `443` may return `[200 OK]`.

2. **Check Ping**:
   - Input: Hostname, timeout.
   - Output: Ping latency or fallback HTTPS test if ICMP is blocked.
   - Example: `www.google.com` may return `latency: 45.67 ms`.

3. **Scan Hosts from File**:
   - Input: Path to a text file with one host per line, timeout.
   - Example file (`hosts.txt`):
     ```text
     cdn.udemy.com
     www.ruangguru.com
     ```
   - Output: Table of results for all hosts.

4. **Save Results**:
   - Saves scan results to a file in the `results/` directory.
   - Example: `hosthunter_results_20250525_104200.txt`.

5. **Show Response Time Chart**:
   - Displays an ASCII chart of response times for scanned hosts.
   - Requires prior scan results.

6. **Check Vmess/Trojan**:
   - Input: Host, port, WebSocket path, protocol (`vmess` or `trojan`), UUID/password, TLS option, timeout.
   - Output: WebSocket connectivity status with JSON validation for Vmess.
   - Example: `example.com:443/vmess` with valid UUID.

7. **Check Quota Bug**:
   - Input: Host, port, timeout.
   - Output: Checks for edukasi-to-regular quota exploit using a custom header.
   - Example: `www.ruangguru.com` may return `[Quota Bug OK]`.

8. **Exit**:
   - Terminates the program.

## Example Hosts File

Create a file (e.g., `examples/hosts.txt`):
```text
cdn.udemy.com
www.ruangguru.com
example.com
```

## Timeout Configuration

- The tool prompts for a timeout value (in seconds) for most operations.
- Default: 10 seconds.
- Use lower values for faster scans or higher values for slow networks.

## Logging

- Logs are saved in the `logs/` directory with timestamps (e.g., `hosthunter_20250525_104200.log`).
- Includes info, warnings, and errors for auditing.

## Legal Warning

⚠️ **Use Responsibly**: Unauthorized use of this tool, especially for quota exploitation, may violate service policies or laws. Always obtain explicit permission from service providers before testing.