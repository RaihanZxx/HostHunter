"""file_handler.py - Handles file-based operations for HostHunter.

This module provides functionalities for scanning a list of hosts from a specified
file and saving the results of host checks into various output formats (TXT, JSON, CSV).
It leverages concurrent execution for efficient host scanning."""

import logging
import os
import datetime
from concurrent.futures import ThreadPoolExecutor
from rich.console import Console
import json
import csv
import re

# Internal module imports
from src import utils
from src import host_checker
from src.utils import COLOR_ERROR, COLOR_SECONDARY

console = Console()


def scan_hosts_from_file(file_path, timeout=10, max_workers=10):
    """
    Scans a list of hosts from a given file concurrently.

    Reads hostnames from the specified file, validates them, and then
    uses a ThreadPoolExecutor to check each host's status concurrently.

    Args:
        file_path (str): The absolute path to the file containing hosts (one host per line).
        timeout (int, optional): The maximum time in seconds to wait for a host check. Defaults to 10.
        max_workers (int, optional): The maximum number of threads to use for concurrent checks. Defaults to 10.

    Returns:
        list: A list of tuples, where each tuple contains (color, message)
              representing the result of each host check. Returns an empty list
              if the file is not found, contains no valid hosts, or if an error occurs.
    """
    # file_path is now expected to be the full path from cli.py, so remove os.path.join("data/hosts", file_path)
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} not found")
        console.print(f"[{COLOR_ERROR}][Error] File {file_path} not found![/]")
        return []

    results = []
    # Read hosts from the file, stripping whitespace and validating each host
    with open(file_path, "r") as f:
        hosts = [
            line.strip()
            for line in f
            if line.strip() and utils.validate_host(line.strip())
        ]

    if not hosts:
        logging.warning(f"File {file_path} contains no valid hosts")
        console.print(
            f"[{COLOR_ERROR}][Error] File {file_path} contains no valid hosts![/]")
        return []

    # Use ThreadPoolExecutor for concurrent host checking
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit check_host tasks for each host
        futures = [
            executor.submit(host_checker.check_host, host, 443, timeout)
            for host in hosts
        ]
        # Collect results as they complete
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                logging.error(f"Host check failed during parallel scan: {str(e)}")
                results.append(("red", f"[Error] Host check failed: {str(e)}"))

    # Sort results by response time (fastest to slowest) - extract ms from message
    def extract_response_time(result):
        color, message = result
        # Look for response time in the message (after "Response: X.XX ms")
        match = re.search(r"Response: ([\d.]+) ms", message)
        if match:
            return float(match.group(1))
        else:
            # If no response time found (e.g. for error messages), assign a high value to sort them last
            return float('inf')

    results.sort(key=extract_response_time)

    return results


def save_results(results, results_dir, output_format="txt"):
    """
    Saves the host check results to a file in the specified format.

    Creates the results directory if it doesn't exist and saves the
    provided results list into a timestamped file. Supports TXT, JSON, and CSV formats.

    Args:
        results (list): A list of tuples, where each tuple contains (color, message)
                        representing the result of each host check.
        results_dir (str): The directory where the results file will be saved.
        output_format (str, optional): The desired output format ('txt', 'json', 'csv').
                                       Defaults to 'txt'.
    """
    os.makedirs(results_dir, exist_ok=True)  # Ensure the results directory exists
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
            # This regex matches the expected output format from host_checker.check_host
            match = re.match(
                r"\\[(.*?)\\] (.*?) \\(IP: (.*?), Port: (.*?), Response: (.*?) ms\\)",
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
                # Fallback for messages that don't match the regex (e.g., error messages)
                json_results.append({"color": color, "raw_message": message})
        with open(file_path, "w") as f:
            json.dump(json_results, f, indent=4)  # Save as pretty-printed JSON
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
                # Attempt to parse host and status from message for structured CSV
                match = re.match(
                    r"\\[(.*?)\\] (.*?) \\(IP: (.*?), Port: (.*?), Response: (.*?) ms\\)",
                    message,
                )
                if match:
                    status_type, host, ip, port, response_time = match.groups()
                    writer.writerow(
                        [color, status_type, host, ip, port, response_time, message]
                    )
                else:
                    # Fallback for messages that don't match the regex
                    writer.writerow(
                        [color, "N/A", "N/A", "N/A", "N/A", "N/A", message]
                    )
    else:
        logging.error(f"Unsupported output format: {output_format}")
        console.print(
            f"[{COLOR_ERROR}][Error] Unsupported output format: {output_format}. Results not saved.[/]"
        )
        return

    logging.info(f"Results saved to {file_path}")
    console.print(f"[{COLOR_SECONDARY}][Success] Results saved to {file_path}[/]")
