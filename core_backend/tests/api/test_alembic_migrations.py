"""This module tests alembic migrations using `pytest-alembic`.

`pytest-alembic` defines two database fixtures, `alembic_config` and `alembic_engine`,
which are used to test the migrations. These fixtures are defined in the local
conftest.py.

NB: The `alembic_runner` fixture is used to skip alembic tests.
"""

from typing import Any, Callable

import alembic
from pytest_alembic import create_alembic_fixture, tests

migration_history = create_alembic_fixture()


def test_single_head_revision(
    alembic_runner: Callable[[dict[str, Any] | alembic.config.Config | None], Callable],
    migration_history: Callable,
) -> None:
    """Assert that there only exists one head revision.

    Parameters
    ----------
    alembic_runner
        A fixture which provides a callable to run alembic migrations.
    migration_history
        A fixture which provides a history of alembic migrations.
    """

    tests.test_single_head_revision(migration_history)


def test_upgrade(
    alembic_runner: Callable[[dict[str, Any] | alembic.config.Config | None], Callable],
    migration_history: Callable,
) -> None:
    """Assert that the revision history can be run through from base to head.

    Parameters
    ----------
    alembic_runner
        A fixture which provides a callable to run alembic migrations.
    migration_history
        A fixture which provides a history of alembic migrations.
    """

    tests.test_upgrade(migration_history)


def test_model_definitions_match_ddl(
    alembic_runner: Callable[[dict[str, Any] | alembic.config.Config | None], Callable],
    migration_history: Callable,
) -> None:
    """Assert that the state of the migrations matches the state of the models
    describing the DDL.

    In general, the set of migrations in the history should coalesce into DDL which is
    described by the current set of models. Therefore, a call to revision --autogenerate
    should always generate an empty migration (e.g. find no difference between your
    database (i.e. migrations history) and your models).

    Parameters
    ----------
    alembic_runner
        A fixture which provides a callable to run alembic migrations.
    migration_history
        A fixture which provides a history of alembic migrations.
    """

    tests.test_model_definitions_match_ddl(migration_history)


# def test_up_down_consistency(
#     alembic_runner: Callable[[dict[str, Any] | alembic.config.Config | None], Callable],  # noqa: E501
#     migration_history: Callable,
# ) -> None:
#     """Assert that all downgrades succeed.
#
#     While downgrading may not be lossless operation data-wise, there’s a theory of
#     database migrations that says that the revisions in existence for a database should  # noqa: E501
#     be able to go from an entirely blank schema to the finished product, and back again.  # noqa: E501
#
#     Parameters
#     ----------
#     alembic_runner
#         A fixture which provides a callable to run alembic migrations.
#     migration_history
#         A fixture which provides a history of alembic migrations.
#     """
#
#     tests.test_up_down_consistency(migration_history)
