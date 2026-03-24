from __future__ import annotations

import random
import time

from selenium.webdriver.support.ui import WebDriverWait

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
window.chrome = window.chrome || { runtime: {} };
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});
Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32'
});
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5]
});
"""


class Humanizer:
    def __init__(self, min_delay: float = 0.2, max_delay: float = 1.0) -> None:
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._random = random.Random()

    def sleep(self, minimum: float | None = None, maximum: float | None = None) -> float:
        lower_bound = self.min_delay if minimum is None else minimum
        upper_bound = self.max_delay if maximum is None else maximum
        if upper_bound < lower_bound:
            lower_bound, upper_bound = upper_bound, lower_bound

        duration = self._random.uniform(lower_bound, upper_bound)
        time.sleep(duration)
        return duration

    def micro_pause(self) -> float:
        return self.sleep(0.08, 0.18)

    def short_pause(self) -> float:
        return self.sleep(0.2, 0.5)

    def page_pause(self) -> float:
        return self.sleep(0.4, 1.0)


def wait_for_document_ready(driver, timeout: int = 20) -> None:
    WebDriverWait(driver, timeout).until(
        lambda current_driver: current_driver.execute_script("return document.readyState") == "complete"
    )


def install_stealth(driver) -> bool:
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": STEALTH_SCRIPT},
        )
    except Exception:
        return False

    return True
