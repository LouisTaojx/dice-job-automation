from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time


class SearchAndFilter:
    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

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
            time.sleep(2)
            return True

        return False

    def _apply_filter(self, filter_name, search_text, locators):
        print(f"Looking for {filter_name} filter...")

        try:
            element = self.wait.until(lambda driver: self._find_first_displayed_element(locators))

            if self._is_filter_selected(element):
                print(f"{filter_name} filter already selected")
                return True

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.driver.execute_script("arguments[0].click();", element)
            print(f"{filter_name} filter applied")
            time.sleep(2)
            return True
        except Exception:
            return self._click_filter_with_script(filter_name, search_text)

    def perform_search(self, keyword):
        """Check for search box, reveal if needed, and perform search"""
        print("Checking for search box...")
        search_input = None

        try:
            try:
                search_input = self.wait.until(EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "input[placeholder='Job title, Keywords, Company']"
                )))
                print("Search box found directly")
            except Exception:
                print("Search box not immediately visible")
                try:
                    print("Navigating to jobs page...")
                    self.driver.get("https://www.dice.com/jobs")
                    time.sleep(3)

                    print("Waiting for search box to appear...")
                    search_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "input#typeaheadInput[data-cy='typeahead-input']"
                    )))
                    print("Search box found after navigation")

                except Exception:
                    print("Trying shadow DOM navigation...")
                    self.driver.execute_script("""
                        const header = document.querySelector('dhi-seds-nav-header');
                        const shadowRoot1 = header.shadowRoot;
                        const technologist = shadowRoot1.querySelector('dhi-seds-nav-header-technologist');
                        const shadowRoot2 = technologist.shadowRoot;
                        const display = shadowRoot2.querySelector('dhi-seds-nav-header-display');
                        const shadowRoot3 = display.shadowRoot;
                        const searchLink = shadowRoot3.querySelector('a[href*="/jobs"]');
                        if (searchLink) {
                            searchLink.click();
                            return true;
                        }
                        return false;
                    """)

                    print("Clicked Search Jobs link, waiting for page load...")
                    time.sleep(5)

                    search_input = self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "input#typeaheadInput[data-cy='typeahead-input']"
                    )))

            if search_input:
                print(f"Entering search keyword: {keyword}")
                search_input.clear()
                time.sleep(1)

                for char in keyword:
                    search_input.send_keys(char)
                    time.sleep(0.1)

                time.sleep(1)
                search_input.send_keys(Keys.RETURN)
                time.sleep(3)

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
