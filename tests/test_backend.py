#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("cloudzero_server", ROOT / "bridge" / "server.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class BackendValidation(unittest.TestCase):
    def test_public_soundcloud_urls(self):
        self.assertTrue(MODULE.valid_sc_url("https://soundcloud.com/artist/track"))
        self.assertTrue(MODULE.valid_sc_url("https://on.soundcloud.com/example"))
        self.assertTrue(MODULE.valid_sc_url("http://m.soundcloud.com/artist/track"))

    def test_reject_non_soundcloud_urls(self):
        self.assertFalse(MODULE.valid_sc_url("https://example.com/soundcloud.com"))
        self.assertFalse(MODULE.valid_sc_url("file:///tmp/track.mp3"))
        self.assertFalse(MODULE.valid_sc_url("javascript:alert(1)"))
        self.assertFalse(MODULE.valid_sc_url("https://soundcloud.com.evil.example/track"))
        self.assertFalse(MODULE.valid_sc_url("https://user:pass@soundcloud.com/track"))

    def test_metadata_is_bounded(self):
        self.assertEqual(len(MODULE.clean_text("x" * 300, 40)), 40)
        self.assertEqual(MODULE.clean_text("  hello   world  "), "hello world")

if __name__ == "__main__":
    unittest.main()
