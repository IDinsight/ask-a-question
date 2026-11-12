"""Tests for the security controls in `app.core.security`, the catch-all error
handler and their wiring into `app.main` (headers, CORS, /metrics, debug mode).

Most tests use tiny throwaway apps, so they need no database or Redis. The ones
that hit `app.main.app` use the shared session `client`.
"""

import logging
import string
from typing import Any

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from limits import parse
from slowapi import Limiter
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.types import Receive, Scope, Send

from app.core import security as core_security
from app.core.config import DOMAIN, RATE_LIMIT_AUTH
from app.core.exceptions import register_exception_handlers
from app.core.observability import RedactingFormatter, redact, scrub_sentry_event
from app.core.security import (
    SECURITY_HEADERS,
    InsecureConfigurationError,
    LegacySha256Hasher,
    SecurityHeadersMiddleware,
    create_access_token,
    generate_recovery_codes,
    get_client_ip,
    get_key_hash,
    get_random_string,
    get_rate_limit_key,
    hash_password,
    hash_recovery_code,
    limiter,
    protect_metrics_app,
    validate_security_settings,
    verify_password,
)
from app.main import app as main_app
from app.users.schemas import UserRoles

STRONG_SECRET = "0123456789abcdef0123456789abcdef"  # pragma: allowlist secret
PASSWORD = "core_security_password"  # pragma: allowlist secret


class TestValidateSecuritySettings:
    """The app must refuse to start with a forgeable JWT configuration."""

    @pytest.mark.parametrize(
        "secret",
        ["", "jwt-secret", "x" * 31],
        ids=["empty", "old-default", "too-short"],
    )
    def test_rejects_weak_secrets(self, secret: str) -> None:
        """Empty, published or short secrets are refused.

        Parameters
        ----------
        secret
            The JWT secret to validate.
        """

        with pytest.raises(InsecureConfigurationError, match="JWT_SECRET"):
            validate_security_settings(jwt_algorithm="HS256", jwt_secret=secret)

    @pytest.mark.parametrize("algorithm", ["none", "RS256", "ES256", ""])
    def test_rejects_non_hmac_algorithms(self, algorithm: str) -> None:
        """Only HMAC algorithms are allowed, even with a strong secret.

        Parameters
        ----------
        algorithm
            The JWT algorithm to validate.
        """

        with pytest.raises(InsecureConfigurationError, match="JWT_ALGORITHM"):
            validate_security_settings(
                jwt_algorithm=algorithm, jwt_secret=STRONG_SECRET
            )

    @pytest.mark.parametrize("algorithm", ["HS256", "HS384", "HS512"])
    def test_accepts_strong_settings(self, algorithm: str) -> None:
        """A 32+ character secret with an HMAC algorithm is accepted.

        Parameters
        ----------
        algorithm
            The JWT algorithm to validate.
        """

        validate_security_settings(jwt_algorithm=algorithm, jwt_secret=STRONG_SECRET)

    def test_running_config_is_valid(self) -> None:
        """The settings the test app was built with pass validation."""

        validate_security_settings()


class TestPasswordHashing:
    """Argon2 for new hashes; legacy SHA-256 hashes verify once and get upgraded."""

    def test_new_hashes_are_argon2_and_salted(self) -> None:
        """Hashing the same password twice gives two different Argon2 hashes."""

        first, second = hash_password(password=PASSWORD), hash_password(
            password=PASSWORD
        )
        assert first.startswith("$argon2id$")
        assert first != second
        assert PASSWORD not in first

    def test_verify_argon2(self) -> None:
        """Right password verifies without an upgrade; wrong password fails."""

        stored = hash_password(password=PASSWORD)
        assert verify_password(password=PASSWORD, stored_hash=stored) == (True, None)
        assert verify_password(password="wrong", stored_hash=stored) == (False, None)

    def test_legacy_hash_verifies_and_returns_argon2_upgrade(self) -> None:
        """A legacy hash still logs in, and an Argon2 replacement is returned."""

        legacy = LegacySha256Hasher().hash(PASSWORD)
        assert len(legacy) == 96

        is_valid, new_hash = verify_password(password=PASSWORD, stored_hash=legacy)
        assert is_valid is True
        assert new_hash is not None and new_hash.startswith("$argon2id$")
        assert verify_password(password=PASSWORD, stored_hash=new_hash) == (
            True,
            None,
        )

    def test_legacy_hash_wrong_password(self) -> None:
        """A wrong password against a legacy hash fails and yields no upgrade."""

        legacy = LegacySha256Hasher().hash(PASSWORD)
        assert verify_password(password="wrong", stored_hash=legacy) == (False, None)

    @pytest.mark.parametrize(
        "value, expected",
        [("a" * 96, True), ("A" * 96, False), ("a" * 95, False), ("$argon2id$", False)],
    )
    def test_legacy_identify(self, expected: bool, value: str) -> None:
        """Only 96 lowercase hex characters are treated as a legacy hash.

        Parameters
        ----------
        expected
            Whether `value` should be identified as legacy.
        value
            The candidate hash.
        """

        assert LegacySha256Hasher.identify(value) is expected


