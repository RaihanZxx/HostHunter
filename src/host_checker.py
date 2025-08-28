"""
host_checker.py - Functions for performing network host checks.

This module provides core functionalities for HostHunter, including
resolving hostnames to IP addresses, checking host availability via HTTP/HTTPS
using `curl`, and performing ICMP ping tests using `ping`.
It leverages subprocess calls to external system commands.
"""

import logging
import subprocess
import re
import time
import shlex
from functools import lru_cache


@lru_cache(maxsize=128)
def get_host_ips(host):
    """
    Resolves a hostname to its IP addresses using the 'dig' command.

    Uses `dig +short` to get A records for the given host. Results are cached
    to improve performance for repeated lookups of the same host.

    Args:
        host (str): The hostname to resolve (e.g., "example.com").

    Returns:
        list: A list of IP addresses (strings) associated with the host.
              Returns ["N/A"] if resolution fails or no valid IPs are found.
    """
    try:
        # Construct the dig command to get short IP output
        cmd = ["dig", "+short", host]
        # Execute the command, capture output, and check for errors
        logging.debug(f"Executing dig command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=True
        )
        logging.debug(f"Dig stdout for {host}:\n{result.stdout}")
        logging.debug(f"Dig stderr for {host}:\n{result.stderr}")

        # Filter and collect valid IPv4 addresses from the dig output
        ips = [
            ip.strip()
            for ip in result.stdout.splitlines()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip.strip())
        ]
        logging.debug(f"Resolved IPs for {host}: {ips}")
        return ips if ips else ["N/A"]
    except subprocess.CalledProcessError as e:
        # Log error if dig command returns a non-zero exit code
        logging.error(f"Dig command failed for {host}: {e.stderr.strip()}")
        return ["N/A"]
    except subprocess.TimeoutExpired:
        # Log error if dig command times out
        logging.error(f"Dig command timed out for {host}")
        return ["N/A"]
    except Exception as e:  # Catch any other unexpected errors during execution
        logging.error(
            f"An unexpected error occurred while resolving IPs for {host}: {str(e)}"
        )
        return ["N/A"]

def check_host(host, port=443, timeout=10):
    """
    Checks the availability of a host on a specific port using 'curl'.

    Attempts to connect to the host's resolved IP addresses. For each IP,
    it uses `curl` to perform an HTTP/HTTPS check and measures response time.
    It prioritizes successful (200 OK) responses.

    Args:
        host (str): The hostname to check.
        port (int, optional): The port number to connect to. Defaults to 443 (HTTPS).
        timeout (int, optional): The maximum time in seconds for the connection and response. Defaults to 10.

    Returns:
        tuple: A tuple containing (color, message).
               Color indicates status (green for success, yellow for redirect, red for failure).
               Message provides details about the check result.
    """
    results = []  # Stores (response_time, message) for each IP
    ips = get_host_ips(host)  # Get all resolved IPs for the host

    for ip in ips:
        if ip == "N/A":
            logging.error(f"Host {host} failed to resolve IP")
            return "red", f"[Error] {host} (IP: N/A) failed to resolve."
        try:
            start_time = time.time()
            protocol = "https" if port == 443 else "http"
            # Construct curl command:
            # -I: Head request only
            # --resolve: Force resolution of host to a specific IP, bypassing DNS cache
            # --connect-timeout: Set timeout for connection phase
            cmd = [
                "curl",
                "-I",
                f"{protocol}://{host}:{port}" if port != 443 else f"https://{host}",
                "--resolve",
                f"{host}:{port}:{ip}",
                "--connect-timeout",
                str(timeout),
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=True,  # Raise CalledProcessError for non-zero exit codes
            )
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            first_line = result.stdout.splitlines()[0] # Get the HTTP status line

            # Categorize response based on HTTP status codes
            if "200" in first_line:
                results.append(
                    (
                        response_time,
                        f"[200 OK] {host} (IP: {ip}, Port: {port}, Response: {response_time:.2f} ms) is active!",
                    )
                )
            elif "301" in first_line or "302" in first_line:
                results.append(
                    (
                        response_time,
                        f"[Redirect] {host} (IP: {ip}, Port: {port}, Response: {response_time:.2f} ms) may be usable.",
                    )
                )
            else:
                results.append(
                    (
                        float("inf"), # Assign infinite time for failures to sort them last
                        f"[Failed] {host} (IP: {ip}, Port: {port}) returned {first_line}",
                    )
                )
        except subprocess.CalledProcessError as e:
            # Log and record error if curl command fails (e.g., connection refused, host unreachable)
            logging.error(
                f"Curl command failed for {host} (IP: {ip}, Port: {port}): {e.stderr.strip()}"
            )
            results.append(
                (
                    float("inf"),
                    f"[Failed] {host} (IP: {ip}, Port: {port}) curl error: {e.stderr.strip()}",
                )
            )
        except subprocess.TimeoutExpired:
            # Log and record timeout if curl command exceeds the timeout
            logging.warning(f"Host {host} (IP: {ip}, Port: {port}) timed out")
            results.append(
                (
                    float("inf"),
                    f"[Timeout] {host} (IP: {ip}, Port: {port}) took too long to respond.",
                )
            )
        except Exception as e: # Catch any other unexpected errors
            logging.error(f"Host {host} (IP: {ip}, Port: {port}) failed: {str(e)}")
            results.append(
                (
                    float("inf"),
                    f"[Error] {host} (IP: {ip}, Port: {port}) failed: {str(e)}",
                )
            )

    # Sort results by response time to find the best/fastest response
    results.sort(key=lambda x: x[0])
    if results:
        # Determine overall color based on the best result
        color = (
            "green"
            if "200 OK" in results[0][1]
            else "yellow" if "Redirect" in results[0][1] else "red"
        )
        # Join all messages for a comprehensive output if multiple IPs were checked
        return color, "\n".join([r[1] for r in results])
    logging.error(f"No valid responses for {host} on port {port}")
    return "red", f"[Error] {host} (IP: N/A, Port: {port}) no valid responses."

