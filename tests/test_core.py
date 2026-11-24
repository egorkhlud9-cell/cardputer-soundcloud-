import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from soundcloud_cardputer.soundcloud_api import OAuthFlow
from soundcloud_cardputer.storage import DEFAULT_CONFIG

class CoreTests(unittest.TestCase):
    def test_pkce_url_has_required_parameters(self):
        flow=OAuthFlow("client","secret","http://127.0.0.1:8765/callback")
        from urllib.parse import urlparse, parse_qs
        params=parse_qs(urlparse(flow.authorize_url()).query)
        self.assertEqual(params["response_type"],["code"])
        self.assertEqual(params["code_challenge_method"],["S256"])
        self.assertEqual(params["state"],[flow.state])
        self.assertTrue(params["code_challenge"][0])
    def test_default_config_has_no_embedded_credentials(self):
        self.assertEqual(DEFAULT_CONFIG["client_id"],"")
        self.assertEqual(DEFAULT_CONFIG["client_secret"],"")
if __name__=="__main__": unittest.main()