class TestRandomValues:
    """Recovery codes and throwaway passwords."""

    def test_recovery_codes_are_hashed_deterministically(self) -> None:
        """Hashes are stable (so lookups work) and never equal the plaintext."""

        code = generate_recovery_codes(num_codes=1)[0]
        assert hash_recovery_code(code=code) == hash_recovery_code(code=code)
        assert hash_recovery_code(code=code) != code
        assert len(hash_recovery_code(code=code)) == 64

    def test_random_string(self) -> None:
        """Random strings have the requested length and alphabet and do not repeat."""

        values = {get_random_string(size=12) for _ in range(50)}
        assert len(values) == 50
        allowed = set(string.ascii_letters + string.digits)
        assert all(len(v) == 12 and set(v) <= allowed for v in values)


class TestSecurityHeaders:
    """`SecurityHeadersMiddleware` on its own and as wired into `app.main`."""

    @pytest.fixture(scope="class")
    def headers_client(self) -> TestClient:
        """Build a tiny app with the middleware and a few routes.

        Returns
        -------
        TestClient
            Client for the tiny app.
        """

        app = FastAPI()

        @app.get("/ok")
        def ok() -> dict[str, str]:
            return {"status": "ok"}

        @app.get("/custom-cache")
        def custom_cache() -> PlainTextResponse:
            return PlainTextResponse("x", headers={"Cache-Control": "max-age=60"})

        app.add_middleware(SecurityHeadersMiddleware)
        return TestClient(app)

    def test_headers_on_every_response(self, headers_client: TestClient) -> None:
        """Successful and 404 responses both carry every header.

        Parameters
        ----------
        headers_client
            Client for the tiny app.
        """

        for path in ("/ok", "/does-not-exist"):
            response = headers_client.get(path)
            for name, value in SECURITY_HEADERS.items():
                assert response.headers[name] == value, (path, name)

    def test_endpoint_headers_win(self, headers_client: TestClient) -> None:
        """A header the endpoint set itself is not overwritten.

        Parameters
        ----------
        headers_client
            Client for the tiny app.
        """

        response = headers_client.get("/custom-cache")
        assert response.headers["Cache-Control"] == "max-age=60"
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_docs_keep_working(self, headers_client: TestClient) -> None:
        """Swagger UI is exempt from the strict CSP (it loads CDN assets).

        Parameters
        ----------
        headers_client
            Client for the tiny app.
        """

        response = headers_client.get("/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "Content-Security-Policy" not in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_main_app_sends_headers(self, client: TestClient) -> None:
        """The real app sends the headers.

        Parameters
        ----------
        client
            Test client for `app.main.app`.
        """

        response = client.get("/healthcheck")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]