def check_ping(host, timeout=10):
    """
    Performs an ICMP ping test to a host.

    If the ping fails or times out, it falls back to an HTTPS check using `check_host`
    to provide alternative diagnostic information.

    Args:
        host (str): The hostname to ping.
        timeout (int, optional): The maximum time in seconds for the ping command. Defaults to 10.

    Returns:
        tuple: A tuple containing (color, message).
               Color indicates status (spring_green2 for success, yellow/orange3 for issues).
               Message provides details about the ping result or fallback HTTPS test.
    """
    ip = get_host_ips(host)[0]  # Get the first resolved IP for ping
    if ip == "N/A":
        logging.error(f"Host {host} failed to resolve for ping")
        return "red", f"[Error] {host} (IP: N/A) failed to resolve."
    try:
        # Construct ping command: -c 4 sends 4 packets
        cmd = ["ping", "-c", "4", shlex.quote(ip)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True
        )
        # If check=True, a non-zero return code will raise CalledProcessError,
        # so this if block only executes on success (returncode == 0).
        if result.returncode == 0:
            # Extract average latency from ping output using regex
            avg_latency = re.search(
                r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", result.stdout
            )
            latency = avg_latency.group(1) if avg_latency else "N/A"
            return "spring_green2", f"[Ping OK] {host} (IP: {ip}) latency: {latency} ms"
    except subprocess.CalledProcessError as e:
        # If ping fails (e.g., host unreachable, ICMP blocked), fall back to HTTPS check
        color, message = check_host(host, timeout=timeout)
        logging.warning(
            f"Ping to {host} (IP: {ip}) failed with exit code {e.returncode}, falling back to HTTPS test. Stderr: {e.stderr.strip()}"
        )
        return (
            "yellow",
            f"[Ping Unreachable] {host} (IP: {ip}) may block ICMP. Stderr: {e.stderr.strip()}\nHTTPS Test:\n{message}",
        )
    except subprocess.TimeoutExpired:
        # If ping times out, fall back to HTTPS check
        color, message = check_host(host, timeout=timeout)
        logging.warning(
            f"Ping to {host} (IP: {ip}) timed out, falling back to HTTPS test"
        )
        return (
            "orange3",
            f"[Timeout] {host} (IP: {ip}) took too long to respond.\nHTTPS Test:\n{message}",
        )
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"Ping to {host} (IP: {ip}) failed: {str(e)}")
        return "red", f"[Error] {host} (IP: {ip}) failed: {str(e)}"
