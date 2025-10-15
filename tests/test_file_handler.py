import os
import sys
import tempfile
import json
import csv
from unittest import TestCase
from unittest.mock import patch

# Add project root to import src package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.file_handler import scan_hosts_from_file, save_results


class TestFileHandler(TestCase):
    def test_scan_hosts_from_file_not_found(self):
        results = scan_hosts_from_file("/nonexistent/path.txt", timeout=1, max_workers=2)
        self.assertEqual(results, [])

    @patch("src.file_handler.host_checker.check_host")
    def test_scan_hosts_from_file_happy(self, mock_check):
        mock_check.side_effect = [
            ("green", "[200 OK] fast.com (IP: 1.1.1.1, Port: 443, Response: 10.50 ms) is active!"),
            ("yellow", "[Redirect] slow.com (IP: 2.2.2.2, Port: 443, Response: 50.00 ms) may be usable."),
        ]
        with tempfile.TemporaryDirectory() as td:
            fp = os.path.join(td, "hosts.txt")
            with open(fp, "w") as f:
                f.write("fast.com\n")
                f.write("slow.com\n")
                f.write("invalid host\n")

            results = scan_hosts_from_file(fp, timeout=1, max_workers=2)
            self.assertEqual(len(results), 2)
            # Results should be sorted by response time (fastest first)
            self.assertIn("fast.com", results[0][1])

    def test_save_results_txt_json_csv(self):
        sample_results = [
            ("green", "[200 OK] a.com (IP: 1.1.1.1, Port: 443, Response: 12.34 ms) is active!"),
            ("red", "[Failed] b.com (IP: 2.2.2.2, Port: 443) returned HTTP 500"),
        ]
        with tempfile.TemporaryDirectory() as td:
            # txt
            save_results(sample_results, td, "txt")
            txt_files = [f for f in os.listdir(td) if f.endswith(".txt")]
            self.assertTrue(txt_files)

            # json
            save_results(sample_results, td, "json")
            json_files = [f for f in os.listdir(td) if f.endswith(".json")]
            self.assertTrue(json_files)
            with open(os.path.join(td, json_files[0])) as jf:
                data = json.load(jf)
                self.assertIsInstance(data, list)
                self.assertIn("raw_message", data[0])

            # csv
            save_results(sample_results, td, "csv")
            csv_files = [f for f in os.listdir(td) if f.endswith(".csv")]
            self.assertTrue(csv_files)
            with open(os.path.join(td, csv_files[0]), newline="") as cf:
                reader = list(csv.reader(cf))
                # header + 2 rows
                self.assertEqual(len(reader), 3)