class TestCors:
    """CORS on `app.main.app`: exact origins, limited methods and headers."""

    def test_allowed_origin_preflight(self, client: TestClient) -> None:
        """The admin app origin may send Authorization on a PUT.

        Parameters
        ----------
        client
            Test client for `app.main.app`.
        """

        origin = f"https://{DOMAIN}"
        response = client.options(
            "/content/",
            headers={
                "Access-Control-Request-Headers": "authorization,content-type",
                "Access-Control-Request-Method": "PUT",
                "Origin": origin,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["access-control-allow-origin"] == origin

    def test_unknown_origin_rejected(self, client: TestClient) -> None:
        """Other origins get no CORS grant.

        Parameters
        ----------
        client
            Test client for `app.main.app`.
        """

        response = client.options(
            "/content/",
            headers={
                "Access-Control-Request-Method": "GET",
                "Origin": "https://evil.example.com",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "access-control-allow-origin" not in response.headers

    def test_unlisted_request_header_rejected(self, client: TestClient) -> None:
        """Arbitrary request headers are no longer allowed.

        Parameters
        ----------
        client
            Test client for `app.main.app`.
        """

        response = client.options(
            "/content/",
            headers={
                "Access-Control-Request-Headers": "x-forwarded-host",
                "Access-Control-Request-Method": "GET",
                "Origin": f"https://{DOMAIN}",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestMetricsGuard:
    """`/metrics` needs `Authorization: Bearer $METRICS_TOKEN`."""

    @staticmethod
    def _client(token: str) -> TestClient:
        """Wrap a fake metrics app with the guard.

        Parameters
        ----------
        token
            The configured metrics token.

        Returns
        -------
        TestClient
            Client for the guarded app.
        """

        async def fake_metrics(scope: Scope, receive: Receive, send: Send) -> None:
            await PlainTextResponse("metric 1")(scope, receive, send)

        return TestClient(protect_metrics_app(fake_metrics, token=token))

    def test_disabled_without_token(self) -> None:
        """No configured token means /metrics does not exist, even with a header."""

        response = self._client("").get("/", headers={"Authorization": "Bearer "})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.parametrize(
        "header",
        [None, "Bearer wrong", "scrape-token", "Basic scrape-token", "bearer x"],
    )
    def test_wrong_or_missing_token(self, header: str | None) -> None:
        """Anything but the exact bearer token is a 401.

        Parameters
        ----------
        header
            The Authorization header to send (`None` = omitted).
        """

        headers = {"Authorization": header} if header else {}
        response = self._client("scrape-token").get("/", headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "metric" not in response.text

    def test_correct_token(self) -> None:
        """The scraper with the right token gets the metrics."""

        response = self._client("scrape-token").get(
            "/", headers={"Authorization": "Bearer scrape-token"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.text == "metric 1"

    def test_main_app_metrics_not_public(self, client: TestClient) -> None:
        """METRICS_TOKEN is unset in tests, so the real /metrics is a 404.

        Parameters
        ----------
        client
            Test client for `app.main.app`.
        """

        assert client.get("/metrics/").status_code == status.HTTP_404_NOT_FOUND


class TestSafeErrors:
    """Unhandled exceptions never reach the client."""

    def test_unhandled_error_is_generic(self) -> None:
        """The response hides the exception text; it is still raised server-side."""

        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/boom")
        def boom() -> None:
            raise RuntimeError("password=hunter2 at /srv/secret/path")

        response = TestClient(app, raise_server_exceptions=False).get("/boom")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"detail": "Internal server error."}
        assert "hunter2" not in response.text

    def test_main_app_debug_off(self) -> None:
        """`app.main.app` does not run in debug mode (which returns tracebacks)."""

        assert main_app.debug is False


class TestRedaction:
    """Credentials are masked in logs and Sentry events."""

    @pytest.mark.parametrize(
        "text, secret",
        [
            ("Authorization: Bearer abc.def-123", "abc.def-123"),
            ("token eyJhbGc.eyJzdWIi.c2lnbmF0dXJl", "eyJhbGc.eyJzdWIi.c2lnbmF0dXJl"),
            ("password=hunter2&next=1", "hunter2"),
            ('{"password": "hunter2", "username": "bob"}', "hunter2"),
            ("recovery_code: Ab12Cd34", "Ab12Cd34"),
            ("api_key='sk-123'", "sk-123"),
        ],
    )
    def test_redact(self, secret: str, text: str) -> None:
        """Each credential is removed; surrounding text survives.

        Parameters
        ----------
        secret
            The credential that must not survive.
        text
            The input text.
        """

        assert secret not in redact(text)

    def test_redact_keeps_normal_text(self) -> None:
        """Ordinary log lines are unchanged."""

        line = "User bob logged in to workspace ws_1"
        assert redact(line) == line

    def test_formatter_redacts_arguments(self) -> None:
        """Values passed as logging args are redacted too."""

        record = logging.LogRecord(
            "x", logging.INFO, __file__, 1, "login %s", ("password=hunter2",), None
        )
        assert "hunter2" not in RedactingFormatter("%(message)s").format(record)

    def test_sentry_scrubber(self) -> None:
        """Auth headers, cookies and password fields are stripped from events."""

        event = {
            "request": {
                "cookies": {"session": "abc"},
                "data": {"password": "hunter2", "username": "bob"},
                "headers": {"Authorization": "Bearer abc", "Accept": "*/*"},
                "query_string": "token=abc&page=2",
            }
        }
        request = scrub_sentry_event(event, None)["request"]
        assert request["headers"] == {"Authorization": "[REDACTED]", "Accept": "*/*"}
        assert request["data"] == {"password": "[REDACTED]", "username": "bob"}
        assert request["cookies"] == {"session": "[REDACTED]"}
        assert "abc" not in request["query_string"]


def _request(headers: dict[str, str] | None = None) -> Request:
    """Build a bare request from socket peer 10.0.0.1 with the given headers.

    Parameters
    ----------
    headers
        Request headers.

    Returns
    -------
    Request
        The request.
    """

    return Request(
        {
            "client": ("10.0.0.1", 1234),
            "headers": [
                (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
            ],
            "method": "GET",
            "path": "/",
            "type": "http",
        }
    )


class TestRateLimitKeys:
    """Who a request is counted against."""

    @pytest.mark.parametrize(
        "hops, forwarded_for, expected",
        [
            (0, "1.1.1.1", "10.0.0.1"),  # Header ignored when no proxy is trusted.
            (1, None, "10.0.0.1"),  # No header: the socket peer.
            (1, "1.1.1.1", "1.1.1.1"),
            # A client-supplied entry on the left is ignored.
            (1, "6.6.6.6, 1.1.1.1", "1.1.1.1"),
            (2, "6.6.6.6, 1.1.1.1, 2.2.2.2", "1.1.1.1"),
            (2, "1.1.1.1", "1.1.1.1"),  # Fewer entries than hops.
        ],
    )
    def test_client_ip(
        self,
        expected: str,
        forwarded_for: str | None,
        hops: int,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """The client IP is read `hops` entries from the right of X-Forwarded-For.

        Parameters
        ----------
        expected
            The IP that should be used.
        forwarded_for
            The X-Forwarded-For header, if any.
        hops
            RATE_LIMIT_TRUSTED_PROXY_HOPS.
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(core_security, "RATE_LIMIT_TRUSTED_PROXY_HOPS", hops)
        headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
        assert get_client_ip(_request(headers)) == expected

    def test_key_for_user_jwt(self) -> None:
        """A valid user JWT is keyed on the username."""

        token = create_access_token(
            user_role=UserRoles.ADMIN, username="alice", workspace_name="ws"
        )
        request = _request({"Authorization": f"Bearer {token}"})
        assert get_rate_limit_key(request) == "user:alice"

    def test_key_for_api_key(self) -> None:
        """Any other bearer token is keyed on its hash, never the raw value."""

        request = _request({"Authorization": "Bearer raw-api-key"})
        key = get_rate_limit_key(request)
        assert key == f"key:{get_key_hash(key='raw-api-key')}"
        assert "raw-api-key" not in key

    def test_key_for_anonymous(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Anonymous requests are keyed on the client IP.

        Parameters
        ----------
        monkeypatch
            Pytest monkeypatch fixture.
        """

        monkeypatch.setattr(core_security, "RATE_LIMIT_TRUSTED_PROXY_HOPS", 1)
        request = _request({"X-Forwarded-For": "1.1.1.1"})
        assert get_rate_limit_key(request) == "ip:1.1.1.1"


class TestRateLimiting:
    """Limits enforced by `app.main.app`. The suite runs with RATE_LIMIT_ENABLED
    false (see tests/test.env), so each test switches limiting on and cleans up."""

    def test_auth_endpoint_limited_per_ip(self, client: TestClient) -> None:
        """Credential endpoints return 429 with Retry-After past RATE_LIMIT_AUTH,
        counted per client IP.

        Parameters
        ----------
        client
            Test client.
        """

        allowed = parse(RATE_LIMIT_AUTH).amount
        limiter.enabled = True
        try:
            limiter.reset()

            def logout(ip: str) -> Any:
                """POST /logout from the given client IP."""
                return client.post(
                    "/logout",
                    headers={"X-Forwarded-For": ip},
                    json={"refresh_token": "junk"},
                )

            for _ in range(allowed):
                assert logout("203.0.113.7").status_code == status.HTTP_204_NO_CONTENT

            response = logout("203.0.113.7")
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert int(response.headers["Retry-After"]) >= 1
            assert "Rate limit exceeded" in response.json()["detail"]

            # Another client IP has its own budget.
            assert logout("203.0.113.8").status_code == status.HTTP_204_NO_CONTENT
        finally:
            limiter.reset()
            limiter.enabled = False

    def test_default_limit_on_every_route(self, client: TestClient) -> None:
        """Routes without their own limit get the default one from the middleware.

        The app's limiter is swapped for one with a tiny default limit and memory
        storage; the middleware reads it from `app.state.limiter`.

        Parameters
        ----------
        client
            Test client.
        """

        original = main_app.state.limiter
        main_app.state.limiter = Limiter(
            key_func=get_rate_limit_key,
            default_limits=["2/minute"],
            storage_uri="memory://",
        )
        try:
            for _ in range(2):
                response = client.get("/user/require-register")
                assert response.status_code == status.HTTP_200_OK
            response = client.get("/user/require-register")
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        finally:
            main_app.state.limiter = original
