from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from ..config_manager import (
    DEFAULT_DICE_CREDENTIALS,
    DEFAULT_LINKEDIN_CREDENTIALS,
    get_config_path,
    load_config,
    normalize_keywords,
    save_config,
)
from ..log_utils import get_log_path, mirrored_output
from ..runner import run_automation


class _QueueWriter:
    def __init__(self, output_queue: queue.Queue[str]) -> None:
        self.output_queue = output_queue

    def write(self, message: str) -> None:
        if message:
            self.output_queue.put(message)

    def flush(self) -> None:
        return None


class AutomationApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Job Automation Control Center")
        self.geometry("920x760")
        self.minsize(820, 620)
        self.configure(bg="#f4efe7")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.is_running = False

        self.dice_enabled_var = tk.BooleanVar(value=True)
        self.linkedin_enabled_var = tk.BooleanVar(value=False)
        self.dice_username_var = tk.StringVar()
        self.dice_password_var = tk.StringVar()
        self.linkedin_username_var = tk.StringVar()
        self.linkedin_password_var = tk.StringVar()
        self.keyword_var = tk.StringVar()
        self.max_applications_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready.")

        self._configure_style()
        self._build_layout()
        self._load_config()
        self.after(100, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.option_add("*Font", ("Segoe UI", 10))
        style.configure("Shell.TFrame", background="#f4efe7")
        style.configure("Card.TFrame", background="#fffaf4")
        style.configure(
            "Title.TLabel",
            background="#f4efe7",
            foreground="#16324f",
        )
        style.configure(
            "Subtitle.TLabel",
            background="#f4efe7",
            foreground="#4b5563",
            font=("Segoe UI", 10),
        )
        style.configure(
            "CardTitle.TLabel",
            background="#fffaf4",
            foreground="#1f2937",
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background="#fffaf4",
            foreground="#334155",
        )
        style.configure(
            "Status.TLabel",
            background="#fffaf4",
            foreground="#0f4c5c",
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
        )

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=20, style="Shell.TFrame")
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(3, weight=1)

        header = ttk.Frame(container, style="Shell.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="LinkedIn + Dice Automation Control Center",
            style="Title.TLabel",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Configure one or both sites, then run a single browser session that logs into each enabled site once and applies across multiple job titles.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        config_card = ttk.Frame(container, padding=18, style="Card.TFrame")
        config_card.grid(row=1, column=0, sticky="nsew")
        config_card.columnconfigure(1, weight=1)
        config_card.columnconfigure(2, weight=0)

        ttk.Label(config_card, text="Configuration", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 14)
        )

        ttk.Checkbutton(
            config_card,
            text="Run Dice",
            variable=self.dice_enabled_var,
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))
        ttk.Checkbutton(
            config_card,
            text="Run LinkedIn",
            variable=self.linkedin_enabled_var,
        ).grid(row=1, column=1, sticky="w", pady=(0, 6))

        self._add_field(config_card, 2, "Dice Email", self.dice_username_var)
        self._add_field(config_card, 3, "Dice Password", self.dice_password_var, show="*")
        self._add_field(config_card, 4, "LinkedIn Email", self.linkedin_username_var)
        self._add_field(config_card, 5, "LinkedIn Password", self.linkedin_password_var, show="*")
        self._add_field(config_card, 6, "Job Titles", self.keyword_var)
        self._add_field(config_card, 7, "Max Applications / Site", self.max_applications_var)

        ttk.Label(
            config_card,
            text=f"Config file: {get_config_path()}",
            style="Body.TLabel",
        ).grid(row=8, column=0, columnspan=3, sticky="w", pady=(10, 0))
        ttk.Label(
            config_card,
            text="Separate multiple job titles with commas. LinkedIn uses Easy Apply + Contract + Past 24 hours and skips cards marked Reposted.",
            style="Body.TLabel",
        ).grid(row=9, column=0, columnspan=3, sticky="w", pady=(6, 0))

        actions_card = ttk.Frame(container, padding=18, style="Card.TFrame")
        actions_card.grid(row=2, column=0, sticky="ew", pady=(16, 16))
        actions_card.columnconfigure(1, weight=1)

        button_bar = ttk.Frame(actions_card, style="Card.TFrame")
        button_bar.grid(row=0, column=0, sticky="w")

        self.save_button = ttk.Button(
            button_bar,
            text="Save Settings",
            style="Accent.TButton",
            command=self._save_settings,
        )
        self.save_button.grid(row=0, column=0, padx=(0, 10))

        self.reload_button = ttk.Button(
            button_bar,
            text="Reload",
            command=self._load_config,
        )
        self.reload_button.grid(row=0, column=1, padx=(0, 10))

        self.start_button = ttk.Button(
            button_bar,
            text="Start Automation",
            style="Accent.TButton",
            command=self._start_automation,
        )
        self.start_button.grid(row=0, column=2)

        ttk.Label(
            actions_card,
            textvariable=self.status_var,
            style="Status.TLabel",
        ).grid(row=0, column=1, sticky="e")

        log_card = ttk.Frame(container, padding=18, style="Card.TFrame")
        log_card.grid(row=3, column=0, sticky="nsew")
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ttk.Label(log_card, text="Run Log", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )
        self.log_output = scrolledtext.ScrolledText(
            log_card,
            wrap="word",
            height=18,
            bg="#13293d",
            fg="#f8fafc",
            insertbackground="#f8fafc",
            relief="flat",
            padx=12,
            pady=12,
        )
        self.log_output.grid(row=1, column=0, sticky="nsew")
        self.log_output.configure(state="disabled")

    def _add_field(
        self,
        parent: ttk.Frame,
        row_index: int,
        label: str,
        variable: tk.StringVar,
        show: str | None = None,
    ) -> None:
        ttk.Label(parent, text=label, style="Body.TLabel").grid(
            row=row_index, column=0, sticky="w", padx=(0, 12), pady=6
        )
        entry_kwargs: dict[str, Any] = {"textvariable": variable}
        if show is not None:
            entry_kwargs["show"] = show

        ttk.Entry(parent, **entry_kwargs).grid(
            row=row_index, column=1, columnspan=2, sticky="ew", pady=6
        )

    def _append_log(self, message: str) -> None:
        self.log_output.configure(state="normal")
        self.log_output.insert("end", message)
        self.log_output.see("end")
        self.log_output.configure(state="disabled")

    def _drain_log_queue(self) -> None:
        while True:
            try:
                message = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(message)

        self.after(100, self._drain_log_queue)

    def _clear_log(self) -> None:
        self.log_output.configure(state="normal")
        self.log_output.delete("1.0", "end")
        self.log_output.configure(state="disabled")

    def _build_config_payload(self, require_ready_values: bool) -> dict[str, dict[str, Any]]:
        try:
            max_applications = int(self.max_applications_var.get().strip())
        except ValueError as exc:
            raise ValueError("Max applications per site must be a whole number.") from exc

        if max_applications <= 0:
            raise ValueError("Max applications per site must be greater than zero.")

        keywords = normalize_keywords(self.keyword_var.get().strip())

        payload = {
            "dice_credentials": {
                "username": self.dice_username_var.get().strip(),
                "password": self.dice_password_var.get().strip(),
            },
            "linkedin_credentials": {
                "username": self.linkedin_username_var.get().strip(),
                "password": self.linkedin_password_var.get().strip(),
            },
            "site_settings": {
                "dice_enabled": bool(self.dice_enabled_var.get()),
                "linkedin_enabled": bool(self.linkedin_enabled_var.get()),
            },
            "search_settings": {
                "keyword": keywords[0] if keywords else self.keyword_var.get().strip(),
                "keywords": keywords,
                "max_applications": max_applications,
            },
        }

        if require_ready_values:
            if not payload["site_settings"]["dice_enabled"] and not payload["site_settings"]["linkedin_enabled"]:
                raise ValueError("Enable Dice and/or LinkedIn before starting.")

            if not payload["search_settings"]["keywords"]:
                raise ValueError("Enter at least one search keyword before starting.")

            if payload["site_settings"]["dice_enabled"]:
                if not payload["dice_credentials"]["username"]:
                    raise ValueError("Enter your Dice email before starting.")
                if not payload["dice_credentials"]["password"]:
                    raise ValueError("Enter your Dice password before starting.")
                if payload["dice_credentials"]["username"] == DEFAULT_DICE_CREDENTIALS["username"]:
                    raise ValueError("Replace the Dice placeholder email before starting.")
                if payload["dice_credentials"]["password"] == DEFAULT_DICE_CREDENTIALS["password"]:
                    raise ValueError("Replace the Dice placeholder password before starting.")

            if payload["site_settings"]["linkedin_enabled"]:
                if not payload["linkedin_credentials"]["username"]:
                    raise ValueError("Enter your LinkedIn email before starting.")
                if not payload["linkedin_credentials"]["password"]:
                    raise ValueError("Enter your LinkedIn password before starting.")
                if payload["linkedin_credentials"]["username"] == DEFAULT_LINKEDIN_CREDENTIALS["username"]:
                    raise ValueError("Replace the LinkedIn placeholder email before starting.")
                if payload["linkedin_credentials"]["password"] == DEFAULT_LINKEDIN_CREDENTIALS["password"]:
                    raise ValueError("Replace the LinkedIn placeholder password before starting.")

        return payload

    def _save_settings(self, show_confirmation: bool = True) -> bool:
        try:
            payload = self._build_config_payload(require_ready_values=False)
        except ValueError as exc:
            messagebox.showerror("Invalid Settings", str(exc), parent=self)
            return False

        save_config(
            payload["dice_credentials"],
            payload["linkedin_credentials"],
            payload["search_settings"],
            payload["site_settings"],
        )
        self.status_var.set("Settings saved to config.py.")

        if show_confirmation:
            messagebox.showinfo("Saved", "Settings saved to config.py.", parent=self)

        return True

    def _load_config(self) -> None:
        config_data = load_config()
        self.dice_enabled_var.set(bool(config_data["site_settings"]["dice_enabled"]))
        self.linkedin_enabled_var.set(bool(config_data["site_settings"]["linkedin_enabled"]))
        self.dice_username_var.set(str(config_data["dice_credentials"]["username"]))
        self.dice_password_var.set(str(config_data["dice_credentials"]["password"]))
        self.linkedin_username_var.set(str(config_data["linkedin_credentials"]["username"]))
        self.linkedin_password_var.set(str(config_data["linkedin_credentials"]["password"]))
        self.keyword_var.set(", ".join(config_data["search_settings"]["keywords"]))
        self.max_applications_var.set(str(config_data["search_settings"]["max_applications"]))
        self.status_var.set("Loaded settings from config.py.")

    def _set_controls_enabled(self, enabled: bool) -> None:
        button_state = "normal" if enabled else "disabled"
        self.save_button.configure(state=button_state)
        self.reload_button.configure(state=button_state)
        self.start_button.configure(state=button_state)

    def _start_automation(self) -> None:
        if self.is_running:
            return

        try:
            payload = self._build_config_payload(require_ready_values=True)
        except ValueError as exc:
            messagebox.showerror("Missing Information", str(exc), parent=self)
            return

        save_config(
            payload["dice_credentials"],
            payload["linkedin_credentials"],
            payload["search_settings"],
            payload["site_settings"],
        )

        self._clear_log()
        self._append_log(f"Saved settings to {get_config_path()}\n")
        self._append_log(f"Writing logs to {get_log_path()}\n")
        self._append_log("Launching browser automation...\n\n")
        self.is_running = True
        self._set_controls_enabled(False)
        self.status_var.set("Automation is running...")

        self.worker_thread = threading.Thread(
            target=self._run_automation_worker,
            args=(payload,),
            daemon=True,
        )
        self.worker_thread.start()

    def _run_automation_worker(self, payload: dict[str, dict[str, Any]]) -> None:
        writer = _QueueWriter(self.log_queue)
        with mirrored_output(writer, include_console=False):
            try:
                run_automation(payload)
                print("\nAutomation finished.")
            except Exception as exc:
                print(f"\nAutomation failed: {exc}\n")
                self._queue_finish(False)
                return

        self._queue_finish(True)

    def _queue_finish(self, succeeded: bool) -> None:
        try:
            self.after(0, lambda: self._finish_automation(succeeded))
        except tk.TclError:
            pass

    def _finish_automation(self, succeeded: bool) -> None:
        self.is_running = False
        self._set_controls_enabled(True)
        if succeeded:
            self.status_var.set("Automation finished.")
        else:
            self.status_var.set("Automation stopped with an error.")

    def _handle_close(self) -> None:
        if self.is_running:
            should_close = messagebox.askyesno(
                "Automation Running",
                "The automation is still running. Close the window anyway?",
                parent=self,
            )
            if not should_close:
                return

        self.destroy()


def launch_ui() -> None:
    app = AutomationApp()
    app.mainloop()
