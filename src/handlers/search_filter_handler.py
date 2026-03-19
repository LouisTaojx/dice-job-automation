from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time


class SearchAndFilter:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

    def _wait_for_search_input(self, timeout=None):
        locators = [
            (By.CSS_SELECTOR, "input#typeaheadInput[data-cy='typeahead-input']"),
            (By.CSS_SELECTOR, "input[data-cy='typeahead-input']"),
            (By.CSS_SELECTOR, "input[placeholder='Job title, Keywords, Company']"),
            (By.CSS_SELECTOR, "input[name='q']"),
            (
                By.XPATH,
                "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'job title')]",
            ),
            (
                By.XPATH,
                "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'keywords')]",
            ),
        ]
        active_wait = self.wait if timeout is None else type(self.wait)(self.driver, timeout)
        return active_wait.until(lambda driver: self._find_first_displayed_element(locators))

    def _navigate_to_jobs_via_shadow_dom(self):
        return self.driver.execute_script(
            """
            const header = document.querySelector('dhi-seds-nav-header');
            if (!header || !header.shadowRoot) {
                return false;
            }

            const technologist = header.shadowRoot.querySelector('dhi-seds-nav-header-technologist');
            if (!technologist || !technologist.shadowRoot) {
                return false;
            }

            const display = technologist.shadowRoot.querySelector('dhi-seds-nav-header-display');
            if (!display || !display.shadowRoot) {
                return false;
            }

            const searchLink = display.shadowRoot.querySelector('a[href*="/jobs"]');
            if (!searchLink) {
                return false;
            }

            searchLink.click();
            return true;
            """
        )

    def _search_debug_summary(self):
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.strip()
        except Exception:
            body_text = ""

        snippet = " ".join(body_text.split())[:300] if body_text else "Unavailable"
        return (
            f"Current URL: {self.driver.current_url}\n"
            f"Page title: {self.driver.title}\n"
            f"Visible text snippet: {snippet}"
        )

    def _find_first_displayed_element(self, locators):
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

    def _is_filter_selected(self, element):
        for attribute in ("aria-checked", "aria-pressed", "aria-selected", "checked", "selected"):
            value = element.get_attribute(attribute)
            if isinstance(value, str) and value.lower() == "true":
                return True

        classes = (element.get_attribute("class") or "").lower().replace(",", " ").split()
        return bool(set(classes) & {"active", "selected", "checked"})

    def _click_filter_with_script(self, filter_name, search_text):
        result = self.driver.execute_script(
            """
            const target = arguments[0].toLowerCase();
            const selectors = [
                "button",
                "label",
                "[role='checkbox']",
                "[role='radio']",
                "[role='button']",
                "input[type='checkbox']",
                "input[type='radio']"
            ];
            const candidates = Array.from(document.querySelectorAll(selectors.join(",")));

            const isSelected = (node) => {
                const ariaState = ["aria-checked", "aria-pressed", "aria-selected"]
                    .some((name) => (node.getAttribute(name) || "").toLowerCase() === "true");
                const classTokens = (node.className || "").toLowerCase().replace(/,/g, " ").split(/\s+/);
                const classState = classTokens.some((token) => ["active", "selected", "checked"].includes(token));
                return ariaState || classState || node.checked === true;
            };

            for (const candidate of candidates) {
                const text = [
                    candidate.innerText,
                    candidate.textContent,
                    candidate.getAttribute("aria-label"),
                    candidate.value
                ].filter(Boolean).join(" ").toLowerCase();

                if (!text.includes(target)) {
                    continue;
                }

                if (isSelected(candidate)) {
                    return "already_selected";
                }

                const clickable = candidate.closest("button, label, [role='checkbox'], [role='radio'], [role='button']") || candidate;
                clickable.scrollIntoView({ block: "center" });
                clickable.click();
                return "clicked";
            }

            return "not_found";
            """,
            search_text,
        )

        if result == "already_selected":
            print(f"{filter_name} filter already selected")
            return True

        if result == "clicked":
            print(f"{filter_name} filter applied")
            time.sleep(1)
            return True

        return False

    def _apply_filter(self, filter_name, search_text, locators):
        print(f"Looking for {filter_name} filter...")

        if self._click_filter_with_script(filter_name, search_text):
            return True

        try:
            quick_wait = type(self.wait)(self.driver, 6)
            element = quick_wait.until(lambda driver: self._find_first_displayed_element(locators))

            if self._is_filter_selected(element):
                print(f"{filter_name} filter already selected")
                return True

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.driver.execute_script("arguments[0].click();", element)
            print(f"{filter_name} filter applied")
            time.sleep(1)
            return True
        except Exception:
            return self._click_filter_with_script(filter_name, search_text)

    def perform_search(self, keyword):
        """Check for search box, reveal if needed, and perform search"""
        print("Checking for search box...")
        search_input = None

        try:
            try:
                search_input = self._wait_for_search_input(timeout=15)
                print("Search box found directly")
            except Exception:
                print("Search box not immediately visible")
                try:
                    print("Navigating to jobs page...")
                    self.driver.get("https://www.dice.com/jobs")
                    self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                    time.sleep(3)

                    print("Waiting for search box to appear...")
                    search_input = self._wait_for_search_input(timeout=20)
                    print("Search box found after navigation")

                except Exception:
                    print("Trying shadow DOM navigation...")
                    clicked_search_link = self._navigate_to_jobs_via_shadow_dom()
                    if not clicked_search_link:
                        raise Exception("Search Jobs link was not available in the header shadow DOM")

                    print("Clicked Search Jobs link, waiting for page load...")
                    time.sleep(5)
                    search_input = self._wait_for_search_input(timeout=20)

            if search_input:
                print(f"Entering search keyword: {keyword}")
                search_input.clear()
                search_input.send_keys(keyword)

                time.sleep(0.5)
                search_input.send_keys(Keys.RETURN)
                time.sleep(1.5)

                try:
                    self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "a[data-cy='card-title-link']"
                    )))
                except Exception:
                    time.sleep(5)

                print("Search initiated successfully")
                return True

            print("Failed to find search input")
            return False

        except Exception as e:
            print(f"Error during search: {str(e)}")
            print(self._search_debug_summary())
            return False

    def apply_filters(self):
        """Apply Easy Apply, Today, and Contract filters"""
        try:
            print("Applying filters...")

            filters = [
                (
                    "Easy Apply",
                    "easy apply",
                    [
                        (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]"),
                        (By.XPATH, "//label[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]"),
                        (By.XPATH, "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]"),
                    ],
                ),
                (
                    "Today",
                    "today",
                    [
                        (By.XPATH, "//button[@role='radio' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'today')]"),
                        (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'today')]"),
                        (By.XPATH, "//label[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'today')]"),
                        (By.XPATH, "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'today')]"),
                    ],
                ),
                (
                    "Contract",
                    "contract",
                    [
                        (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contract')]"),
                        (By.XPATH, "//label[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contract')]"),
                        (By.XPATH, "//*[@aria-label and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'contract')]"),
                    ],
                ),
            ]

            for filter_name, search_text, locators in filters:
                if not self._apply_filter(filter_name, search_text, locators):
                    raise Exception(f"Could not apply {filter_name} filter")

            print("Successfully applied all filters")
            return True

        except Exception as e:
            print(f"Error applying filters: {str(e)}")
            return False
