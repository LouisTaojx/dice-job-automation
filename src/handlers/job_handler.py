import time

from selenium.webdriver.common.by import By

from ..utils.humanizer import wait_for_document_ready


class JobHandler:
    def __init__(self, driver, wait, shadow_dom_handler, humanizer):
        self.driver = driver
        self.wait = wait
        self.shadow_dom_handler = shadow_dom_handler
        self.humanizer = humanizer

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

    def _click_first_available_action(self, actions, timeout=4):
        normalized_actions = [
            {"name": name, "variants": [variant.lower() for variant in text_variants]}
            for name, text_variants in actions
        ]

        clicked_action = self.driver.execute_script(
            """
            const actions = arguments[0];
            const visited = new Set();
            const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));
            const readText = (node) => [
                node?.innerText,
                node?.textContent,
                node?.getAttribute?.("aria-label"),
                node?.value
            ].filter(Boolean).join(" ").toLowerCase().trim();

            const dialogRoots = Array.from(
                document.querySelectorAll("[role='dialog'], dialog, [aria-modal='true']")
            ).filter(isVisible);
            const queue = dialogRoots.length ? [...dialogRoots] : [document];

            while (queue.length) {
                const root = queue.shift();
                if (!root || visited.has(root)) {
                    continue;
                }
                visited.add(root);

                const candidates = root.querySelectorAll("button, a, [role='button'], input[type='button'], input[type='submit'], span");
                for (const candidate of candidates) {
                    const clickable = candidate.closest("button, a, [role='button']") || candidate;
                    const text = `${readText(candidate)} ${readText(clickable)}`.trim();

                    if (!isVisible(candidate)) {
                        continue;
                    }

                    for (const action of actions) {
                        if (!action.variants.some((variant) => text.includes(variant))) {
                            continue;
                        }

                        clickable.scrollIntoView({ block: "center" });
                        clickable.click();
                        return action.name;
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
            """,
            normalized_actions,
        )

        if clicked_action:
            print(f"Clicked {clicked_action} button")
            self.humanizer.short_pause()
            return clicked_action

        end_time = time.time() + timeout
        while time.time() < end_time:
            for action in normalized_actions:
                locators = []
                for variant in action["variants"]:
                    locators.extend([
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

                button = self._find_first_visible(locators)
                if button is None:
                    continue

                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                self.humanizer.short_pause()
                self.driver.execute_script("arguments[0].click();", button)
                print(f"Clicked {action['name']} button")
                self.humanizer.short_pause()
                return action["name"]

            time.sleep(0.2)

        return None

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

    def _has_existing_application(self):
        exact_terms = ["applied"]
        phrase_terms = [
            "already applied",
            "application submitted",
            "you have already applied",
            "you've already applied",
            "you have successfully applied",
            "successfully applied",
            "application sent",
            "thanks for applying",
        ]

        try:
            marker = self.driver.execute_script(
                """
                const exactTerms = arguments[0];
                const phraseTerms = arguments[1];
                const queue = [document];
                const visited = new Set();
                const normalize = (value) => (value || "").toLowerCase().replace(/\\s+/g, " ").trim();
                const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));
                const readText = (node) => normalize([
                    node?.innerText,
                    node?.textContent,
                    node?.getAttribute?.("aria-label"),
                    node?.value
                ].filter(Boolean).join(" "));

                while (queue.length) {
                    const root = queue.shift();
                    if (!root || visited.has(root)) {
                        continue;
                    }
                    visited.add(root);

                    const candidates = root.querySelectorAll(
                        "button, a, [role='button'], [aria-label], [data-cy], [data-testid], span"
                    );
                    for (const candidate of candidates) {
                        if (!isVisible(candidate)) {
                            continue;
                        }

                        const text = readText(candidate);
                        if (!text) {
                            continue;
                        }

                        if (exactTerms.some((term) => text === term)) {
                            return text;
                        }
                        if (phraseTerms.some((term) => text.includes(term))) {
                            return text;
                        }
                    }

                    const descendants = root.querySelectorAll("*");
                    for (const node of descendants) {
                        if (node.shadowRoot) {
                            queue.push(node.shadowRoot);
                        }
                    }
                }

                const bodyText = normalize(document.body?.innerText);
                const bodyMarker = phraseTerms.find((term) => bodyText.includes(term));
                return bodyMarker || "";
                """,
                exact_terms,
                phrase_terms,
            )
        except Exception:
            return False

        return bool(marker)

    def apply_to_job(self, job_title="", job_url=""):
        """Handle the application process for a single job"""
        new_tab = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_tab)

        try:
            print("Waiting for page to load completely...")
            try:
                wait_for_document_ready(self.driver, timeout=25)
            except Exception:
                pass
            self.humanizer.page_pause()

            if self._has_existing_application():
                print(f"Skipping job - already applied: {job_title} | {job_url}")
                return False

            if not self.shadow_dom_handler.find_and_click_easy_apply():
                print(f"Skipping job - Easy Apply / Continue Application was not available: {job_title} | {job_url}")
                return False

            self.humanizer.short_pause()

            prioritized_actions = [
                ("Next", ["next", "continue"]),
                ("Review", ["review", "review application"]),
                ("Submit", ["submit application", "submit", "apply now", "send application"]),
            ]

            for _ in range(6):
                if self._is_application_complete():
                    print(f"Application submitted: {job_title}")
                    return True

                print("Looking for Next, Review, or Submit button...")
                clicked_action = self._click_first_available_action(prioritized_actions, timeout=4)
                if clicked_action in {"Next", "Review"}:
                    continue
                if clicked_action == "Submit":
                    self.humanizer.page_pause()
                    if self._is_application_complete() or self._has_existing_application():
                        print(f"Application submitted: {job_title}")
                    else:
                        print(f"Submit clicked for: {job_title}")
                    return True

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
            self.humanizer.short_pause()
