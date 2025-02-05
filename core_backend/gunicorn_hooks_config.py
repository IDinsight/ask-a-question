"""This module contains the gunicorn hooks configuration for the application."""

from gunicorn.arbiter import Arbiter
from main import Worker
from prometheus_client import multiprocess


def child_exit(server: Arbiter, worker: Worker) -> None:  # pylint: disable=W0613
    """Multiprocess mode requires to mark the process as dead.

    Parameters
    ----------
    server
        The arbiter instance.
    worker
        The worker instance.
    """

    multiprocess.mark_process_dead(worker.pid)
