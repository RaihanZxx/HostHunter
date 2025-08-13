import logging
import os
import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
import json
import csv
import re

# Changed relative imports to absolute imports
from src import utils
from src import host_checker
from src.utils import COLOR_ERROR, COLOR_SECONDARY

console = Console()


def scan_hosts_from_file(file_path, timeout=10, max_workers=10):
    
    # file_path is now expected to be the full path from cli.py, so remove os.path.join("data/hosts", file_path)
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} not found")
        console.print(f"[{COLOR_ERROR}][Error] File {file_path} not found![/]")
        return []
    results = []
    with open(file_path, "r") as f:
        hosts = [
            line.strip()
            for line in f
            if line.strip() and utils.validate_host(line.strip())
        ]
    if not hosts:
        logging.warning(f"File {file_path} contains no valid hosts")
        console.print(
            f"[{COLOR_ERROR}][Error] File {file_path} contains no valid hosts![/]"
        )
        return []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(host_checker.check_host, host, 443, timeout)
            for host in hosts
        ]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                logging.error(f"Host check failed during parallel scan: {str(e)}")
                results.append(("red", f"[Error] Host check failed: {str(e)}"))

    
    return results


def save_results(results, results_dir, output_format="txt"):  # Added output_format
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_format == "txt":
        file_path = os.path.join(results_dir, f"hosthunter_results_{timestamp}.txt")
        with open(file_path, "w") as f:
            for _, message in results:
                f.write(message + "\n")
    elif output_format == "json":
        file_path = os.path.join(results_dir, f"hosthunter_results_{timestamp}.json")
        json_results = []
        for color, message in results:
            # Attempt to parse host and status from message for structured JSON
            match = re.match(
                r"\\[(.*?)\\] (.*?) \(IP: (.*?), Port: (.*?), Response: (.*?) ms\)",
                message,
            )
            if match:
                status_type, host, ip, port, response_time = match.groups()
                json_results.append(
                    {
                        "color": color,
                        "status_type": status_type,
                        "host": host,
                        "ip": ip,
                        "port": port,
                        "response_time_ms": (
                            float(response_time) if response_time != "N/A" else "N/A"
                        ),
                        "raw_message": message,
                    }
                )
            else:
                # Fallback for messages that don't match the regex
                json_results.append({"color": color, "raw_message": message})
        with open(file_path, "w") as f:
            json.dump(json_results, f, indent=4)
    elif output_format == "csv":
        file_path = os.path.join(results_dir, f"hosthunter_results_{timestamp}.csv")
        with open(file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Color",
                    "Status Type",
                    "Host",
                    "IP",
                    "Port",
                    "Response Time (ms)",
                    "Raw Message",
                ]
            )  # CSV Header
            for color, message in results:
                match = re.match(
                    r"\\[(.*?)\\] (.*?) \(IP: (.*?), Port: (.*?), Response: (.*?) ms\)",
                    message,
                )
                if match:
                    status_type, host, ip, port, response_time = match.groups()
                    writer.writerow(
                        [color, status_type, host, ip, port, response_time, message]
                    )
                else:
                    writer.writerow(
                        [color, "N/A", "N/A", "N/A", "N/A", "N/A", message]
                    )  # Fallback for CSV
    else:
        logging.error(f"Unsupported output format: {output_format}")
        console.print(
            f"[{COLOR_ERROR}][Error] Unsupported output format: {output_format}. Results not saved.[/]"
        )
        return

    logging.info(f"Results saved to {file_path}")
    console.print(f"[{COLOR_SECONDARY}][Success] Results saved to {file_path}[/]")
