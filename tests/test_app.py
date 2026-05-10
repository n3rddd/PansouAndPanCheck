import unittest
from unittest.mock import patch

import main
import pancheck
from config import Config
from proxy import get_query_param_pairs, parse_request_body


class ConfigTests(unittest.TestCase):
    def test_auth_requires_fixed_jwt_secret(self):
        original_enabled = Config.AUTH_ENABLED
        original_users = Config.AUTH_USERS_RAW
        original_secret = Config.AUTH_JWT_SECRET

        try:
            Config.AUTH_ENABLED = True
            Config.AUTH_USERS_RAW = "admin:secret"
            Config.AUTH_JWT_SECRET = ""

            with self.assertRaises(ValueError):
                Config.validate()
        finally:
            Config.AUTH_ENABLED = original_enabled
            Config.AUTH_USERS_RAW = original_users
            Config.AUTH_JWT_SECRET = original_secret


class RequestParsingTests(unittest.TestCase):
    def test_form_post_body_is_parsed(self):
        with main.app.test_request_context(
            "/api/search",
            method="POST",
            data={"kw": "abc", "res": "merge"},
        ):
            self.assertEqual(parse_request_body()["kw"], "abc")

    def test_get_query_pairs_keep_duplicate_values(self):
        with main.app.test_request_context("/api/search?channels=a&channels=b&kw=abc"):
            self.assertEqual(
                get_query_param_pairs(),
                [("channels", "a"), ("channels", "b"), ("kw", "abc")],
            )


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.original_enabled = Config.AUTH_ENABLED
        self.original_users = Config.AUTH_USERS_RAW
        self.original_secret = Config.AUTH_JWT_SECRET
        Config.AUTH_ENABLED = True
        Config.AUTH_USERS_RAW = "admin:secret"
        Config.AUTH_JWT_SECRET = "test-secret"
        self.client = main.app.test_client()

    def tearDown(self):
        Config.AUTH_ENABLED = self.original_enabled
        Config.AUTH_USERS_RAW = self.original_users
        Config.AUTH_JWT_SECRET = self.original_secret

    def test_verify_requires_token_when_auth_enabled(self):
        response = self.client.get("/api/auth/verify")
        self.assertEqual(response.status_code, 401)

    def test_login_and_verify_token(self):
        login = self.client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "secret"},
        )
        self.assertEqual(login.status_code, 200)

        token = login.get_json()["data"]["token"]
        verify = self.client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(verify.status_code, 200)
        self.assertTrue(verify.get_json()["data"]["valid"])


class CheckLinksTests(unittest.TestCase):
    def setUp(self):
        self.original_enabled = Config.AUTH_ENABLED
        Config.AUTH_ENABLED = False
        self.client = main.app.test_client()

    def tearDown(self):
        Config.AUTH_ENABLED = self.original_enabled

    def test_check_links_uses_pancheck_result(self):
        def fake_call_pancheck(client, links, selected_platforms=None):
            return {"valid_links": [links[0]]}

        payload = {
            "items": [
                {
                    "url": "https://pan.quark.cn/s/abc",
                    "disk_type": "quark",
                    "password": "1234",
                },
                {"url": "https://example.com/bad", "disk_type": "unknown"},
            ]
        }

        with patch.object(pancheck, "call_pancheck_api", fake_call_pancheck):
            response = self.client.post("/api/check/links", json=payload)

        data = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["data"]["results"][0]["state"], "ok")
        self.assertEqual(data["data"]["results"][1]["state"], "unsupported")


if __name__ == "__main__":
    unittest.main()
