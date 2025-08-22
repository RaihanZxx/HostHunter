"""
special_checks.py - Defines and registers specialized network checks for HostHunter.

This module contains functions for performing advanced network checks beyond
basic host availability, such as Vmess/Trojan protocol checks and specific
quota bug vulnerability checks. It also provides a mechanism to register
these checks dynamically for use in the main CLI.
"""

import logging
import requests
import websocket
import json

from . import utils # Relative import for internal utility functions

# SPECIAL_CHECKS dictionary: A registry for all special checks.
# Each entry maps a check name (string) to a dictionary containing:
#   - 'function': The Python function that implements the check logic.
#   - 'prompts': A list of dictionaries, each describing a user input prompt
#                required by the check function. Each prompt dictionary includes:
#                'name': The argument name for the function.
#                'text': The user-facing prompt message.
#                'default': Optional default value for the prompt.
#                'choices': Optional list of valid choices for the prompt.
#                'type': Expected input type ('str', 'int', 'bool').
SPECIAL_CHECKS = {}


def register_check(name, function, prompts):
    """
    Registers a new special check with the HostHunter system.

    This function adds a new entry to the `SPECIAL_CHECKS` dictionary, making
    the custom check available for selection in the main CLI menu.

    Args:
        name (str): A user-friendly name for the special check (e.g., "Vmess/Trojan").
        function (callable): The Python function that implements the logic for this check.
        prompts (list): A list of dictionaries, each defining a prompt for user input
                        required by the `function`.
    """
    SPECIAL_CHECKS[name] = {"function": function, "prompts": prompts}


def check_vmess_trojan(
    host,
    port=80,
    path="/",
    protocol="vmess",
    uuid_or_password="",
    use_tls=False,
    timeout=5,
):
    """
    Performs a Vmess or Trojan protocol check using WebSocket.

    Attempts to establish a WebSocket connection to the specified host and port
    with protocol-specific headers (Vmess UUID or Trojan password) to verify
    the service's reachability and basic functionality.

    Args:
        host (str): The target hostname or IP address.
        port (int, optional): The port number for the WebSocket connection. Defaults to 80.
        path (str, optional): The WebSocket path. Defaults to "/".
        protocol (str, optional): The protocol to check ("vmess" or "trojan"). Defaults to "vmess".
        uuid_or_password (str, optional): The UUID for Vmess or password for Trojan. Defaults to "".
        use_tls (bool, optional): Whether to use TLS (wss://) for the connection. Defaults to False.
        timeout (int, optional): Connection timeout in seconds. Defaults to 5.

    Returns:
        tuple: A tuple containing (color, message) indicating the check result.
    """
    # Validate UUID format for Vmess or password length for Trojan
    if protocol == "vmess" and not utils.validate_uuid(uuid_or_password):
        logging.error(f"Invalid UUID format for {host}")
        return "red", f"[Error] Invalid UUID format for {host}."
    if protocol == "trojan" and len(uuid_or_password) < 8:
        logging.error(f"Trojan password too short for {host}")
        return (
            "red",
            f"[Error] Trojan password must be at least 8 characters for {host}.",
        )

    try:
        # Construct WebSocket URL (ws:// or wss://)
        ws_protocol = "wss" if use_tls else "ws"
        ws_url = f"{ws_protocol}://{host}:{port}{path}"
        headers = {}
        # Set protocol-specific headers
        if protocol == "vmess":
            headers["Sec-WebSocket-Protocol"] = f"v2ray.vmess.{uuid_or_password}"
        elif protocol == "trojan":
            headers["Trojan-Password"] = uuid_or_password

        ws = websocket.WebSocket()
        ws.connect(ws_url, header=headers, timeout=timeout) # Establish WebSocket connection
        ws.send("PING") # Send a PING frame
        response = ws.recv() # Receive response
        ws.close() # Close the connection

        if protocol == "vmess":
            try:
                json.loads(response) # Attempt to parse response as JSON for Vmess
                return (
                    "green",
                    f"[VMESS OK] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) is reachable with valid JSON response.",
                )
            except json.JSONDecodeError:
                # Vmess connected but response was not valid JSON
                return (
                    "yellow",
                    f"[VMESS Warning] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) connected but received non-JSON response.",
                )
        else: # Trojan protocol
            if response:
                # Trojan connected and received a non-empty response
                return (
                    "green",
                    f"[TROJAN OK] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) is reachable.",
                )
            else:
                # Trojan connected but received an empty response
                return (
                    "yellow",
                    f"[TROJAN Warning] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) connected but received empty response.",
                )
    except websocket.WebSocketException as e:
        # Handle WebSocket-specific errors (e.g., connection refused, handshake failure)
        logging.error(f"{protocol} to {host}:{port}{path} failed: {str(e)}")
        return (
            "red",
            f"[{protocol.upper()} Error] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) failed: {str(e)}",
        )
    except Exception as e: # Catch any other unexpected errors
        logging.error(f"{protocol} to {host}:{port}{path} failed: {str(e)}")
        return (
            "red",
            f"[{protocol.upper()} Error] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) failed: {str(e)}",
        )


