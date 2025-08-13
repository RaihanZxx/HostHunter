import logging
import requests
import websocket
import json

from . import utils

# Define a dictionary to register special checks
# Each entry will contain:
#   - 'function': The actual function to call
#   - 'prompts': A list of dictionaries, each describing a prompt needed for the function
#                'name': The variable name for the prompt's result
#                'text': The prompt text for the user
#                'default': Default value (optional)
#                'choices': List of choices (optional)
#                'type': 'str', 'int', 'bool' (for Prompt.ask)
SPECIAL_CHECKS = {}


def register_check(name, function, prompts):
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
        ws_protocol = "wss" if use_tls else "ws"
        ws_url = f"{ws_protocol}://{host}:{port}{path}"
        headers = {}
        if protocol == "vmess":
            headers["Sec-WebSocket-Protocol"] = f"v2ray.vmess.{uuid_or_password}"
        elif protocol == "trojan":
            headers["Trojan-Password"] = uuid_or_password
        ws = websocket.WebSocket()
        ws.connect(ws_url, header=headers, timeout=timeout)
        ws.send("PING")
        response = ws.recv()
        ws.close()
        if protocol == "vmess":
            try:
                json.loads(response)
                
                return (
                    "green",
                    f"[VMESS OK] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) is reachable with valid JSON response.",
                )
            except json.JSONDecodeError:
                
                return (
                    "yellow",
                    f"[VMESS Warning] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) connected but received non-JSON response.",
                )
        else:
            if response:
                
                return (
                    "green",
                    f"[TROJAN OK] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) is reachable.",
                )
            else:
                
                return (
                    "yellow",
                    f"[TROJAN Warning] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) connected but received empty response.",
                )
    except websocket.WebSocketException as e:
        logging.error(f"{protocol} to {host}:{port}{path} failed: {str(e)}")
        return (
            "red",
            f"[{protocol.upper()} Error] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) failed: {str(e)}",
        )
    except Exception as e:
        logging.error(f"{protocol} to {host}:{port}{path} failed: {str(e)}")
        return (
            "red",
            f"[{protocol.upper()} Error] {host} (Port: {port}, Path: {path}, TLS: {use_tls}) failed: {str(e)}",
        )


def check_quota_bug(host, port=443, timeout=10):
    
    try:
        headers = {
            "Host": "www.ruangguru.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Connection": "close",
        }
        url = f"https://{host}:{port}" if port == 443 else f"http://{host}:{port}"
        response = requests.get(url, headers=headers, timeout=timeout)
        
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
            return (
                "yellow",
                f"[Quota Bug Partial] {host} (Port: {port}) returned 200 but missing expected content or header.",
            )
        else:
            return (
                "yellow",
                f"[Quota Bug Failed] {host} (Port: {port}) returned {response.status_code}.",
            )
    except requests.RequestException as e:
        logging.error(f"Quota bug check on {host}:{port} failed: {str(e)}")
        return "red", f"[Quota Bug Error] {host} (Port: {port}) failed: {str(e)}"


# Register the special checks
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
