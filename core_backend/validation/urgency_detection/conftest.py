from typing import TYPE_CHECKING, AsyncGenerator, List

import pytest
from httpx import ASGITransport, AsyncClient
from pytest import Item
from pytest_asyncio import is_async_test

from app.main import app

if TYPE_CHECKING:  # Fixture from validation/conftest.py; imported for typing only.
    from validation.conftest import ValidationWorkspace


def pytest_collection_modifyitems(items: List[Item]) -> None:
    pytest_asyncio_tests = (item for item in items if is_async_test(item))
    session_scope_marker = pytest.mark.asyncio(loop_scope="session")
    for async_test in pytest_asyncio_tests:
        async_test.add_marker(session_scope_marker, append=False)


@pytest.fixture(scope="session")
async def client(
    validation_workspace: "ValidationWorkspace",
) -> AsyncGenerator[AsyncClient, None]:
    """Async client for the app, with the app's lifespan running.

    `ASGITransport` does not run the lifespan, so it is entered here: it creates
    `app.state.redis` (API quotas) on this event loop. Depends on
    `validation_workspace` so workspace setup has finished first.
    """

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


# create command line arguments for pytest as per https://stackoverflow.com/a/42145604/7664921
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--validation_data_path", type=str, help="Path to validation data")
    parser.addoption("--ud_rules_path", type=str, help="Path to UD rules data")
    parser.addoption(
        "--validation_data_question_col",
        type=str,
        help="Question column in validation data",
    )
    parser.addoption(
        "--validation_data_label_col",
        type=str,
        help="Urgency label column in validation data",
    )
    parser.addoption(
        "--ud_rules_col",
        type=str,
        help="The column in UD rules data that has the urgency rules",
    )
    parser.addoption(
        "--notification_topic",
        type=str,
        help="AWS SNS topic to send notification to. If none, no notification is sent",
        nargs="?",
        default=None,
    )
    parser.addoption(
        "--aws_profile",
        nargs="?",
        type=str,
        help="Name of AWS profile with access to S3 in case data is stored there "
        "(optional)",
        default=None,
    )


@pytest.fixture(scope="session")
def api_key(validation_workspace: "ValidationWorkspace") -> str:
    """The validation workspace's API key (used by /urgency-detect)."""

    return validation_workspace.api_key


@pytest.fixture(scope="session")
def fullaccess_token(validation_workspace: "ValidationWorkspace") -> str:
    """An admin access token for the validation workspace (used to manage rules)."""

    return validation_workspace.access_token


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".

    args = [
        "validation_data_path",
        "ud_rules_path",
        "validation_data_question_col",
        "validation_data_label_col",
        "ud_rules_col",
        "notification_topic",
        "aws_profile",
    ]

    for arg in args:
        option_value = metafunc.config.option.__getattribute__(arg)
        if arg in metafunc.fixturenames and option_value is not None:
            metafunc.parametrize(arg, [option_value], scope="session")
        else:
            metafunc.parametrize(arg, [None], scope="session")
