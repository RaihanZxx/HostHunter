"""
host_checker.py - Functions for performing network host checks (pure-Python).

This module provides core functionalities for HostHunter without relying on
external CLI tools. It resolves hostnames to IP addresses using the socket
module, performs HTTP/HTTPS reachability checks with the requests library,
and estimates reachability latency via TCP connect timing (as a ping-like
check) to avoid invoking system commands.
"""

import logging
import socket
import re
import time
from functools import lru_cache

import requests

# Local import to reuse existing validation
try:
    import utils  # when imported from tests (sys.path points to src)
except Exception:  # pragma: no cover - fallback for package import contexts
    try:
        from src import utils as utils  # type: ignore
    except Exception:  # pragma: no cover
        utils = None


@lru_cache(maxsize=128)
def get_host_ips(host):
    """
    Resolve a hostname to IPv4 addresses using the socket module.

    Args:
        host (str): Hostname to resolve.

    Returns:
        list[str]: Unique IPv4 addresses for the host or ["N/A"] on failure.
    """
    try:
        if utils and not utils.validate_host(host):
            logging.error(f"Invalid host provided: {host}")
            return ["N/A"]

        infos = socket.getaddrinfo(host, None, family=socket.AF_INET)
        seen = set()
        ips = []
        for info in infos:
            ip = info[4][0]
            if ip not in seen and re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", ip):
                seen.add(ip)
                ips.append(ip)
        logging.debug(f"Resolved IPs for {host}: {ips}")
        return ips if ips else ["N/A"]
    except socket.gaierror as e:
        logging.error(f"DNS resolution failed for {host}: {e}")
        return ["N/A"]
    except Exception as e:
        logging.error(f"Unexpected error resolving IPs for {host}: {e}")
        return ["N/A"]

def check_host(host, port=443, timeout=10):
    """
    Check the availability of a host on a specific port using requests.

    For each resolved IP, attempt an HTTP HEAD request to that IP with the
    Host header set to the original hostname. HTTPS certificate verification
    is disabled when connecting directly to IPs to avoid SNI/hostname
    mismatch errors during scanning.

    Returns:
        tuple[str, str]: (color, message)
    """
    results = []
    ips = get_host_ips(host)

    for ip in ips:
        if ip == "N/A":
            logging.error(f"Host {host} failed to resolve IP")
            return "red", f"[Error] {host} (IP: N/A) failed to resolve."
        try:
            start_time = time.time()
            scheme = "https" if port == 443 else "http"
            url = f"{scheme}://{ip}:{port}"
            headers = {"Host": host}
            # Disable redirects to match previous behavior
            resp = requests.head(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
                verify=False if scheme == "https" else True,
            )
            response_time = (time.time() - start_time) * 1000

            status = resp.status_code
            if status == 200:
                results.append(
                    (
                        response_time,
                        f"[200 OK] {host} (IP: {ip}, Port: {port}, Response: {response_time:.2f} ms) is active!",
                    )
                )
            elif status in (301, 302):
                results.append(
                    (
                        response_time,
                        f"[Redirect] {host} (IP: {ip}, Port: {port}, Response: {response_time:.2f} ms) may be usable.",
                    )
                )
            else:
                results.append(
                    (
                        float("inf"),
                        f"[Failed] {host} (IP: {ip}, Port: {port}) returned HTTP {status}",
                    )
                )
        except requests.exceptions.Timeout:
            logging.warning(f"Host {host} (IP: {ip}, Port: {port}) timed out")
            results.append(
                (
                    float("inf"),
                    f"[Timeout] {host} (IP: {ip}, Port: {port}) took too long to respond.",
                )
            )
        except requests.RequestException as e:
            logging.error(f"Request to {host} (IP: {ip}, Port: {port}) failed: {e}")
            results.append(
                (
                    float("inf"),
                    f"[Failed] {host} (IP: {ip}, Port: {port}) request error: {e}",
                )
            )
        except Exception as e:
            logging.error(f"Unexpected error checking {host} (IP: {ip}, Port: {port}): {e}")
            results.append(
                (
                    float("inf"),
                    f"[Error] {host} (IP: {ip}, Port: {port}) failed: {e}",
                )
            )

    results.sort(key=lambda x: x[0])
    if results:
        color = (
            "green" if "200 OK" in results[0][1] else "yellow" if "Redirect" in results[0][1] else "red"
        )
        return color, "\n".join([r[1] for r in results])
    logging.error(f"No valid responses for {host} on port {port}")
    return "red", f"[Error] {host} (IP: N/A, Port: {port}) no valid responses."

def check_ping(host, timeout=10):
    """
    Estimate reachability/latency by timing TCP connect attempts.

    If connection attempts fail or time out, fall back to HTTPS check using
    check_host to provide diagnostic information.
    """
    ip = get_host_ips(host)[0]
    if ip == "N/A":
        logging.error(f"Host {host} failed to resolve for ping")
        return "red", f"[Error] {host} (IP: N/A) failed to resolve."
    try:
        samples = []
        port = 443
        for _ in range(4):
            start = time.time()
            # create_connection returns after handshake at TCP level
            with socket.create_connection((ip, port), timeout=timeout):
                pass
            samples.append((time.time() - start) * 1000)
        avg = sum(samples) / len(samples) if samples else 0.0
        return "spring_green2", f"[Ping OK] {host} (IP: {ip}) latency: {avg:.2f} ms"
    except socket.timeout:
        color, message = check_host(host, timeout=timeout)
        logging.warning(f"TCP ping to {host} (IP: {ip}) timed out, falling back to HTTPS test")
        return (
            "orange3",
            f"[Timeout] {host} (IP: {ip}) took too long to respond.\nHTTPS Test:\n{message}",
        )
    except OSError as e:
        color, message = check_host(host, timeout=timeout)
        logging.warning(
            f"TCP ping to {host} (IP: {ip}) failed with error: {e}. Falling back to HTTPS test."
        )
        return (
            "yellow",
            f"[Ping Unreachable] {host} (IP: {ip}) may block ICMP/TCP. Error: {e}\nHTTPS Test:\n{message}",
        )
    except Exception as e:
        logging.error(f"TCP ping to {host} (IP: {ip}) failed: {e}")
        return "red", f"[Error] {host} (IP: {ip}) failed: {e}"
