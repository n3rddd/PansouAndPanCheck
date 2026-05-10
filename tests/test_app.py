import unittest
from unittest.mock import patch

import httpx
import main
import pancheck
import pansou_auth
from config import Config
from proxy import get_query_param_pairs, make_api_request, make_pansou_api_request, parse_request_body


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

    def test_pansou_auth_requires_token_or_credentials(self):
        original_enabled = Config.PANSOU_AUTH_ENABLED
        original_username = Config.PANSOU_AUTH_USERNAME
        original_password = Config.PANSOU_AUTH_PASSWORD
        original_token = Config.PANSOU_AUTH_TOKEN

        try:
            Config.PANSOU_AUTH_ENABLED = True
            Config.PANSOU_AUTH_USERNAME = ""
            Config.PANSOU_AUTH_PASSWORD = ""
            Config.PANSOU_AUTH_TOKEN = ""

            with self.assertRaises(ValueError):
                Config.validate()
        finally:
            Config.PANSOU_AUTH_ENABLED = original_enabled
            Config.PANSOU_AUTH_USERNAME = original_username
            Config.PANSOU_AUTH_PASSWORD = original_password
            Config.PANSOU_AUTH_TOKEN = original_token


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


class ApiResponseParsingTests(unittest.TestCase):
    def test_invalid_utf8_response_is_decoded_lossily(self):
        class DummyClient:
            def get(self, url, params=None, headers=None):
                return httpx.Response(
                    200,
                    content=b'{"code":0,"message":"bad \xff bytes","data":{}}',
                    request=httpx.Request("GET", url),
                )

        data = make_api_request(DummyClient(), "http://example.test/api", method="GET")

        self.assertEqual(data["code"], 0)
        self.assertIn("bad", data["message"])


class PansouAuthTests(unittest.TestCase):
    def setUp(self):
        self.original_enabled = Config.PANSOU_AUTH_ENABLED
        self.original_username = Config.PANSOU_AUTH_USERNAME
        self.original_password = Config.PANSOU_AUTH_PASSWORD
        self.original_token = Config.PANSOU_AUTH_TOKEN
        self.original_login_url = Config.PANSOU_AUTH_LOGIN_URL
        self.original_search_url = Config.SEARCH_API_URL
        Config.PANSOU_AUTH_ENABLED = True
        Config.PANSOU_AUTH_USERNAME = "WebAdmin"
        Config.PANSOU_AUTH_PASSWORD = "PansouWeb"
        Config.PANSOU_AUTH_TOKEN = ""
        Config.PANSOU_AUTH_LOGIN_URL = ""
        Config.SEARCH_API_URL = "http://pansou.test"
        pansou_auth.reset_cached_pansou_token()

    def tearDown(self):
        Config.PANSOU_AUTH_ENABLED = self.original_enabled
        Config.PANSOU_AUTH_USERNAME = self.original_username
        Config.PANSOU_AUTH_PASSWORD = self.original_password
        Config.PANSOU_AUTH_TOKEN = self.original_token
        Config.PANSOU_AUTH_LOGIN_URL = self.original_login_url
        Config.SEARCH_API_URL = self.original_search_url
        pansou_auth.reset_cached_pansou_token()

    def test_static_pansou_token_is_used(self):
        Config.PANSOU_AUTH_TOKEN = "static-token"

        headers = pansou_auth.get_pansou_auth_headers(client=None)

        self.assertEqual(headers, {"Authorization": "Bearer static-token"})

    def test_pansou_login_token_is_cached(self):
        class DummyClient:
            def __init__(self):
                self.login_count = 0

            def post(self, url, json=None, headers=None):
                self.login_count += 1
                return httpx.Response(
                    200,
                    json={"code": 0, "data": {"token": "login-token", "expires_in": 3600}},
                    request=httpx.Request("POST", url),
                )

        client = DummyClient()

        first = pansou_auth.get_pansou_auth_headers(client)
        second = pansou_auth.get_pansou_auth_headers(client)

        self.assertEqual(first, {"Authorization": "Bearer login-token"})
        self.assertEqual(second, {"Authorization": "Bearer login-token"})
        self.assertEqual(client.login_count, 1)

    def test_pansou_login_falls_back_to_legacy_route_when_auth_path_404(self):
        class DummyClient:
            def __init__(self):
                self.login_urls = []

            def post(self, url, json=None, headers=None):
                self.login_urls.append(url)
                if url.endswith("/api/auth/login"):
                    return httpx.Response(
                        404,
                        json={"code": 404, "message": "not found"},
                        request=httpx.Request("POST", url),
                    )
                return httpx.Response(
                    200,
                    json={"code": 0, "data": {"token": "legacy-token", "expires_in": 3600}},
                    request=httpx.Request("POST", url),
                )

        client = DummyClient()

        headers = pansou_auth.get_pansou_auth_headers(client)

        self.assertEqual(headers, {"Authorization": "Bearer legacy-token"})
        self.assertEqual(
            client.login_urls,
            [
                "http://pansou.test/api/auth/login",
                "http://pansou.test/api/login",
            ],
        )

    def test_custom_pansou_login_url_is_supported(self):
        class DummyClient:
            def __init__(self):
                self.login_urls = []

            def post(self, url, json=None, headers=None):
                self.login_urls.append(url)
                return httpx.Response(
                    200,
                    json={"code": 0, "data": {"token": "custom-token", "expires_in": 3600}},
                    request=httpx.Request("POST", url),
                )

        Config.PANSOU_AUTH_LOGIN_URL = "/custom/login"
        client = DummyClient()

        headers = pansou_auth.get_pansou_auth_headers(client)

        self.assertEqual(headers, {"Authorization": "Bearer custom-token"})
        self.assertEqual(client.login_urls, ["http://pansou.test/custom/login"])

    def test_pansou_token_refreshes_once_on_401(self):
        class DummyClient:
            def __init__(self):
                self.get_headers = []
                self.login_count = 0

            def get(self, url, params=None, headers=None):
                self.get_headers.append(headers)
                if len(self.get_headers) == 1:
                    return httpx.Response(
                        401,
                        json={"code": 401, "message": "expired"},
                        request=httpx.Request("GET", url),
                    )
                return httpx.Response(
                    200,
                    json={"code": 0, "message": "ok", "data": {}},
                    request=httpx.Request("GET", url),
                )

            def post(self, url, json=None, headers=None):
                self.login_count += 1
                return httpx.Response(
                    200,
                    json={"code": 0, "data": {"token": "fresh-token", "expires_in": 3600}},
                    request=httpx.Request("POST", url),
                )

        client = DummyClient()
        pansou_auth.set_cached_pansou_token("expired-token", cache_seconds=3600)

        data = make_pansou_api_request(client, "http://pansou.test/api/health", method="GET")

        self.assertEqual(data["code"], 0)
        self.assertEqual(client.login_count, 1)
        self.assertEqual(client.get_headers[0], {"Authorization": "Bearer expired-token"})
        self.assertEqual(client.get_headers[1], {"Authorization": "Bearer fresh-token"})


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
