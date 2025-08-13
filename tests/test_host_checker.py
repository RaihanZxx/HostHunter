import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import subprocess  # Added import

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from host_checker import get_host_ips, check_host, check_ping


class TestHostChecker(unittest.TestCase):

    def setUp(self):
        # Clear the cache before each test to ensure fresh results
        get_host_ips.cache_clear()

    @patch("subprocess.run")
    def test_get_host_ips_success(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="192.168.1.1\n8.8.8.8\n", stderr="", returncode=0
        )
        ips = get_host_ips("example.com")
        self.assertEqual(ips, ["192.168.1.1", "8.8.8.8"])
        mock_run.assert_called_once_with(
            ["dig", "+short", "example.com"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )

    @patch("subprocess.run")
    def test_get_host_ips_no_ip(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout=";; connection timed out; no servers could be reached\n",
            stderr="",
            returncode=0,  # dig returns 0 even if no IP is found, if command itself runs
        )
        ips = get_host_ips("nonexistent.com")
        self.assertEqual(ips, ["N/A"])

    @patch("subprocess.run")
    def test_get_host_ips_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="dig", timeout=10)
        ips = get_host_ips("example.com")
        self.assertEqual(ips, ["N/A"])

    @patch("subprocess.run")
    def test_get_host_ips_called_process_error(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="dig", stderr="Error output"
        )
        ips = get_host_ips("example.com")
        self.assertEqual(ips, ["N/A"])

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    def test_check_host_200_ok(self, mock_run, mock_get_host_ips):
        mock_run.return_value = MagicMock(
            stdout="HTTP/1.1 200 OK\nContent-Length: 123\n", stderr="", returncode=0
        )
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "green")
        self.assertIn("[200 OK]", message)
        mock_run.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    def test_check_host_redirect(self, mock_run, mock_get_host_ips):
        mock_run.return_value = MagicMock(
            stdout="HTTP/1.1 301 Moved Permanently\nLocation: https://new.example.com\n",
            stderr="",
            returncode=0,
        )
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "yellow")
        self.assertIn("[Redirect]", message)
        mock_run.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    def test_check_host_timeout(self, mock_run, mock_get_host_ips):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="curl", timeout=10)
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "red")
        self.assertIn("[Timeout]", message)
        mock_run.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    def test_check_host_curl_error(self, mock_run, mock_get_host_ips):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=6, cmd="curl", stderr="Could not resolve host"
        )
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "red")
        self.assertIn("[Failed]", message)
        self.assertIn("curl error", message)
        mock_run.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    @patch("host_checker.check_host", return_value=("green", "[200 OK] fallback"))
    def test_check_ping_success(self, mock_check_host, mock_run, mock_get_host_ips):
        mock_run.return_value = MagicMock(
            stdout="--- 192.168.1.1 ping statistics ---\n4 packets transmitted, 4 received, 0% packet loss, time 3003ms\nrtt min/avg/max/mdev = 10.000/12.500/15.000/2.000 ms\n",
            stderr="",
            returncode=0,
        )
        color, message = check_ping("example.com", 10)
        self.assertEqual(color, "spring_green2")
        self.assertIn("[Ping OK]", message)
        mock_run.assert_called_once()
        mock_check_host.assert_not_called()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    @patch(
        "host_checker.check_host",
        return_value=("yellow", "[Ping Unreachable] fallback"),
    )
    def test_check_ping_unreachable_fallback(
        self, mock_check_host, mock_run, mock_get_host_ips
    ):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="ping", stderr="Destination Host Unreachable"
        )
        color, message = check_ping("example.com", 10)
        self.assertEqual(color, "yellow")
        self.assertIn("[Ping Unreachable]", message)
        self.assertIn("fallback", message)
        mock_run.assert_called_once()
        mock_check_host.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("subprocess.run")
    @patch("host_checker.check_host", return_value=("yellow", "[Timeout] fallback"))
    def test_check_ping_timeout_fallback(
        self, mock_check_host, mock_run, mock_get_host_ips
    ):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=10)
        color, message = check_ping("example.com", 10)
        self.assertEqual(color, "orange3")
        self.assertIn("[Timeout]", message)
        self.assertIn("fallback", message)
        mock_run.assert_called_once()
        mock_check_host.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["N/A"])
    @patch("subprocess.run")
    def test_check_ping_no_ip(self, mock_run, mock_get_host_ips):
        color, message = check_ping("nonexistent.com", 10)
        self.assertEqual(color, "red")
        self.assertIn("[Error] nonexistent.com (IP: N/A) failed to resolve.", message)
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
