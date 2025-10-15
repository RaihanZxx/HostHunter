import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import unittest
from utils import validate_host


class TestValidateHost(unittest.TestCase):
    def test_valid_hosts(self):
        self.assertTrue(validate_host("example.com"))
        self.assertTrue(validate_host("sub.domain.co"))
        self.assertTrue(validate_host("xn--bcher-kva.example"))  # punycode label
        self.assertTrue(validate_host("127.0.0.1"))

    def test_invalid_hosts(self):
        self.assertFalse(validate_host(""))
        self.assertFalse(validate_host("example.com/"))
        self.assertFalse(validate_host("http://example.com"))
        self.assertFalse(validate_host("example.com:80"))
        self.assertFalse(validate_host("bad host.com"))
        self.assertFalse(validate_host("example..com"))
        self.assertFalse(validate_host("-example.com"))
        self.assertFalse(validate_host("example-.com"))
        self.assertFalse(validate_host("exa$mple.com"))
        self.assertFalse(validate_host("example.com && rm -rf /"))
        long_label = "a" * 64
        self.assertFalse(validate_host(f"{long_label}.com"))
        long_host = "a." * 127 + "com"
        self.assertFalse(validate_host(long_host))


if __name__ == "__main__":
    unittest.main()
