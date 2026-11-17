"""Unit tests for `app.core.observability`.

Prometheus metrics use a private registry, and Sentry, Langfuse and LiteLLM
callbacks are mocked, so nothing is sent anywhere.
"""

import importlib.util
import logging
from functools import partial
from types import ModuleType, SimpleNamespace
from typing import Any, Generator
from unittest.mock import MagicMock
from uuid import uuid4

import litellm
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry, Counter, Histogram

from app.core import config, observability
from app.core.observability import (
    PrometheusMiddleware,
    create_langfuse_metadata,
    create_metrics_app,
    get_log_level_from_str,
    init_langfuse,
    init_sentry,
    setup_logger,
)


def _load_observability_copy(name: str) -> ModuleType:
    """Execute `observability.py` again as a separate module.

    Used to run the import-time Langfuse block under a patched config without
    reloading (and so replacing the objects of) the real module. Coverage still
    attributes the executed lines to `app/core/observability.py`.

    Parameters
    ----------
    name
        Module name for the copy.

    Returns
    -------
    ModuleType
        The freshly executed module.
    """

    spec = importlib.util.spec_from_file_location(name, observability.__file__)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> CollectorRegistry:
    """Make `PrometheusMiddleware` register its metrics in a private registry.

    The app already registered `requests` / `durations_seconds` in the default
    registry, so a second middleware instance would otherwise fail as a duplicate.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.

    Returns
    -------
    CollectorRegistry
        The private registry.
    """

    registry = CollectorRegistry()
    monkeypatch.setattr(observability, "Counter", partial(Counter, registry=registry))
    monkeypatch.setattr(
        observability, "Histogram", partial(Histogram, registry=registry)
    )
    return registry


@pytest.fixture
def metrics_client(registry: CollectorRegistry) -> TestClient:
    """Build a tiny app wrapped in `PrometheusMiddleware`.

    Parameters
    ----------
    registry
        The private Prometheus registry.

    Returns
    -------
    TestClient
        Client for the tiny app.
    """

    app = FastAPI()

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        """Return a fixed payload.

        Returns
        -------
        dict[str, str]
            The payload.
        """

        return {"ping": "pong"}

    @app.get("/metrics")
    async def metrics() -> dict[str, str]:
        """Stand in for the mounted metrics app.

        Returns
        -------
        dict[str, str]
            The payload.
        """

        return {}

    app.add_middleware(PrometheusMiddleware)
    return TestClient(app)


@pytest.fixture
def fresh_logger_name() -> Generator[str, None, None]:
    """Return a unique logger name and remove its handlers afterwards.

    Yields
    ------
    Generator[str, None, None]
        The logger name.
    """

    name = f"test-observability-{uuid4().hex}"
    yield name
    logging.getLogger(name).handlers.clear()


# Prometheus.
def test_prometheus_middleware_records_requests(
    metrics_client: TestClient, registry: CollectorRegistry
) -> None:
    """Normal requests are counted and timed, labelled by method, code and path.

    Parameters
    ----------
    metrics_client
        Client for the tiny app.
    registry
        The private Prometheus registry.
    """

    assert metrics_client.get("/ping").json() == {"ping": "pong"}

    labels = {"method": "GET", "code": "200", "endpoint": "/ping"}
    assert registry.get_sample_value("requests_total", labels) == 1
    assert (
        registry.get_sample_value(
            "durations_seconds_count", {"method": "GET", "endpoint": "/ping"}
        )
        == 1
    )


def test_prometheus_middleware_skips_metrics_endpoint(
    metrics_client: TestClient, registry: CollectorRegistry
) -> None:
    """Scrapes of `/metrics` are not themselves recorded.

    Parameters
    ----------
    metrics_client
        Client for the tiny app.
    registry
        The private Prometheus registry.
    """

    assert metrics_client.get("/metrics").status_code == 200

    labels = {"method": "GET", "code": "200", "endpoint": "/metrics"}
    assert registry.get_sample_value("requests_total", labels) is None


