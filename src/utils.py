import subprocess
import datetime
import logging
import re
import os
import configparser  # Added import
from rich.console import Console


# Rich color tags (Modern Palette)
COLOR_PRIMARY = "#77BEF0"
COLOR_SECONDARY = "#7ADAA5"
COLOR_WARNING = "#FFC900"
COLOR_YELLOW = "gold1"
COLOR_ERROR = "#D92C54"
COLOR_ACCENT = "grey70"
COLOR_HIGHLIGHT = "magenta"
COLOR_CYAN = "#8ABB6C"  
COLOR_NEW_ACCENT = "#1C6EA4"
COLOR_BANNER_PART2 = "#8C1007"

# Panel Colors
PANEL_BORDER_COLOR = "grey50"
PANEL_TEXT_COLOR = "grey82"


console = Console()


# New function to load configuration
def load_config(config_file="config.ini"):
    config = configparser.ConfigParser()
    # Set default values
    config["General"] = {
        "log_level": "INFO",
        "default_timeout": "10",
        "max_concurrent_checks": "10",
    }
    config["Paths"] = {
        "hosts_dir": "data/hosts",
        "output_dir": "output",
        "logs_dir": "output/logs",
        "results_dir": "output/results",
    }

    if os.path.exists(config_file):
        try:
            config.read(config_file)
            logging.info(f"Configuration loaded from {config_file}")
        except configparser.Error as e:
            console.print(
                f"{COLOR_ERROR}[Error] Failed to parse config file {config_file}: {e}. Using default settings."
            )
            logging.error(
                f"Failed to parse config file {config_file}: {e}. Using default settings."
            )
    else:
        console.print(
            f"{COLOR_WARNING}[Warning] Config file {config_file} not found. Using default settings."
        )
        logging.warning(f"Config file {config_file} not found. Using default settings.")

    return config


def setup_logging(config):  # Added config parameter
    log_level_str = config["General"]["log_level"].upper()
    log_level = getattr(
        logging, log_level_str, logging.INFO
    )  # Get logging level from string

    logs_dir = config["Paths"]["logs_dir"]  # Get logs directory from config
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(
        logs_dir,  # Use logs_dir from config
        f"hosthunter_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    )

    # Configure file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)  # Use log_level from config
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Configure console handler for warnings and errors
    console_handler = logging.StreamHandler()
    console_handler.setLevel(
        logging.WARNING
    )  # Only show WARNING, ERROR, CRITICAL on console
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )  # Simpler format for console
    console_handler.setFormatter(console_formatter)

    # Get the root logger and add handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)  # Set root logger level to log_level from config
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("HostHunter started")
    logging.warning(
        "This tool is for educational purposes only. Unauthorized use may violate service policies or laws."
    )


def print_banner():
    banner_part1 = """██╗░░██╗░█████╗░░██████╗████████╗  ████╗░░░░░░████╗
██║░░██║██╔══██╗██╔════╝╚══██╔══╝  ██╔═╝░░░░░░╚═██║
███████║██║░░██║╚█████╗░░░░██║░░░  ██║░░█████╗░░██║
██╔══██║██║░░██║░╚═══██╗░░░██║░░░  ██║░░╚════╝░░██║
██║░░██║╚█████╔╝██████╔╝░░░██║░░░  ████╗░░░░░░████║
╚═╝░░╚═╝░╚════╝░╚═════╝░░░░╚═╝░░░  ╚═══╝░░░░░░╚═══╝"""
    banner_part2 = """
░░██╗██╗░░██╗██╗░░  ██╗░░██╗██╗░░░██╗███╗░░██╗████████╗███████╗██████╗░
░██╔╝╚██╗██╔╝╚██╗░  ██║░░██║██║░░░██║████╗░██║╚══██╔══╝██╔════╝██╔══██╗
██╔╝░░╚███╔╝░░╚██╗  ███████║██║░░░██║██╔██╗██║░░░██║░░░█████╗░░██████╔╝
╚██╗░░██╔██╗░░██╔╝  ██╔══██║██║░░░██║██║╚████║░░░██║░░░██╔══╝░░██╔══██╗
░╚██╗██╔╝╚██╗██╔╝░  ██║░░██║╚██████╔╝██║░╚███║░░░██║░░░███████╗██║░░██║
░░╚═╝╚═╝░░╚═╝╚═╝░░  ╚═╝░░╚═╝░╚═════╝░╚═╝░░╚══╝░░░╚═╝░░░╚══════╝╚═╝░░╚═╝"""
    console.print(f"[{COLOR_NEW_ACCENT}]{banner_part1}[/]")
    console.print(f"[{COLOR_BANNER_PART2}]{banner_part2}[/]")


def check_dependencies():
    required_tools = ["dig", "curl", "ping"]
    for tool in required_tools:
        if subprocess.run(["which", tool], capture_output=True).returncode != 0:
            console.print(f"{COLOR_ERROR}[Error] {tool} is not installed!")
            return False
    try:
        pass  # Imports moved to specific modules where they are used
    except ImportError as e:
        console.print(
            f"{COLOR_ERROR}[Error] Python library {str(e).split()[-1]} is not installed! Run 'pip install {str(e).split()[-1]}'"
        )
        return False
    return True


def validate_host(host):
    if not isinstance(host, str):
        return False

    # Regex for domain names
    domain_regex = r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
    # Regex for IPv4 addresses
    ipv4_regex = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"

    # Check for IP address first
    if re.match(ipv4_regex, host):
        return True

    # Then check for domain name
    sanitized_host = re.sub(
        r"[^a-zA-Z0-9.-]", "", host
    )  # Keep only allowed characters for domain
    if sanitized_host != host:
        logging.warning(f"Invalid characters detected in host: {host}")
        return False

    return bool(re.match(domain_regex, host))


def validate_uuid(uuid):
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, uuid))
