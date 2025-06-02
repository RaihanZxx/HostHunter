import subprocess
import requests
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
import re
import os
import time
import datetime
import logging
import websocket
from functools import lru_cache
import shlex
from concurrent.futures import ThreadPoolExecutor
import json

console = Console()

def setup_logging():
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"hosthunter_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logging.info("HostHunter started")
    logging.warning("This tool is for educational purposes only. Unauthorized use may violate service policies or laws.")

def print_banner():
    banner = """
                                    ╔═════════════════════════════════════╗
                                    ║       HostHunter by hansobored      ║
                                    ║ Bug & Host Checker for Inject Quota ║
                                    ╚═════════════════════════════════════╝


    Usage:
    - Enter a valid domain (e.g., cdn.udemy.com) for host checks.
    - For file scans, provide a text file with one host per line in the 'hosts' folder.
    - Vmess/Trojan checks require valid UUID/Password and path.
    - Quota bug checks test notregular-to-regular quota exploits.
    """
    console.print(Panel(banner, style="bold blue", border_style="green"))
    console.print("[bold red][WARNING] Unauthorized use of this tool for quota exploitation may violate laws or service policies. Use only with explicit permission.[/bold red]")

def check_dependencies():
    required_tools = ['dig', 'curl', 'ping']
    for tool in required_tools:
        if subprocess.run(['which', tool], capture_output=True).returncode != 0:
            console.print(f"[red][Error] {tool} is not installed![/red]")
            return False
    try:
        import requests
        import websocket
    except ImportError as e:
        console.print(f"[red][Error] Python library {str(e).split()[-1]} is not installed! Run 'pip install {str(e).split()[-1]}'[/red]")
        return False
    return True

def validate_host(host):
    if not isinstance(host, str):
        return False
    sanitized_host = re.sub(r'[^\w.-]', '', host)
    if sanitized_host != host:
        logging.warning(f"Invalid characters detected in host: {host}")
        return False
    return bool(re.match(r'^[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', host))

def validate_uuid(uuid):
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, uuid))

