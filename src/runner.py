from __future__ import annotations

from typing import Any

from .automation import DiceAutomation
from .config_manager import load_config
from .linkedin_automation import LinkedInAutomation
from .utils.webdriver_setup import setup_driver


def run_automation(config_data: dict[str, dict[str, Any]] | None = None) -> None:
    active_config = config_data or load_config()
    dice_credentials = active_config.get("dice_credentials", active_config.get("credentials", {}))
    linkedin_credentials = active_config.get("linkedin_credentials", {})
    search_settings = active_config["search_settings"]
    site_settings = active_config.get(
        "site_settings",
        {"dice_enabled": True, "linkedin_enabled": False},
    )

    driver = None
    try:
        driver, wait, humanizer = setup_driver()

        automations = []
        if bool(site_settings.get("dice_enabled", True)):
            automations.append((
                "Dice",
                DiceAutomation(
                    driver=driver,
                    wait=wait,
                    username=str(dice_credentials.get("username", "")),
                    password=str(dice_credentials.get("password", "")),
                    keywords=search_settings.get("keywords", search_settings.get("keyword", "")),
                    max_applications=int(search_settings.get("max_applications", 0)),
                    humanizer=humanizer,
                ),
            ))

        if bool(site_settings.get("linkedin_enabled", False)):
            automations.append((
                "LinkedIn",
                LinkedInAutomation(
                    driver=driver,
                    wait=wait,
                    username=str(linkedin_credentials.get("username", "")),
                    password=str(linkedin_credentials.get("password", "")),
                    keywords=search_settings.get("keywords", search_settings.get("keyword", "")),
                    max_applications=int(search_settings.get("max_applications", 0)),
                    humanizer=humanizer,
                ),
            ))

        if not automations:
            raise ValueError("No job sites are enabled. Enable Dice and/or LinkedIn before starting.")

        for site_name, automation in automations:
            print(f"\n=== Starting {site_name} automation ===")
            automation.run()
    finally:
        if driver:
            driver.quit()
