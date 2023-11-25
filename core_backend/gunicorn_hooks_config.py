from gunicorn.arbiter import Arbiter
from main import Worker
from prometheus_client import multiprocess


def child_exit(server: Arbiter, worker: Worker) -> None:
    """multiprocess mode requires to mark the process as dead"""
    multiprocess.mark_process_dead(worker.pid)
