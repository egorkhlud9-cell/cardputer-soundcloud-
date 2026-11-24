import os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from soundcloud_cardputer.storage import DEFAULT_CONFIG, load_library, save_library

class CoreTests(unittest.TestCase):
    def test_default_config_needs_no_api_credentials(self):
        self.assertEqual(DEFAULT_CONFIG, {"volume":70,"last_section":"Home","last_track":None})
    def test_local_library_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            from soundcloud_cardputer import storage
            old_dir,old_file=storage.APP_DIR,storage.LIBRARY_FILE
            try:
                storage.APP_DIR=Path(tmp)/".config"/"soundcloud-cardputer"
                storage.LIBRARY_FILE=storage.APP_DIR/"library.json"
                data={"favorites":[{"title":"Track"}],"playlists":[{"name":"Local","tracks":[]}],"history":[]}
                save_library(data)
                self.assertEqual(load_library(),data)
                self.assertEqual(storage.LIBRARY_FILE.stat().st_mode & 0o777,0o600)
            finally:
                storage.APP_DIR,storage.LIBRARY_FILE=old_dir,old_file
if __name__=="__main__": unittest.main()