def check_quota_bug(host, port=443, timeout=10):
    """
    Checks for a specific "quota bug" vulnerability on a given host.

    This check simulates a request with specific headers (e.g., "Host: www.ruangguru.com")
    and analyzes the response status code, content, and headers to determine
    if a known quota bypass vulnerability might be present.

    Args:
        host (str): The target hostname or IP address.
        port (int, optional): The port number for the HTTP/HTTPS request. Defaults to 443.
        timeout (int, optional): Request timeout in seconds. Defaults to 10.

    Returns:
        tuple: A tuple containing (color, message) indicating the check result.
    """
    try:
        # Define custom headers to simulate a specific request
        headers = {
            "Host": "www.ruangguru.com", # Specific Host header for the bug check
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Connection": "close",
        }
        # Construct the URL (http:// or https://)
        url = f"https://{host}:{port}" if port == 443 else f"http://{host}:{port}"
        # Make the HTTP GET request
        response = requests.get(url, headers=headers, timeout=timeout)

        # Check for specific indicators of the quota bug
        if (
            response.status_code == 200
            and "ruangguru" in response.text.lower()
            and "X-Ruangguru" in response.headers
        ):
            return (
                "green",
                f"[Quota Bug OK] {host} (Port: {port}) allows access with edukasi header, contains expected content, and valid header!",
            )
        elif response.status_code == 200:
            # Connected, but missing expected content or header
            return (
                "yellow",
                f"[Quota Bug Partial] {host} (Port: {port}) returned 200 but missing expected content or header.",
            )
        else:
            # Non-200 status code
            return (
                "yellow",
                f"[Quota Bug Failed] {host} (Port: {port}) returned {response.status_code}.",
            )
    except requests.RequestException as e:
        # Handle request-specific errors (e.g., connection errors, DNS resolution failures)!
        logging.error(f"Quota bug check on {host}:{port} failed: {str(e)}")
        return "red", f"[Quota Bug Error] {host} (Port: {port}) failed: {str(e)}"


# --- Register the special checks for use in the CLI ---

# Register Vmess/Trojan check
register_check(
    "Vmess/Trojan",
    check_vmess_trojan,
    [
        {"name": "host", "text": "Enter host for Vmess/Trojan", "type": "str"},
        {"name": "port", "text": "Enter port", "default": "443", "type": "int"},
        {"name": "path", "text": "Enter WebSocket path", "default": "/", "type": "str"},
        {
            "name": "protocol",
            "text": "Enter protocol",
            "choices": ["vmess", "trojan"],
            "type": "str",
        },
        {
            "name": "uuid_or_password",
            "text": "Enter UUID (for Vmess) or Password (for Trojan)",
            "type": "str",
        },
        {
            "name": "use_tls",
            "text": "Use TLS?",
            "choices": ["yes", "no"],
            "type": "bool",
        },
    ],
)

# Register Quota Bug check
register_check(
    "Quota Bug",
    check_quota_bug,
    [
        {
            "name": "host",
            "text": "Enter host for quota bug check (e.g., www.ruangguru.com)",
            "type": "str",
        },
        {"name": "port", "text": "Enter port", "default": "443", "type": "int"},
    ],
)
