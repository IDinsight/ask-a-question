import pytest
from fastapi.testclient import TestClient

from core_backend.app import create_app
from core_backend.app.db.engine import get_session


@pytest.fixture(scope="session")
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_session() -> pytest.FixtureRequest:
    """Create a test database session."""
    session_gen = get_session()
    session = next(session_gen)

    try:
        yield session
    finally:
        session.rollback()
        next(session_gen, None)


# create command line arguments for pytest as per https://stackoverflow.com/a/42145604/7664921
def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--validation_data_path", type=str, help="Path to validation data")
    parser.addoption("--content_data_path", type=str, help="Path to content data")
    parser.addoption(
        "--validation_data_question_col",
        type=str,
        help="Question column in validation data",
    )
    parser.addoption(
        "--validation_data_label_col",
        type=str,
        help="Content label column in validation data",
    )
    parser.addoption(
        "--content_data_label_col",
        type=str,
        help="Content label column in content data",
    )
    parser.addoption(
        "--content_data_text_col",
        type=str,
        help="Content text body column in content data",
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


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    # This is called for every test. Only get/set command line arguments
    # if the argument is specified in the list of test "fixturenames".

    args = [
        "validation_data_path",
        "content_data_path",
        "validation_data_question_col",
        "validation_data_label_col",
        "content_data_label_col",
        "content_data_text_col",
        "notification_topic",
        "aws_profile",
    ]

    for arg in args:
        option_value = metafunc.config.option.__getattribute__(arg)
        if arg in metafunc.fixturenames and option_value is not None:
            metafunc.parametrize(arg, [option_value])
        else:
            metafunc.parametrize(arg, [None])
