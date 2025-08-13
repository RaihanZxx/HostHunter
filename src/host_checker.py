import logging
import subprocess
import re
import time
import shlex
from functools import lru_cache


@lru_cache(maxsize=128)
def get_host_ips(host):
    
    try:
        cmd = ["dig", "+short", shlex.quote(host)]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=True
        )  # Added check=True
        ips = [
            ip.strip()
            for ip in result.stdout.splitlines()
            if re.match(r"^\d+\.\d+\.\d+\.\d+$", ip.strip())
        ]
        
        return ips if ips else ["N/A"]
    except subprocess.CalledProcessError as e:
        logging.error(f"Dig command failed for {host}: {e.stderr.strip()}")
        return ["N/A"]
    except subprocess.TimeoutExpired:
        logging.error(f"Dig command timed out for {host}")
        return ["N/A"]
    except Exception as e:  # Catch any other unexpected errors
        logging.error(
            f"An unexpected error occurred while resolving IPs for {host}: {str(e)}"
        )
        return ["N/A"]


def check_host(host, port=443, timeout=10):
    
    results = []
    ips = get_host_ips(host)
    for ip in ips:
        if ip == "N/A":
            logging.error(f"Host {host} failed to resolve IP")
            return "red", f"[Error] {host} (IP: N/A) failed to resolve."
        try:
            start_time = time.time()
            protocol = "https" if port == 443 else "http"
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
                check=True,  # Added check=True
            )
            response_time = (time.time() - start_time) * 1000  # ms
            first_line = result.stdout.splitlines()[0]
            
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
                        float("inf"),
                        f"[Failed] {host} (IP: {ip}, Port: {port}) returned {first_line}",
                    )
                )
        except subprocess.CalledProcessError as e:
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
            logging.warning(f"Host {host} (IP: {ip}, Port: {port}) timed out")
            results.append(
                (
                    float("inf"),
                    f"[Timeout] {host} (IP: {ip}, Port: {port}) took too long to respond.",
                )
            )
        except Exception as e:
            logging.error(f"Host {host} (IP: {ip}, Port: {port}) failed: {str(e)}")
            results.append(
                (
                    float("inf"),
                    f"[Error] {host} (IP: {ip}, Port: {port}) failed: {str(e)}",
                )
            )

    results.sort(key=lambda x: x[0])
    if results:
        color = (
            "green"
            if "200 OK" in results[0][1]
            else "yellow" if "Redirect" in results[0][1] else "red"
        )
        return color, "\n".join([r[1] for r in results])
    logging.error(f"No valid responses for {host} on port {port}")
    return "red", f"[Error] {host} (IP: N/A, Port: {port}) no valid responses."


def check_ping(host, timeout=10):
    
    ip = get_host_ips(host)[0]
    if ip == "N/A":
        logging.error(f"Host {host} failed to resolve for ping")
        return "red", f"[Error] {host} (IP: N/A) failed to resolve."
    try:
        cmd = ["ping", "-c", "4", shlex.quote(ip)]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=True
        )  # Added check=True
        if (
            result.returncode == 0
        ):  # This check is now redundant due to check=True, but keeping for clarity of original logic
            avg_latency = re.search(
                r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", result.stdout
            )
            latency = avg_latency.group(1) if avg_latency else "N/A"
            
            return "spring_green2", f"[Ping OK] {host} (IP: {ip}) latency: {latency} ms"
        # The else block for non-zero returncode is now handled by CalledProcessError
    except subprocess.CalledProcessError as e:
        color, message = check_host(host, timeout=timeout)
        logging.warning(
            f"Ping to {host} (IP: {ip}) failed with exit code {e.returncode}, falling back to HTTPS test. Stderr: {e.stderr.strip()}"
        )
        return (
            "yellow",
            f"[Ping Unreachable] {host} (IP: {ip}) may block ICMP. Stderr: {e.stderr.strip()}\nHTTPS Test:\n{message}",
        )
    except subprocess.TimeoutExpired:
        color, message = check_host(host, timeout=timeout)
        logging.warning(
            f"Ping to {host} (IP: {ip}) timed out, falling back to HTTPS test"
        )
        return (
            "orange3",
            f"[Timeout] {host} (IP: {ip}) took too long to respond.\nHTTPS Test:\n{message}",
        )
    except Exception as e:
        logging.error(f"Ping to {host} (IP: {ip}) failed: {str(e)}")
        return "red", f"[Error] {host} (IP: {ip}) failed: {str(e)}"
