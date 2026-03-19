from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
import sys

LOG_PATH = Path(__file__).resolve().parent.parent / "log.txt"


class MultiWriter:
    def __init__(self, *writers):
        self.writers = [writer for writer in writers if writer is not None]

    def write(self, message: str) -> None:
        for writer in self.writers:
            writer.write(message)

    def flush(self) -> None:
        for writer in self.writers:
            flush = getattr(writer, "flush", None)
            if callable(flush):
                flush()


def get_log_path() -> Path:
    return LOG_PATH


@contextmanager
def mirrored_output(*extra_writers, include_console: bool = True):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"\n=== Run started {timestamp} ===\n")
        log_file.flush()

        stdout_targets = [log_file, *extra_writers]
        stderr_targets = [log_file, *extra_writers]

        if include_console:
            stdout_targets.insert(0, sys.__stdout__)
            stderr_targets.insert(0, sys.__stderr__)

        stdout_writer = MultiWriter(*stdout_targets)
        stderr_writer = MultiWriter(*stderr_targets)

        with redirect_stdout(stdout_writer), redirect_stderr(stderr_writer):
            yield LOG_PATH
