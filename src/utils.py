"""
utils.py - Collection of utility functions for the HostHunter project.

This module provides common functionalities such as loading configuration,
setting up logging, displaying the application banner, checking system
dependencies, and validating various input formats like hostnames and UUIDs.
"""

import subprocess
import datetime
import logging
import re
import os
import configparser
from rich.console import Console


# Rich color tags for console output (Modern Palette)
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

# Panel Colors for Rich console panels
PANEL_BORDER_COLOR = "grey50"
PANEL_TEXT_COLOR = "grey82"


console = Console()


def load_config(config_file="config.ini"):
    """
    Loads configuration settings from 'config.ini' or uses default values.

    Initializes a ConfigParser object with default settings for General and Paths sections.
    If 'config.ini' exists, it attempts to read and override these defaults.
    Logs warnings or errors if the file is not found or malformed.

    Args:
        config_file (str, optional): The name of the configuration file. Defaults to "config.ini".

    Returns:
        configparser.ConfigParser: A ConfigParser object containing the loaded or default settings.
    """
    config = configparser.ConfigParser()
    # Set default configuration values
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
            config.read(config_file) # Read configuration from the file
            logging.info(f"Configuration loaded from {config_file}")
        except configparser.Error as e:
            # Handle errors during config file parsing
            console.print(
                f"{COLOR_ERROR}[Error] Failed to parse config file {config_file}: {e}. Using default settings."
            )
            logging.error(
                f"Failed to parse config file {config_file}: {e}. Using default settings."
            )
    else:
        # Warn if config file is not found
        console.print(
            f"{COLOR_WARNING}[Warning] Config file {config_file} not found. Using default settings."
        )
        logging.warning(f"Config file {config_file} not found. Using default settings.")

    return config


def setup_logging(config):
    """
    Configures the application's logging system.

    Sets up a file handler for detailed logs and a console handler for warnings and errors.
    The log level and log directory are determined from the provided configuration.

    Args:
        config (configparser.ConfigParser): The application configuration object.
    """
    # Determine logging level from configuration
    log_level_str = config["General"]["log_level"].upper()
    log_level = getattr(
        logging, log_level_str, logging.INFO
    )

    # Create logs directory if it doesn't exist
    logs_dir = config["Paths"]["logs_dir"]
    os.makedirs(logs_dir, exist_ok=True)
    # Generate a timestamped log file name
    log_file = os.path.join(
        logs_dir,
        f"hosthunter_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    )

    # Configure file handler for all log messages
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(file_formatter)

    # Configure console handler for warnings and errors only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(
        logging.WARNING
    )
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )
    console_handler.setFormatter(console_formatter)

    # Get the root logger and add both handlers
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    
    


def print_banner():
    """
    Prints the HostHunter ASCII art banner to the console.
    """
    # ASCII art for "HostHunter"
    banner_part1 = """██╗░░██╗░█████╗░░██████╗████████╗  ████╗░░░░░░████╗
██║░░██║██╔══██╗██╔════╝╚══██╔══╝  ██╔═╝░░░░░░╚═██║
███████║██║░░██║╚█████╗░░░░██║░░░  ██║░░█████╗░░██║
██╔══██║██║░░██║░╚═══██╗░░░██║░░░  ██║░░╚════╝░░██║
██║░░██║╚█████╔╝██████╔╝░░░██║░░░  ████╗░░░░░░████║
╚═╝░░╚═╝░╚════╝░╚═════╝░░░░╚═╝░░░  ╚═══╝░░░░░░╚═══╝"""
    # ASCII art for "by hansobored"
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
    """
    Check for required Python libraries (pure-Python implementation).

    Returns:
        bool: True if all required libraries are available, False otherwise.
    """
    try:
        import importlib

        for lib in ("requests", "rich"):
            importlib.import_module(lib)
        return True
    except ImportError as e:
        missing = str(e).split("'")[-2]
        console.print(
            f"{COLOR_ERROR}[Error] Python library {missing} is not installed! Run 'pip install {missing}'"
        )
        return False


def validate_host(host):
    """
    Validates if a given string is a valid hostname or IPv4 address.

    Checks against regex patterns for both domain names and IPv4 addresses.
    Prioritizes IPv4 validation. Performs basic sanitization for domain names.

    Args:
        host (str): The string to validate as a host.

    Returns:
        bool: True if the host is valid, False otherwise.
    """
    if not isinstance(host, str):
        return False

    host = host.strip()
    if not host:
        return False
    if len(host) > 253:
        return False
    # Reject obvious protocol/port/userinfo injections
    if any(sep in host for sep in ("//", "/", "@", ":", "?", "#")):
        return False
    # Allow numeric IPv4 quickly
    ipv4_regex = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if re.match(ipv4_regex, host):
        return True

    # Only allow valid DNS label charset and length
    if not re.fullmatch(r"[A-Za-z0-9.-]+", host):
        return False
    if host.startswith("-") or host.endswith("-") or host.startswith(".") or host.endswith("."):
        return False
    if ".." in host:
        return False
    labels = host.split(".")
    if any(len(label) == 0 or len(label) > 63 for label in labels):
        return False
    # Each label must start and end with alnum; hyphens allowed in between
    for label in labels:
        if not re.match(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])$", label):
            return False
    # TLD should be alphabetic and at least 2 chars
    if not re.match(r"^[A-Za-z]{2,}$", labels[-1]):
        return False
    return True


def validate_uuid(uuid):
    """
    Validates if a given string is a valid UUID (Universally Unique Identifier) format.

    Args:
        uuid (str): The string to validate as a UUID.

    Returns:
        bool: True if the string matches the UUID format, False otherwise.
    """
    # Regex pattern for standard UUID format (8-4-4-4-12 hexadecimal digits)
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, uuid))
