"""This module tests alembic migrations using `pytest-alembic`.

`pytest-alembic` defines two database fixtures, `alembic_config` and `alembic_engine`,
which are used to test the migrations. These fixtures are defined in the local
conftest.py.

NB: The `alembic_runner` fixture is used to skip alembic tests.
"""

from typing import Any, Callable

import alembic
from pytest_alembic import create_alembic_fixture, tests
from pytest_alembic.runner import MigrationContext

migration_history = create_alembic_fixture()


def test_single_head_revision(
    alembic_runner: Callable[[dict[str, Any] | alembic.config.Config | None], Callable],
    migration_history: MigrationContext,
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
    migration_history: MigrationContext,
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
    migration_history: MigrationContext,
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
#     migration_history: MigrationContext,
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


def test_b7e1c2d4a9f0_hashes_recovery_codes(
    alembic_runner: Any, alembic_engine: Any
) -> None:
    """The Argon2/recovery-code migration hashes plaintext codes in place, leaves
    already-hashed codes and legacy password hashes alone, and widens the column.

    Parameters
    ----------
    alembic_runner
        pytest-alembic runner for the throwaway migration database.
    alembic_engine
        Engine for the same database.
    """

    import hashlib
    from datetime import datetime, timezone

    from sqlalchemy import text

    already_hashed = hashlib.sha256(b"already").hexdigest()
    legacy_password_hash = "ab" * 48  # 96 hex chars, the legacy format.
    now = datetime.now(timezone.utc)

    # Database as it was just before this revision, with one pre-migration user.
    # Other tests may have left the DB at head, so step to the previous revision
    # from whichever side we are on.
    alembic_runner.migrate_up_to("3c54b4f5decf")
    alembic_runner.migrate_down_to("3c54b4f5decf")
    alembic_runner.insert_into(
        "user",
        {
            "created_datetime_utc": now,
            "hashed_password": legacy_password_hash,
            "recovery_codes": ["PlainCode0123456789A", already_hashed],
            "updated_datetime_utc": now,
            "username": "pre_migration_user",
        },
    )
    alembic_runner.migrate_up_one()

    with alembic_engine.connect() as conn:
        codes, password_hash = conn.execute(
            text(
                'SELECT recovery_codes, hashed_password FROM "user" '
                "WHERE username = 'pre_migration_user'"
            )
        ).one()
        width = conn.execute(
            text(
                "SELECT character_maximum_length FROM information_schema.columns "
                "WHERE table_name = 'user' AND column_name = 'hashed_password'"
            )
        ).scalar_one()

    assert codes == [
        hashlib.sha256(b"PlainCode0123456789A").hexdigest(),
        already_hashed,
    ]
    assert password_hash == legacy_password_hash
    assert width == 255