def test_create_metrics_app(monkeypatch: pytest.MonkeyPatch) -> None:
    """The metrics app collects from the multiprocess directory.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    multiprocess = MagicMock()
    monkeypatch.setattr(observability, "multiprocess", multiprocess)

    metrics_app = create_metrics_app()

    assert callable(metrics_app)
    registry = multiprocess.MultiProcessCollector.call_args.args[0]
    assert isinstance(registry, CollectorRegistry)


# Langfuse.
@pytest.mark.parametrize(
    "session_id, expected",
    [
        (None, {"trace_id": "trace-1"}),
        (5, {"trace_id": "trace-1", "session_id": 5}),
    ],
)
def test_create_langfuse_metadata(
    monkeypatch: pytest.MonkeyPatch, session_id: int | None, expected: dict
) -> None:
    """Metadata carries the current trace ID and, if given, the session ID.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    session_id
        The session ID.
    expected
        The expected metadata.
    """

    context = MagicMock()
    context.get_current_trace_id.return_value = "trace-1"
    monkeypatch.setattr(observability, "langfuse_context", context)

    metadata = create_langfuse_metadata(
        feature_name="search", query_id=1, session_id=session_id, workspace_id=2
    )

    assert metadata == expected


@pytest.mark.parametrize(
    "langfuse, expected_callbacks", [("True", ["langfuse"]), ("False", [])]
)
def test_init_langfuse(
    monkeypatch: pytest.MonkeyPatch, langfuse: str, expected_callbacks: list[str]
) -> None:
    """LiteLLM callbacks are routed to Langfuse only when enabled.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    langfuse
        Value of the `LANGFUSE` setting.
    expected_callbacks
        Expected LiteLLM success and failure callbacks.
    """

    monkeypatch.setattr(observability, "LANGFUSE", langfuse)
    monkeypatch.setattr(litellm, "success_callback", [])
    monkeypatch.setattr(litellm, "failure_callback", [])

    init_langfuse()

    assert litellm.success_callback == expected_callbacks
    assert litellm.failure_callback == expected_callbacks


def _langfuse_logger(project_name: str | None) -> Any:
    """Build a fake LiteLLM Langfuse logger.

    Parameters
    ----------
    project_name
        Name returned for the project; `None` makes the lookup fail.

    Returns
    -------
    Any
        The fake logger.
    """

    projects = MagicMock()
    if project_name is None:
        projects.get.side_effect = RuntimeError("unreachable")
    else:
        projects.get.return_value = SimpleNamespace(
            data=[SimpleNamespace(name=project_name)]
        )
    client = SimpleNamespace(projects=projects)
    return SimpleNamespace(Langfuse=SimpleNamespace(client=client))


@pytest.mark.parametrize(
    "langfuse_logger, expected",
    [
        (_langfuse_logger("my-project"), "my-project"),
        (_langfuse_logger(None), None),
        (None, None),
    ],
)
def test_langfuse_project_name_at_import(
    monkeypatch: pytest.MonkeyPatch, langfuse_logger: Any, expected: str | None
) -> None:
    """With Langfuse enabled, the project name is looked up once at import.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    langfuse_logger
        The LiteLLM Langfuse logger, or `None` if not set up.
    expected
        The expected `LANGFUSE_PROJECT_NAME`.
    """

    monkeypatch.setattr(config, "LANGFUSE", "True")
    monkeypatch.setattr(litellm.utils, "langFuseLogger", langfuse_logger, raising=False)

    module = _load_observability_copy(f"observability_copy_{uuid4().hex}")

    assert module.LANGFUSE_PROJECT_NAME == expected


# Logging.
@pytest.mark.parametrize(
    "level_str, expected",
    [
        ("debug", logging.DEBUG),
        ("WARNING", logging.WARNING),
        ("CRITICAL", logging.CRITICAL),
        ("bogus", logging.INFO),
    ],
)
def test_get_log_level_from_str(level_str: str, expected: int) -> None:
    """Level names map case-insensitively; unknown names fall back to INFO.

    Parameters
    ----------
    level_str
        The level name.
    expected
        The expected logging level.
    """

    assert get_log_level_from_str(log_level_str=level_str) == expected


def test_setup_logger_configures_once(fresh_logger_name: str) -> None:
    """A new logger gets one handler at the given level; repeat calls reuse it.

    Parameters
    ----------
    fresh_logger_name
        A logger name not used elsewhere.
    """

    logger = setup_logger(log_level=logging.WARNING, name=fresh_logger_name)
    again = setup_logger(log_level=logging.DEBUG, name=fresh_logger_name)

    assert again is logger
    assert logger.level == logging.WARNING
    assert len(logger.handlers) == 1
    assert logger.handlers[0].level == logging.WARNING


def test_setup_logger_default_level(fresh_logger_name: str) -> None:
    """Without an explicit level, the configured `LOG_LEVEL` is used.

    Parameters
    ----------
    fresh_logger_name
        A logger name not used elsewhere.
    """

    logger = setup_logger(name=fresh_logger_name)

    assert logger.level == get_log_level_from_str()


# Sentry.
@pytest.mark.parametrize("dsn", [None, "", "https://..."])
def test_init_sentry_disabled_without_dsn(
    monkeypatch: pytest.MonkeyPatch, dsn: str | None
) -> None:
    """Sentry stays off when no real DSN is configured.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    dsn
        The configured DSN.
    """

    sentry_sdk = MagicMock()
    monkeypatch.setattr(observability, "sentry_sdk", sentry_sdk)
    monkeypatch.setattr(observability, "SENTRY_DSN", dsn)

    init_sentry()

    sentry_sdk.init.assert_not_called()


def test_init_sentry_with_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """A real DSN initialises Sentry with the configured sample rate.

    Parameters
    ----------
    monkeypatch
        Pytest monkeypatch fixture.
    """

    dsn = "https://[KEY]@sentry.example.com/1"
    sentry_sdk = MagicMock()
    monkeypatch.setattr(observability, "sentry_sdk", sentry_sdk)
    monkeypatch.setattr(observability, "SENTRY_DSN", dsn)
    monkeypatch.setattr(observability, "SENTRY_TRACES_SAMPLE_RATE", "0.25")

    init_sentry()

    kwargs = sentry_sdk.init.call_args.kwargs
    assert kwargs["dsn"] == dsn
    assert kwargs["traces_sample_rate"] == 0.25
