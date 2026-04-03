from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


class ShadowDOMHandler:
    APPLICATION_ENTRY_TERMS = (
        "easy apply",
        "continue application",
        "continue applying",
    )
    APPLIED_STATUS_TERMS = (
        "applied",
        "already applied",
    )

    def __init__(self, driver, wait, humanizer):
        self.driver = driver
        self.wait = wait
        self.humanizer = humanizer

    def _matches_apply_action(self, text: str) -> bool:
        normalized = text.lower()
        return any(term in normalized for term in self.APPLICATION_ENTRY_TERMS)

    def _matches_applied_status(self, text: str) -> bool:
        normalized = " ".join(text.lower().split())
        return normalized == "applied" or "already applied" in normalized

    def _find_visible_easy_apply_button(self):
        locators = []
        xpath_templates = [
            "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{term}')]",
            "//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{term}')]",
            "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{term}')]",
            "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{term}')]",
        ]

        for term in self.APPLICATION_ENTRY_TERMS:
            for xpath_template in xpath_templates:
                locators.append((By.XPATH, xpath_template.format(term=term)))

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
            const terms = arguments[0];
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

                    if (!isVisible || !terms.some((term) => text.includes(term))) {
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
            """,
            list(self.APPLICATION_ENTRY_TERMS),
        )

    def _find_visible_applied_status(self):
        locators = [
            (By.XPATH, "//button[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']"),
            (By.XPATH, "//*[@role='button' and translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']"),
            (By.XPATH, "//a[translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']"),
            (By.XPATH, "//*[@aria-label and translate(normalize-space(@aria-label), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')='applied']"),
            (By.XPATH, "//*[self::button or self::a or @role='button'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'already applied')]"),
            (By.XPATH, "//*[@aria-label and contains(translate(normalize-space(@aria-label), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'already applied')]"),
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

    def _has_applied_status_in_any_shadow_root(self):
        return bool(
            self.driver.execute_script(
                """
                const queue = [document];
                const visited = new Set();
                const normalize = (value) => (value || "").toLowerCase().replace(/\s+/g, " ").trim();

                while (queue.length) {
                    const root = queue.shift();
                    if (!root || visited.has(root)) {
                        continue;
                    }
                    visited.add(root);

                    const candidates = root.querySelectorAll("button, a, [role='button'], span");
                    for (const candidate of candidates) {
                        const text = normalize([
                            candidate.innerText,
                            candidate.textContent,
                            candidate.getAttribute("aria-label")
                        ].filter(Boolean).join(" "));
                        const isVisible = Boolean(candidate.offsetParent || candidate.getClientRects().length);

                        if (!isVisible) {
                            continue;
                        }

                        if (text === "applied" || text.includes("already applied")) {
                            return true;
                        }
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
        )

    def has_applied_status(self):
        try:
            direct_indicator = self._find_visible_applied_status()
            if direct_indicator is not None:
                return True

            shadow_host = None
            try:
                quick_wait = type(self.wait)(self.driver, 5)
                shadow_host = quick_wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "apply-button-wc, apply-button-wc.hydrated"))
                )
            except Exception:
                shadow_host = None

            if shadow_host is not None:
                button_marked_applied = self.driver.execute_script(
                    """
                    const shadowHost = arguments[0];
                    const shadowRoot = shadowHost.shadowRoot;
                    if (!shadowRoot) {
                        return false;
                    }

                    const normalize = (value) => (value || "").toLowerCase().replace(/\\s+/g, " ").trim();
                    const candidates = shadowRoot.querySelectorAll("button, a, [role='button'], span");
                    for (const candidate of candidates) {
                        const text = normalize([
                            candidate.innerText,
                            candidate.textContent,
                            candidate.getAttribute("aria-label")
                        ].filter(Boolean).join(" "));

                        if (text === "applied" || text.includes("already applied")) {
                            return true;
                        }
                    }

                    return false;
                    """,
                    shadow_host,
                )
                if button_marked_applied:
                    return True

            return self._has_applied_status_in_any_shadow_root()
        except Exception:
            return False

    def find_and_click_easy_apply(self):
        """Find and click the Easy Apply or Continue Application button"""
        print("Looking for Easy Apply / Continue Application button...")
        try:
            direct_button = self._find_visible_easy_apply_button()
            if direct_button is not None:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", direct_button)
                self.humanizer.short_pause()
                self.driver.execute_script("arguments[0].click();", direct_button)
                print("Clicked application entry button from regular DOM")
                self.humanizer.short_pause()
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
                    const terms = arguments[1];
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

                        if (terms.some((term) => text.includes(term))) {
                            candidate.click();
                            return true;
                        }
                    }

                    return false;
                """, shadow_host, list(self.APPLICATION_ENTRY_TERMS))

            if not button_clicked:
                button_clicked = self._click_easy_apply_in_any_shadow_root()

            if button_clicked:
                print("Successfully clicked application entry button")
                self.humanizer.short_pause()
                return True

            print("Application entry button not found - job may already be completed or not eligible")
            return False

        except Exception as e:
            message = getattr(e, "msg", str(e)).splitlines()[0]
            print(f"Error finding application entry button: {message}")
            return False
