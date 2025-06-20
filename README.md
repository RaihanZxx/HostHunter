# HostHunter 🕵️‍♂️

**A powerful tool for host checking and quota bug exploration**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

HostHunter is a Python-based CLI tool designed to check host connectivity, resolve IPs, test Vmess/Trojan protocols, and explore quota bugs (e.g., edukasi-to-regular exploits). Built with a modern interface using the `rich` library, it provides a user-friendly experience for network enthusiasts and security researchers.

> ⚠️ **Legal Warning**: This tool is for **educational purposes only**. Unauthorized use, especially for quota exploitation, may violate service policies or laws. Always obtain explicit permission before testing.

---

## 🖼️ Previews

### Below are some previews of HostHunter in action:
**Scan Host From File (batch):**

<img src="https://github.com/RaihanZxx/HostHunter/blob/main/previews%2FIMG_20250526_122834_765.jpg" width="400">

**Show Response Time Chart:**

<img src="https://github.com/RaihanZxx/HostHunter/blob/main/previews%2FIMG_20250526_122834_584.jpg" width="400">

**Check Ping:**

<img src="https://github.com/RaihanZxx/HostHunter/blob/main/previews%2FIMG_20250526_122833_950.jpg" width="400">

---

## ✨ Features

- **Host Checking**: Verify host status via HTTP/HTTPS with detailed response times.
- **Ping Testing**: Check host reachability with ICMP ping and fallback to HTTPS.
- **File Scanning**: Scan multiple hosts from a file with parallel processing for efficiency.
- **Vmess/Trojan Support**: Test WebSocket-based Vmess and Trojan connections.
- **Quota Bug Detection**: Identify potential notregular-to-regular quota exploits.
- **Visual Output**: Generate ASCII-based response time charts for quick analysis.
- **Logging**: Save detailed logs and results for auditing.

---

## 🚀 Installation

### Prerequisites
- **Python 3.8+**
- System tools: `dig`, `curl`, `ping`
- Python libraries: Install via `requirements.txt`

### Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/RaihanZxx/HostHunter.git
   cd HostHunter
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure system tools are installed:
   - On Debian/Ubuntu:
     ```bash
     sudo apt-get install dnsutils curl iputils-ping
     ```
   - On macOS:
     ```bash
     brew install dig curl
     ```

4. Run the tool:
   ```bash
   python hosthunter.py
   ```

---

## 🛠️ Usage

Run the tool and select from the interactive menu:

1. **Check Single Host**: Test a single host (e.g., `cdn.udemy.com`) on a specified port.
2. **Check Ping**: Ping a host to check reachability.
3. **Scan Hosts from File**: Provide a text file with one host per line (see `examples/hosts.txt`).
4. **Save Results**: Save scan results to a text file.
5. **Show Response Time Chart**: Visualize response times with an ASCII chart.
6. **Check Vmess/Trojan**: Test WebSocket connectivity for Vmess or Trojan protocols.
7. **Check Quota Bug**: Test for edukasi-to-regular quota exploits.
8. **Exit**: Quit the tool.

For detailed usage instructions, see [docs/usage.md](docs/usage.md).

### Example
```bash
$ python hosthunter.py
```
- Enter a host like `cdn.udemy.com` and port `443`.
- For file scanning, create a `hosts.txt` (see `examples/hosts.txt`):
  ```text
  cdn.udemy.com
  www.ruangguru.com
  ```

---

## 📋 Example Output

```
[200 OK] cdn.udemy.com (IP: 104.16.65.34, Port: 443, Response: 120.45 ms) is active!
[Ping OK] www.ruangguru.com (IP: 172.67.68.123) latency: 45.67 ms
[VMESS OK] example.com (Port: 443, Path: /vmess, TLS: True) is reachable with valid JSON response.
[Quota Bug OK] www.ruangguru.com (Port: 443) allows access with edukasi header!
```

---

## 📊 Response Time Chart

HostHunter generates an ASCII chart to visualize response times:

```
┌──────────────────────────────────────────────────────────────┐
│ Response Time Chart (1 █ = 10 ms, Max: 120.45 ms)                       │
├──────────────────────────────────────────────────────────────┤
│ cdn.udemy.com        | ████████████ 120.45 ms                         │
│ www.ruangguru.com    | █████ 45.67 ms                                  │
└──────────────────────────────────────────────────────────────┘
Scale: █ = 10 ms
```

---

## ⚠️ Legal Notice

HostHunter is intended for **educational and authorized testing only**. Unauthorized use, especially for exploiting quota systems, may violate terms of service or local laws. Always obtain explicit permission from service providers before using this tool.

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/YourFeature`).
3. Commit your changes (`git commit -m 'Add YourFeature'`).
4. Push to the branch (`git push origin feature/YourFeature`).
5. Open a pull request.

---

## 📬 Contact

For questions or feedback, reach out via GitHub Issues or contact the maintainer at:
- <img src="https://img.shields.io/badge/Telegram-%40HanSoBored-0088cc?style=flat-square&logo=telegram" alt="Telegram" height="20">
- <img src="https://img.shields.io/badge/Email-raihanzxzy%40gmail.com-d14836?style=flat-square&logo=gmail" alt="Email" height="20">

---