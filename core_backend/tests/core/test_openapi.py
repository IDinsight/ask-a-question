"""Tests for the OpenAPI spec that `app.main` publishes.

admin_app generates its typed API client from this spec (see
admin_app/openapi-ts.config.ts), using each operationId as an SDK function name.
"""

from collections import Counter

from app.main import app


class TestOperationIds:
    def _operation_ids(self) -> list[str]:
        spec = app.openapi()
        return [
            operation["operationId"]
            for path_item in spec["paths"].values()
            for operation in path_item.values()
        ]

    def test_operation_ids_are_unique(self) -> None:
        """Two routes with the same function name would generate clashing SDK
        functions. Give one an explicit `operation_id` if this fails."""
        duplicates = [
            name for name, count in Counter(self._operation_ids()).items() if count > 1
        ]
        assert duplicates == []

    def test_operation_ids_use_the_route_function_name(self) -> None:
        """No FastAPI default suffixes such as `_content__get`."""
        operation_ids = self._operation_ids()
        assert "retrieve_content" in operation_ids
        assert "create_urgency_rule" in operation_ids
