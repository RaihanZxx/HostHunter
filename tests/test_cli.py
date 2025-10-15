import os
import sys
from unittest import TestCase
from unittest.mock import patch, MagicMock
import configparser

# Add project root for importing src package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.cli import main_menu


class DummyStatus:
    def __enter__(self):
        return None
    def __exit__(self, exc_type, exc, tb):
        return False


class DummyConsole:
    def print(self, *args, **kwargs):
        pass
    def clear(self):
        pass
    def status(self, *args, **kwargs):
        return DummyStatus()


def minimal_config():
    cfg = configparser.ConfigParser()
    cfg["General"] = {
        "log_level": "INFO",
        "default_timeout": "10",
        "max_concurrent_checks": "5",
    }
    cfg["Paths"] = {
        "hosts_dir": "data/hosts",
        "output_dir": "output",
        "logs_dir": "output/logs",
        "results_dir": "output/results",
    }
    return cfg


class TestCLI(TestCase):
    @patch("src.cli.console", new=DummyConsole())
    @patch("src.cli.utils.setup_logging")
    @patch("src.cli.utils.load_config", side_effect=lambda: minimal_config())
    @patch("src.cli.utils.check_dependencies", return_value=True)
    @patch("src.cli.SPECIAL_CHECKS", new={})
    @patch("src.cli.Prompt.ask", side_effect=["6"])  # Exit immediately
    def test_main_menu_exit(self, *_):
        main_menu()

    @patch("src.cli.console", new=DummyConsole())
    @patch("src.cli.utils.setup_logging")
    @patch("src.cli.utils.load_config", side_effect=lambda: minimal_config())
    @patch("src.cli.utils.check_dependencies", return_value=True)
    @patch("src.cli.SPECIAL_CHECKS", new={})
    @patch("src.cli.host_checker.check_host", return_value=("green", "[200 OK] example.com (IP: 1.1.1.1, Port: 443, Response: 12.34 ms) is active!"))
    @patch("src.cli.Prompt.ask", side_effect=["1", "10", "example.com", "443", "", "6"])  # single host then exit
    def test_main_menu_single_host_flow(self, *_):
        main_menu()
