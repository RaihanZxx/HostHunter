import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import socket

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from host_checker import get_host_ips, check_host, check_ping


class TestHostChecker(unittest.TestCase):

    def setUp(self):
        # Clear the cache before each test to ensure fresh results
        get_host_ips.cache_clear()

    @patch("socket.getaddrinfo")
    def test_get_host_ips_success(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (socket.AF_INET, None, None, None, ("192.168.1.1", 0)),
            (socket.AF_INET, None, None, None, ("8.8.8.8", 0)),
        ]
        ips = get_host_ips("example.com")
        self.assertEqual(ips, ["192.168.1.1", "8.8.8.8"])

    @patch("socket.getaddrinfo")
    def test_get_host_ips_no_ip(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = []
        ips = get_host_ips("nonexistent.com")
        self.assertEqual(ips, ["N/A"])

    @patch("socket.getaddrinfo")
    def test_get_host_ips_exception(self, mock_getaddrinfo):
        mock_getaddrinfo.side_effect = socket.gaierror("fail")
        ips = get_host_ips("example.com")
        self.assertEqual(ips, ["N/A"])

    

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("requests.head")
    def test_check_host_200_ok(self, mock_head, mock_get_host_ips):
        mock_resp = MagicMock(status_code=200)
        mock_head.return_value = mock_resp
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "green")
        self.assertIn("[200 OK]", message)
        mock_head.assert_called()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("requests.head")
    def test_check_host_redirect(self, mock_head, mock_get_host_ips):
        mock_resp = MagicMock(status_code=301)
        mock_head.return_value = mock_resp
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "yellow")
        self.assertIn("[Redirect]", message)
        mock_head.assert_called()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("requests.head")
    def test_check_host_timeout(self, mock_head, mock_get_host_ips):
        from requests.exceptions import Timeout

        mock_head.side_effect = Timeout("timeout")
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "red")
        self.assertIn("[Timeout]", message)
        mock_head.assert_called()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("requests.head")
    def test_check_host_request_error(self, mock_head, mock_get_host_ips):
        from requests.exceptions import RequestException

        mock_head.side_effect = RequestException("boom")
        color, message = check_host("example.com", 443, 10)
        self.assertEqual(color, "red")
        self.assertIn("[Failed]", message)
        mock_head.assert_called()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("socket.create_connection")
    def test_check_ping_success(self, mock_conn, mock_get_host_ips):
        # Simulate successful TCP connects
        mock_conn.return_value.__enter__.return_value = None
        color, message = check_ping("example.com", 10)
        self.assertEqual(color, "spring_green2")
        self.assertIn("[Ping OK]", message)

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("host_checker.check_host", return_value=("yellow", "[Ping Unreachable] fallback"))
    @patch("socket.create_connection")
    def test_check_ping_unreachable_fallback(self, mock_conn, mock_check_host, mock_get_host_ips):
        mock_conn.side_effect = OSError("unreachable")
        color, message = check_ping("example.com", 10)
        self.assertEqual(color, "yellow")
        self.assertIn("[Ping Unreachable]", message)
        self.assertIn("fallback", message)
        mock_check_host.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["192.168.1.1"])
    @patch("host_checker.check_host", return_value=("yellow", "[Timeout] fallback"))
    @patch("socket.create_connection")
    def test_check_ping_timeout_fallback(self, mock_conn, mock_check_host, mock_get_host_ips):
        mock_conn.side_effect = socket.timeout
        color, message = check_ping("example.com", 10)
        self.assertEqual(color, "orange3")
        self.assertIn("[Timeout]", message)
        self.assertIn("fallback", message)
        mock_check_host.assert_called_once()

    @patch("host_checker.get_host_ips", return_value=["N/A"])
    def test_check_ping_no_ip(self, mock_get_host_ips):
        color, message = check_ping("nonexistent.com", 10)
        self.assertEqual(color, "red")
        self.assertIn("[Error] nonexistent.com (IP: N/A) failed to resolve.", message)


if __name__ == "__main__":
    unittest.main()