@lru_cache(maxsize=128)
def get_host_ips(host):
    logging.info(f"Resolving IPs for host: {host}")
    try:
        cmd = ['dig', '+short', shlex.quote(host)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        ips = [ip.strip() for ip in result.stdout.splitlines() if re.match(r'^\d+\.\d+\.\d+\.\d+$', ip.strip())]
        logging.info(f"Resolved IPs for {host}: {ips}")
        return ips if ips else ["N/A"]
    except Exception as e:
        logging.error(f"Failed to resolve IPs for {host}: {str(e)}")
        return ["N/A"]

def check_host(host, port=443, timeout=10):
    logging.info(f"Checking host: {host} on port: {port} with timeout: {timeout}")
    results = []
    ips = get_host_ips(host)
    for ip in ips:
        if ip == "N/A":
            logging.error(f"Host {host} failed to resolve IP")
            return "red", f"[Error] {host} (IP: N/A) failed to resolve."
        try:
            start_time = time.time()
            protocol = 'https' if port == 443 else 'http'
            cmd = ['curl', '-I', f'{protocol}://{host}:{port}' if port != 443 else f'https://{host}', '--resolve', f'{host}:{port}:{ip}', '--connect-timeout', str(timeout)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            response_time = (time.time() - start_time) * 1000  # ms
            first_line = result.stdout.splitlines()[0]
            logging.info(f"Host {host} (IP: {ip}, Port: {port}) returned: {first_line}")
            if '200' in first_line:
                results.append((response_time, f"[200 OK] {host} (IP: {ip}, Port: {port}, Response: {response_time:.2f} ms) is active!"))
            elif '301' in first_line or '302' in first_line:
                results.append((response_time, f"[Redirect] {host} (IP: {ip}, Port: {port}, Response: {response_time:.2f} ms) may be usable."))
            else:
                results.append((float('inf'), f"[Failed] {host} (IP: {ip}, Port: {port}) returned {first_line}"))
        except subprocess.TimeoutExpired:
            logging.warning(f"Host {host} (IP: {ip}, Port: {port}) timed out")
            results.append((float('inf'), f"[Timeout] {host} (IP: {ip}, Port: {port}) took too long to respond."))
        except Exception as e:
            logging.error(f"Host {host} (IP: {ip}, Port: {port}) failed: {str(e)}")
            results.append((float('inf'), f"[Error] {host} (IP: {ip}, Port: {port}) failed: {str(e)}"))
    
    results.sort(key=lambda x: x[0])
    if results:
        color = "green" if "200 OK" in results[0][1] else "yellow" if "Redirect" in results[0][1] else "red"
        return color, "\n".join([r[1] for r in results])
    logging.error(f"No valid responses for {host} on port {port}")
    return "red", f"[Error] {host} (IP: N/A, Port: {port}) no valid responses."

def check_ping(host, timeout=10):
    logging.info(f"Pinging host: {host}")
    ip = get_host_ips(host)[0]
    if ip == "N/A":
        logging.error(f"Host {host} failed to resolve for ping")
        return "red", f"[Error] {host} (IP: N/A) failed to resolve."
    try:
        cmd = ['ping', '-c', '4', shlex.quote(ip)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            avg_latency = re.search(r'rtt min/avg/max/mdev = [\d.]+/([\d.]+)/', result.stdout)
            latency = avg_latency.group(1) if avg_latency else "N/A"
            logging.info(f"Ping to {host} (IP: {ip}) successful, latency: {latency} ms")
            return "green", f"[Ping OK] {host} (IP: {ip}) latency: {latency} ms"
        else:
            color, message = check_host(host, timeout=timeout)
            logging.warning(f"Ping to {host} (IP: {ip}) failed, falling back to HTTPS test")
            return "yellow", f"[Ping Unreachable] {host} (IP: {ip}) may block ICMP.\nHTTPS Test:\n{message}"
    except subprocess.TimeoutExpired:
        color, message = check_host(host, timeout=timeout)
        logging.warning(f"Ping to {host} (IP: {ip}) timed out, falling back to HTTPS test")
        return "yellow", f"[Timeout] {host} (IP: {ip}) took too long to respond.\nHTTPS Test:\n{message}"
    except Exception as e:
        logging.error(f"Ping to {host} (IP: {ip}) failed: {str(e)}")
        return "red", f"[Error] {host} (IP: {ip}) failed: {str(e)}"

def check_vmess_trojan(host, port=80, path='/', protocol='vmess', uuid_or_password='', use_tls=False, timeout=5):
    logging.info(f"Checking {protocol} on {host}:{port}{path} (TLS: {use_tls})")
    if protocol == 'vmess' and not validate_uuid(uuid_or_password):
        logging.error(f"Invalid UUID format for {host}")
        return "red", f"[Error] Invalid UUID format for {host}."
    if protocol == 'trojan' and len(uuid_or_password) < 8:
        logging.error(f"Trojan password too short for {host}")
        return "red", f"[Error] Trojan password must be at least 8 characters for {host}."
    
    try:
        ws_protocol = 'wss' if use_tls else 'ws'
        ws_url = f"{ws_protocol}://{host}:{port}{path}"
        headers = {}
        if protocol == 'vmess':
            headers['Sec-WebSocket-Protocol'] = f'v2ray.vmess.{uuid_or_password}'
        elif protocol == 'trojan':
            headers['Trojan-Password'] = uuid_or_password
        ws = websocket.WebSocket()
        ws.connect(ws_url, header=headers, timeout=timeout)
        ws.send("PING")
        response = ws.recv()
        ws.close()
        if protocol == 'vmess':
            try:
                json.loads(response)
                logging.info(f"Vmess connection to {host}:{port}{path} successful, valid JSON response")
                return "green", f"[VMESS OK] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) is reachable with valid JSON response."
            except json.JSONDecodeError:
                logging.warning(f"Vmess connection to {host}:{port}{path} received non-JSON response")
                return "yellow", f"[VMESS Warning] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) connected but received non-JSON response."
        else:
            if response:
                logging.info(f"Trojan connection to {host}:{port}{path} successful, response: {response}")
                return "green", f"[TROJAN OK] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) is reachable."
            else:
                logging.warning(f"Trojan connection to {host}:{port}{path} received empty response")
                return "yellow", f"[TROJAN Warning] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) connected but received empty response."
    except websocket.WebSocketException as e:
        logging.error(f"{protocol} to {host}:{port}{path} failed: {str(e)}")
        return "red", f"[{protocol.upper()} Error] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) failed: {str(e)}"
    except Exception as e:
        logging.error(f"{protocol} to {host}:{port}{path} failed: {str(e)}")
        return "red", f"[{protocol.upper()} Error] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) failed: {str(e)}"

def check_quota_bug(host, port=443, timeout=10):
    logging.info(f"Checking quota bug on {host}:{port}")
    try:
        headers = {
            'Host': 'www.ruangguru.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Connection': 'close'
        }
        url = f"https://{host}:{port}" if port == 443 else f"http://{host}:{port}"
        response = requests.get(url, headers=headers, timeout=timeout)
        logging.info(f"Quota bug check on {host}:{port} returned status: {response.status_code}")
        if (response.status_code == 200 and 
            'ruangguru' in response.text.lower() and 
            'X-Ruangguru' in response.headers):
            return "green", f"[Quota Bug OK] {host} (Port: {port}) allows access with edukasi header, contains expected content, and valid header!"
        elif response.status_code == 200:
            return "yellow", f"[Quota Bug Partial] {host} (Port: {port}) returned 200 but missing expected content or header."
        else:
            return "yellow", f"[Quota Bug Failed] {host} (Port: {port}) returned {response.status_code}."
    except requests.RequestException as e:
        logging.error(f"Quota bug check on {host}:{port} failed: {str(e)}")
        return "red", f"[Quota Bug Error] {host} (Port: {port}) failed: {str(e)}"

def scan_hosts_from_file(file_path, timeout=10):
    logging.info(f"Scanning hosts from file: {file_path}")
    # Ensure file is read from hosts directory
    file_path = os.path.join("hosts", file_path)
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} not found")
        console.print(f"[red][Error] File {file_path} not found![/red]")
        return []
    results = []
    with open(file_path, 'r') as f:
        hosts = [line.strip() for line in f if line.strip() and validate_host(line.strip())]
    if not hosts:
        logging.warning(f"File {file_path} contains no valid hosts")
        console.print(f"[red][Error] File {file_path} contains no valid hosts![/red]")
        return []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(check_host, host, 443, timeout) for host in hosts]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                logging.error(f"Host check failed during parallel scan: {str(e)}")
                results.append(("red", f"[Error] Host check failed: {str(e)}"))
    
    for color, message in results:
        logging.info(f"Scan result: {message}")
    return results

def save_results(results):
    # Create results directory if it doesn't exist
    os.makedirs("results", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join("results", f"hosthunter_results_{timestamp}.txt")
    with open(file_path, 'w') as f:
        for _, message in results:
            f.write(message + '\n')
    logging.info(f"Results saved to {file_path}")
    console.print(f"[green][Success] Results saved to {file_path}[/green]")

def generate_response_time_chart(results):
    logging.info("Generating optimized ASCII response time chart")
    labels = []
    data = []
    for _, message in results:
        host = message.split('] ')[1].split(' ')[0]
        match = re.search(r'Response: ([\d.]+) ms', message)
        if match:
            labels.append(host)
            data.append(float(match.group(1)))
    if not data:
        logging.warning("No valid response times for chart")
        console.print("[red][Error] No valid response times to display![/red]")
        return False

    try:
        max_bar_length = 50
        scale_factor = 10
        max_response = max(data, default=1)
        max_label_length = max(len(label) for label in labels)
        
        console.print("[bold green]┌" + "─" * (max_label_length + max_bar_length + 15) + "┐[/bold green]")
        console.print(f"[bold green]│ Response Time Chart (1 █ = 10 ms, Max: {max_response:.2f} ms) │[/bold green]")
        console.print("[bold green]├" + "─" * (max_label_length + max_bar_length + 15) + "┤[/bold green]")
        
        colors = ['red', 'blue', 'green', 'yellow', 'magenta']
        for i, (label, response_time) in enumerate(zip(labels, data)):
            bar_length = int(response_time / scale_factor)
            if bar_length > max_bar_length:
                bar_length = max_bar_length
            bar = '█' * bar_length
            console.print(f"[bold green]│[/bold green] [bold]{label:<{max_label_length}}[/bold] | [{colors[i % len(colors)]}]{bar:<{max_bar_length}}[/] {response_time:.2f} ms [bold green]│[/bold green]")
        
        console.print("[bold green]└" + "─" * (max_label_length + max_bar_length + 15) + "┘[/bold green]")
        console.print("[bold cyan]Scale: █ = 10 ms[/bold cyan]")
        
        logging.info("Optimized ASCII chart displayed successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to generate ASCII chart: {str(e)}")
        console.print(f"[red][Error] Failed to generate ASCII chart: {str(e)}[/red]")
        return False

def main_menu():
    setup_logging()
    if not check_dependencies():
        console.print("[red][Exit] Please install missing dependencies and try again.[/red]")
        return
    results = []
    while True:
        console.clear()
        print_banner()
        console.print(Panel("1. Check Single Host\n2. Check Ping\n3. Scan Hosts from File\n4. Save Results\n5. Show Response Time Chart\n6. Check Vmess/Trojan\n7. Check Quota Bug\n8. Exit", title="Menu", style="cyan"))
        choice = Prompt.ask("[bold cyan]Select an option[/bold cyan]", choices=["1", "2", "3", "4", "5", "6", "7", "8"])

        if choice in ["1", "2", "3", "6", "7"]:
            timeout = Prompt.ask("[bold cyan]Enter timeout second default:[/bold cyan]", default="10")
            if not timeout.isdigit() or int(timeout) <= 0:
                console.print("[red][Error] Timeout must be a positive integer![/red]")
                timeout = 10
            else:
                timeout = int(timeout)

        if choice == "1":
            host = Prompt.ask("[bold cyan]Enter host (e.g., cdn.udemy.com)[/bold cyan]")
            port = Prompt.ask("[bold cyan]Enter port default:[/bold cyan]", default="443")
            if validate_host(host) and port.isdigit() and int(port) > 0:
                color, message = check_host(host, int(port), timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print("[red][Error] Invalid host or port format! Port must be a positive integer.[/red]")

        elif choice == "2":
            host = Prompt.ask("[bold cyan]Enter host to ping (e.g., cdn.udemy.com)[/bold cyan]")
            if validate_host(host):
                color, message = check_ping(host, timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print("[red][Error] Invalid host format![/red]")

        elif choice == "3":
            file_path = Prompt.ask("[bold cyan]Enter host file name in hosts folder (e.g., hosts.txt)[/bold cyan]")
            file_path = os.path.join("hosts", file_path)
            file_path = os.path.abspath(file_path)
            if os.path.exists(file_path):
                results.extend(scan_hosts_from_file(file_path, timeout))
                if results:
                    table = Table(title="Scan Results")
                    table.add_column("Host", style="cyan")
                    table.add_column("Status", style="green")
                    for color, message in results:
                        host = message.split('] ')[1].split(' ')[0]
                        status = message.split('] ')[1]
                        table.add_row(host, f"[{color}]{status}[/{color}]")
                    console.print(table)
            else:
                console.print(f"[red][Error] File {file_path} not found![/red]")

        elif choice == "4":
            if results:
                save_results(results)
            else:
                console.print("[red][Error] No results to save![/red]")

        elif choice == "5":
            if results:
                generate_response_time_chart(results)
            else:
                console.print("[red][Error] No results to visualize![/red]")

        elif choice == "6":
            host = Prompt.ask("[bold cyan]Enter host for Vmess/Trojan[/bold cyan]")
            port = Prompt.ask("[bold cyan]Enter port default[/bold cyan]", default="443")
            path = Prompt.ask("[bold cyan]Enter WebSocket path[/bold cyan]")
            protocol = Prompt.ask("[bold cyan]Enter protocol[/bold cyan]", choices=["vmess", "trojan"])
            uuid_or_password = Prompt.ask("[bold cyan]Enter UUID (for Vmess) or Password (for Trojan)[/bold cyan]")
            use_tls = Prompt.ask("[bold cyan]Use TLS?[/bold cyan]", choices=["yes", "no"]) == "yes"
            if validate_host(host) and port.isdigit() and int(port) > 0:
                color, message = check_vmess_trojan(host, int(port), path, protocol, uuid_or_password, use_tls, timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print("[red][Error] Invalid host or port format! Port must be a positive integer.[/red]")

        elif choice == "7":
            host = Prompt.ask("[bold cyan]Enter host for quota bug check (e.g., www.ruangguru.com)[/bold cyan]")
            port = Prompt.ask("[bold cyan]Enter port default:[/bold cyan]", default="443")
            if validate_host(host) and port.isdigit() and int(port) > 0:
                color, message = check_quota_bug(host, int(port), timeout)
                console.print(f"[{color}]{message}[/{color}]")
                results.append((color, message))
            else:
                console.print("[red][Error] Invalid host or port format! Port must be a positive integer.[/red]")

        elif choice == "8":
            console.print("[bold green]Thank you for using HostHunter by hansobored![/bold green]")
            break

        Prompt.ask("[bold cyan]Press Enter to continue...[/bold cyan]")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        logging.info("Program terminated by user")
        console.print("\n[red][Exit] Program terminated by user.[/red]")