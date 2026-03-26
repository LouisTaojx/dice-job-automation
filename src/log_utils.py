from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
import re
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


def get_automation_log_path(automation_name: str) -> Path:
    normalized_name = automation_name.strip().lower()
    if normalized_name == "dice":
        filename = "dice_auto_apply_log.txt"
    elif normalized_name in {"zoho mail", "send email"}:
        filename = "send_email_log.txt"
    else:
        safe_name = re.sub(r"[^a-z0-9]+", "_", normalized_name).strip("_") or "automation"
        filename = f"{safe_name}_log.txt"

    return LOG_PATH.parent / filename


def _write_run_header(log_file, label: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file.write(f"\n=== {label} {timestamp} ===\n")
    log_file.flush()


@contextmanager
def mirrored_output(*extra_writers, include_console: bool = True):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        _write_run_header(log_file, "Run started")

        stdout_targets = [log_file, *extra_writers]
        stderr_targets = [log_file, *extra_writers]

        if include_console:
            stdout_targets.insert(0, sys.__stdout__)
            stderr_targets.insert(0, sys.__stderr__)

        stdout_writer = MultiWriter(*stdout_targets)
        stderr_writer = MultiWriter(*stderr_targets)

        with redirect_stdout(stdout_writer), redirect_stderr(stderr_writer):
            yield LOG_PATH


@contextmanager
def tee_output_to_path(log_path: Path, run_label: str | None = None):
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("a", encoding="utf-8") as log_file:
        if run_label:
            _write_run_header(log_file, run_label)

        stdout_writer = MultiWriter(sys.stdout, log_file)
        stderr_writer = MultiWriter(sys.stderr, log_file)

        with redirect_stdout(stdout_writer), redirect_stderr(stderr_writer):
            yield log_path
