from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import time


class JobHandler:
    def __init__(self, driver, wait, shadow_dom_handler):
        self.driver = driver
        self.wait = wait
        self.shadow_dom_handler = shadow_dom_handler

    def _page_debug_summary(self):
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.strip()
        except Exception:
            body_text = ""

        snippet = " ".join(body_text.split())[:400] if body_text else "Unavailable"
        return (
            f"Current URL: {self.driver.current_url}\n"
            f"Page title: {self.driver.title}\n"
            f"Visible text snippet: {snippet}"
        )

    def _click_action_button(self, action_name, text_variants, timeout=5):
        lowered_variants = [variant.lower() for variant in text_variants]

        button_clicked = self.driver.execute_script(
            """
            const variants = arguments[0];
            const queue = [document];
            const visited = new Set();

            const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));

            while (queue.length) {
                const root = queue.shift();
                if (!root || visited.has(root)) {
                    continue;
                }
                visited.add(root);

                const candidates = root.querySelectorAll("button, a, [role='button'], input[type='button'], input[type='submit'], span");
                for (const candidate of candidates) {
                    const text = [
                        candidate.innerText,
                        candidate.textContent,
                        candidate.getAttribute("aria-label"),
                        candidate.value
                    ].filter(Boolean).join(" ").toLowerCase().trim();

                    if (!isVisible(candidate) || !variants.some((variant) => text.includes(variant))) {
                        continue;
                    }

                    const clickable = candidate.closest("button, a, [role='button']") || candidate;
                    clickable.scrollIntoView({ block: "center" });
                    clickable.click();
                    return true;
                }

                const descendants = root.querySelectorAll("*");
                for (const node of descendants) {
                    if (node.shadowRoot) {
                        queue.push(node.shadowRoot);
                    }
                }
            }

            return false;
            """,
            lowered_variants,
        )

        if button_clicked:
            print(f"Clicked {action_name} button")
            time.sleep(1)
            return True

        xpaths = []
        for variant in lowered_variants:
            xpaths.extend([
                (
                    By.XPATH,
                    f"//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{variant}')]",
                ),
                (
                    By.XPATH,
                    f"//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{variant}')]",
                ),
                (
                    By.XPATH,
                    f"//input[(@type='button' or @type='submit') and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{variant}')]",
                ),
                (
                    By.XPATH,
                    f"//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{variant}')]",
                ),
            ])

        quick_wait = type(self.wait)(self.driver, timeout)
        try:
            button = quick_wait.until(lambda driver: self._find_first_visible(xpaths))
        except TimeoutException:
            return False

        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        self.driver.execute_script("arguments[0].click();", button)
        print(f"Clicked {action_name} button")
        time.sleep(1)
        return True

    def _find_first_visible(self, locators):
        for by, value in locators:
            try:
                elements = self.driver.find_elements(by, value)
            except Exception:
                continue

            for element in elements:
                try:
                    if element.is_displayed():
                        return element
                except Exception:
                    continue

        return None

    def _is_application_complete(self):
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            return False

        success_markers = (
            "application submitted",
            "successfully applied",
            "application sent",
            "you have successfully applied",
            "thanks for applying",
            "you've applied",
        )
        return any(marker in body_text for marker in success_markers)

    def apply_to_job(self, job_title="", job_url=""):
        """Handle the application process for a single job"""
        new_tab = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_tab)

        try:
            print("Waiting for page to load completely...")
            time.sleep(4)

            if not self.shadow_dom_handler.find_and_click_easy_apply():
                print(f"Skipping job - already applied or not available for easy apply: {job_title} | {job_url}")
                return False

            time.sleep(1)

            for _ in range(5):
                if self._is_application_complete():
                    print(f"Application submitted: {job_title}")
                    return True

                print("Looking for Submit button...")
                if self._click_action_button("Submit", ["submit application", "submit", "apply now", "send application"]):
                    if self._is_application_complete():
                        print(f"Application submitted: {job_title}")
                    else:
                        print(f"Submit clicked for: {job_title}")
                    return True

                print("Looking for Review button...")
                if self._click_action_button("Review", ["review", "review application"]):
                    continue

                print("Looking for Next button...")
                if self._click_action_button("Next", ["next", "continue"]):
                    continue

                print("Could not find another application action button.")
                print(self._page_debug_summary())
                return False

            print("Reached the maximum number of application steps without finding completion.")
            print(self._page_debug_summary())
            return False

        except Exception as e:
            message = getattr(e, "msg", str(e)).splitlines()[0]
            print(f"Could not process job: {job_title} | {job_url} | {message}")
            print(self._page_debug_summary())
            return False
        finally:
            print("Closing job tab...")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            time.sleep(0.75)
