from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class ShadowDOMHandler:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

    def _find_visible_easy_apply_button(self):
        locators = [
            (
                By.XPATH,
                "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]",
            ),
            (
                By.XPATH,
                "//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]",
            ),
            (
                By.XPATH,
                "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]",
            ),
            (
                By.XPATH,
                "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]",
            ),
        ]

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

    def _click_easy_apply_in_any_shadow_root(self):
        return self.driver.execute_script(
            """
            const queue = [document];
            const visited = new Set();

            while (queue.length) {
                const root = queue.shift();
                if (!root || visited.has(root)) {
                    continue;
                }
                visited.add(root);

                const candidates = root.querySelectorAll("button, a, [role='button'], span");
                for (const candidate of candidates) {
                    const text = [
                        candidate.innerText,
                        candidate.textContent,
                        candidate.getAttribute("aria-label")
                    ].filter(Boolean).join(" ").toLowerCase();
                    const isVisible = Boolean(candidate.offsetParent || candidate.getClientRects().length);

                    if (!isVisible || !text.includes("easy apply")) {
                        continue;
                    }

                    candidate.click();
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
            """
        )

    def find_and_click_easy_apply(self):
        """Find and click the Easy Apply button from regular DOM or shadow DOM"""
        print("Looking for Easy Apply button...")
        try:
            direct_button = self._find_visible_easy_apply_button()
            if direct_button is not None:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", direct_button)
                self.driver.execute_script("arguments[0].click();", direct_button)
                print("Clicked Easy Apply button from regular DOM")
                return True

            shadow_host = None
            try:
                quick_wait = type(self.wait)(self.driver, 5)
                shadow_host = quick_wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "apply-button-wc, apply-button-wc.hydrated"))
                )
            except Exception:
                shadow_host = None

            button_clicked = False
            if shadow_host is not None:
                button_clicked = self.driver.execute_script("""
                    const shadowHost = arguments[0];
                    const shadowRoot = shadowHost.shadowRoot;
                    if (!shadowRoot) {
                        return false;
                    }

                    const candidates = shadowRoot.querySelectorAll("button, a, [role='button'], span");
                    for (const candidate of candidates) {
                        const text = [
                            candidate.innerText,
                            candidate.textContent,
                            candidate.getAttribute("aria-label")
                        ].filter(Boolean).join(" ").toLowerCase();

                        if (text.includes('easy apply')) {
                            candidate.click();
                            return true;
                        }
                    }

                    return false;
                """, shadow_host)

            if not button_clicked:
                button_clicked = self._click_easy_apply_in_any_shadow_root()

            if button_clicked:
                print("Successfully clicked Easy Apply button")
                return True

            print("Easy Apply button not found - job might be already applied to")
            return False

        except Exception as e:
            message = getattr(e, "msg", str(e)).splitlines()[0]
            print(f"Error finding Easy Apply button: {message}")
            return False
