from __future__ import annotations

from typing import Any

from .automation import DiceAutomation
from .config_manager import load_config
from .log_utils import get_automation_log_path, tee_output_to_path
from .utils.webdriver_setup import setup_driver
from .zoho_mail_automation import ZohoMailAutomation


def run_automation(config_data: dict[str, dict[str, Any]] | None = None) -> None:
    active_config = config_data or load_config()
    dice_credentials = active_config.get("dice_credentials", active_config.get("credentials", {}))
    zoho_credentials = active_config.get("zoho_credentials", {})
    zoho_mail_settings = active_config.get("zoho_mail_settings", {})
    search_settings = active_config["search_settings"]
    site_settings = active_config.get(
        "site_settings",
        {"dice_enabled": True, "zoho_mail_enabled": False},
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

        if bool(site_settings.get("zoho_mail_enabled", False)):
            automations.append((
                "Zoho Mail",
                ZohoMailAutomation(
                    driver=driver,
                    wait=wait,
                    username=str(zoho_credentials.get("username", "")),
                    password=str(zoho_credentials.get("password", "")),
                    recipient_emails=zoho_mail_settings.get("recipient_emails", []),
                    humanizer=humanizer,
                ),
            ))

        if not automations:
            raise ValueError("No automations are enabled. Enable Dice and/or Zoho Mail before starting.")

        for site_name, automation in automations:
            automation_log_path = get_automation_log_path(site_name)
            with tee_output_to_path(automation_log_path, run_label=f"{site_name} run started"):
                print(f"\n=== Starting {site_name} automation ===")
                print(f"Writing {site_name} log to {automation_log_path}")
                automation.run()
    finally:
        if driver:
            driver.quit()
