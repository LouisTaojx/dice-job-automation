from __future__ import annotations

from typing import Any

from .automation import DiceAutomation
from .config_manager import load_config
from .utils.webdriver_setup import setup_driver


def run_automation(config_data: dict[str, dict[str, Any]] | None = None) -> None:
    active_config = config_data or load_config()
    credentials = active_config["credentials"]
    search_settings = active_config["search_settings"]

    driver = None
    try:
        driver, wait, humanizer = setup_driver()

        automation = DiceAutomation(
            driver=driver,
            wait=wait,
            username=str(credentials.get("username", "")),
            password=str(credentials.get("password", "")),
            keywords=search_settings.get("keywords", search_settings.get("keyword", "")),
            max_applications=int(search_settings.get("max_applications", 0)),
            humanizer=humanizer,
        )
        automation.run()
    finally:
        if driver:
            driver.quit()
