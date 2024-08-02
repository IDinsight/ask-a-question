from typing import Callable

from fastapi import FastAPI
from fastapi.requests import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus middleware for FastAPI.
    """

    def __init__(self, app: FastAPI) -> None:
        """
        This middleware will collect metrics about requests made to the application
        and expose them on the `/metrics` endpoint.
        """
        super().__init__(app)
        self.counter = Counter(
            "requests",
            "Number of requests served, by http code",
            ["method", "code", "endpoint"],
        )
        self.histogram = Histogram(
            "durations_seconds",
            "Request duration in seconds",
            ["method", "endpoint"],
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Collect metrics about requests made to the application.
        """

        if request.url.path == "/metrics":
            return await call_next(request)

        with self.histogram.labels(
            method=request.method, endpoint=request.url.path
        ).time():
            response = await call_next(request)

        self.counter.labels(
            method=request.method, code=response.status_code, endpoint=request.url.path
        ).inc()

        return response
