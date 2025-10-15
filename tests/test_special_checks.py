import os
import sys
from unittest import TestCase
from unittest.mock import patch, MagicMock

# Add project root to import src package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.special_checks import check_vmess_trojan, check_quota_bug


class TestSpecialChecks(TestCase):
    @patch("src.special_checks.utils.validate_uuid", return_value=True)
    @patch("src.special_checks.websocket.WebSocket")
    def test_check_vmess_ok_json(self, mock_ws_cls, _):
        mock_ws = MagicMock()
        mock_ws.recv.return_value = "{\"ok\":true}"
        mock_ws_cls.return_value = mock_ws

        color, msg = check_vmess_trojan(
            host="example.com",
            port=443,
            path="/ws",
            protocol="vmess",
            uuid_or_password="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            use_tls=True,
        )
        self.assertEqual(color, "green")
        self.assertIn("VMESS OK", msg)

    @patch("src.special_checks.utils.validate_uuid", return_value=True)
    @patch("src.special_checks.websocket.WebSocket")
    def test_check_vmess_non_json(self, mock_ws_cls, _):
        mock_ws = MagicMock()
        mock_ws.recv.return_value = "not json"
        mock_ws_cls.return_value = mock_ws
        color, msg = check_vmess_trojan(
            host="example.com", protocol="vmess", uuid_or_password="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        )
        self.assertEqual(color, "yellow")
        self.assertIn("Warning", msg)

    def test_check_vmess_invalid_uuid(self):
        color, msg = check_vmess_trojan(
            host="example.com", protocol="vmess", uuid_or_password="bad-uuid"
        )
        self.assertEqual(color, "red")

    def test_check_trojan_short_password(self):
        color, msg = check_vmess_trojan(
            host="example.com", protocol="trojan", uuid_or_password="short"
        )
        self.assertEqual(color, "red")

    @patch("src.special_checks.requests.get")
    def test_check_quota_bug_green(self, mock_get):
        resp = MagicMock(status_code=200, text="Hello Ruangguru", headers={"X-Ruangguru": "1"})
        mock_get.return_value = resp
        color, msg = check_quota_bug("example.com", 443, 5)
        self.assertEqual(color, "green")

    @patch("src.special_checks.requests.get")
    def test_check_quota_bug_yellow_200(self, mock_get):
        resp = MagicMock(status_code=200, text="Hello", headers={})
        mock_get.return_value = resp
        color, msg = check_quota_bug("example.com", 443, 5)
        self.assertEqual(color, "yellow")

    @patch("src.special_checks.requests.get")
    def test_check_quota_bug_yellow_non200(self, mock_get):
        resp = MagicMock(status_code=404, text="Not Found", headers={})
        mock_get.return_value = resp
        color, msg = check_quota_bug("example.com", 443, 5)
        self.assertEqual(color, "yellow")

    @patch("src.special_checks.requests.get")
    def test_check_quota_bug_error(self, mock_get):
        from requests import RequestException

        mock_get.side_effect = RequestException("boom")
        color, msg = check_quota_bug("example.com", 443, 5)
        self.assertEqual(color, "red")
