import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC

from ..utils.humanizer import wait_for_document_ready


class SearchAndFilter:
    EMPTY_RESULTS_MARKERS = (
        "no jobs found",
        "no matching jobs",
        "no results",
        "try removing filters",
    )

    def __init__(self, driver, wait, humanizer):
        self.driver = driver
        self.wait = wait
        self.humanizer = humanizer

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

    def _get_results_snapshot(self):
        return self.driver.execute_script(
            """
            const emptyMarkers = arguments[0];
            const anchors = Array.from(document.querySelectorAll(
                "a[data-cy='card-title-link'], a.card-title-link, a[href*='/job-detail/'], a[href*='/jobs/'], a[href*='/job/']"
            ));
            const seen = new Set();
            const jobs = [];
            const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));

            for (const anchor of anchors) {
                const href = anchor.href || "";
                const text = (anchor.innerText || anchor.textContent || anchor.getAttribute("aria-label") || "").trim();
                const looksLikeJobLink = /\\/job-detail\\//i.test(href) || /\\/jobs\\//i.test(href) || /\\/job\\//i.test(href);

                if (!isVisible(anchor) || !looksLikeJobLink || text.length < 8 || seen.has(href)) {
                    continue;
                }

                seen.add(href);
                jobs.push(href);
                if (jobs.length >= 3) {
                    break;
                }
            }

            const bodyText = (document.body?.innerText || "").toLowerCase();
            return {
                url: window.location.href,
                firstListingUrl: jobs[0] || "",
                listingCount: jobs.length,
                noResults: emptyMarkers.some((marker) => bodyText.includes(marker)),
            };
            """,
            list(self.EMPTY_RESULTS_MARKERS),
        )

    def _wait_for_results(self, previous_snapshot=None, timeout=20):
        active_wait = type(self.wait)(self.driver, timeout)

        def results_ready(_driver):
            snapshot = self._get_results_snapshot()
            if not (snapshot["listingCount"] > 0 or snapshot["noResults"]):
                return False

            if previous_snapshot is None:
                return snapshot

            if (
                snapshot["url"] != previous_snapshot["url"]
                or snapshot["firstListingUrl"] != previous_snapshot["firstListingUrl"]
                or snapshot["noResults"] != previous_snapshot["noResults"]
                or (
                    previous_snapshot["listingCount"] == 0
                    and snapshot["listingCount"] > 0
                )
            ):
                return snapshot

            return False

        try:
            return active_wait.until(results_ready)
        except TimeoutException:
            snapshot = self._get_results_snapshot()
            if snapshot["listingCount"] > 0 or snapshot["noResults"]:
                return snapshot
            raise

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

    def _click_filter_with_script(self, search_text, click_if_needed):
        result = self.driver.execute_script(
            """
            const target = arguments[0].toLowerCase();
            const clickIfNeeded = arguments[1];
            const selectors = [
                "[data-cy*='filter'] button",
                "[data-cy*='filter'] label",
                "[data-testid*='filter'] button",
                "[data-testid*='filter'] label",
                "aside button",
                "aside label",
                "[role='dialog'] button",
                "[role='dialog'] label",
                "button",
                "label",
                "[role='checkbox']",
                "[role='radio']",
                "[role='button']",
                "input[type='checkbox']",
                "input[type='radio']"
            ];
            const candidates = [];
            const seen = new Set();
            const normalize = (value) => (value || "").toLowerCase().replace(/\\s+/g, " ").trim();
            const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));

            const isSelected = (node) => {
                const ariaState = ["aria-checked", "aria-pressed", "aria-selected"]
                    .some((name) => (node.getAttribute(name) || "").toLowerCase() === "true");
                const classTokens = (node.className || "").toLowerCase().replace(/,/g, " ").split(/\s+/);
                const classState = classTokens.some((token) => ["active", "selected", "checked"].includes(token));
                return ariaState || classState || node.checked === true;
            };

            for (const selector of selectors) {
                for (const candidate of document.querySelectorAll(selector)) {
                    if (seen.has(candidate)) {
                        continue;
                    }
                    seen.add(candidate);
                    candidates.push(candidate);
                }
            }

            let bestMatch = null;
            let bestScore = -1;

            for (const candidate of candidates) {
                if (!isVisible(candidate)) {
                    continue;
                }

                const clickable = candidate.closest("button, label, [role='checkbox'], [role='radio'], [role='button']") || candidate;
                const text = normalize([
                    candidate.innerText,
                    candidate.textContent,
                    candidate.getAttribute("aria-label"),
                    candidate.value,
                    clickable.innerText,
                    clickable.textContent,
                    clickable.getAttribute("aria-label"),
                    clickable.value
                ].filter(Boolean).join(" "));

                if (!text.includes(target)) {
                    continue;
                }

                let score = 0;
                if (text === target) {
                    score += 4;
                }
                if (text.startsWith(`${target} `) || text.endsWith(` ${target}`)) {
                    score += 2;
                }
                if (clickable.closest("aside, [data-cy*='filter'], [data-testid*='filter'], [aria-label*='filter']")) {
                    score += 2;
                }
                if (isSelected(candidate) || isSelected(clickable)) {
                    score += 1;
                }

                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = {
                        clickable,
                        selected: isSelected(candidate) || isSelected(clickable),
                    };
                }
            }

            if (!bestMatch) {
                return "not_found";
            }

            if (bestMatch.selected) {
                return "already_selected";
            }

            if (!clickIfNeeded) {
                return "found";
            }

            bestMatch.clickable.scrollIntoView({ block: "center" });
            bestMatch.clickable.click();
            return "clicked";
            """,
            search_text,
            click_if_needed,
        )

        return str(result)

    def _wait_for_filter_selected(self, search_text, timeout=10):
        active_wait = type(self.wait)(self.driver, timeout)
        try:
            active_wait.until(
                lambda _driver: self._click_filter_with_script(search_text, click_if_needed=False) == "already_selected"
            )
        except TimeoutException:
            return False

        return True

    def _apply_filter(self, filter_name, search_text, locators):
        print(f"Looking for {filter_name} filter...")

        previous_snapshot = self._get_results_snapshot()
        script_result = self._click_filter_with_script(search_text, click_if_needed=True)

        if script_result == "already_selected":
            print(f"{filter_name} filter already selected")
            return True

        if script_result == "clicked":
            self.humanizer.short_pause()
            self._wait_for_filter_selected(search_text, timeout=10)
            try:
                self._wait_for_results(previous_snapshot, timeout=12)
            except TimeoutException:
                pass
            print(f"{filter_name} filter applied")
            return True

        try:
            quick_wait = type(self.wait)(self.driver, 4)
            element = quick_wait.until(lambda driver: self._find_first_displayed_element(locators))

            if self._is_filter_selected(element):
                print(f"{filter_name} filter already selected")
                return True

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.humanizer.short_pause()
            self.driver.execute_script("arguments[0].click();", element)
            self.humanizer.short_pause()
            self._wait_for_filter_selected(search_text, timeout=10)
            try:
                self._wait_for_results(previous_snapshot, timeout=12)
            except TimeoutException:
                pass
            print(f"{filter_name} filter applied")
            return True
        except Exception:
            return self._click_filter_with_script(search_text, click_if_needed=True) in {"clicked", "already_selected"}

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
                    wait_for_document_ready(self.driver, timeout=30)
                    self.humanizer.page_pause()

                    print("Waiting for search box to appear...")
                    search_input = self._wait_for_search_input(timeout=20)
                    print("Search box found after navigation")

                except Exception:
                    print("Trying shadow DOM navigation...")
                    clicked_search_link = self._navigate_to_jobs_via_shadow_dom()
                    if not clicked_search_link:
                        raise Exception("Search Jobs link was not available in the header shadow DOM")

                    print("Clicked Search Jobs link, waiting for page load...")
                    wait_for_document_ready(self.driver, timeout=30)
                    self.humanizer.page_pause()
                    search_input = self._wait_for_search_input(timeout=20)

            if search_input:
                print(f"Entering search keyword: {keyword}")
                previous_snapshot = self._get_results_snapshot()
                search_input.click()
                self.humanizer.short_pause()
                search_input.send_keys(Keys.CONTROL, "a")
                self.humanizer.short_pause()
                search_input.send_keys(Keys.DELETE)
                self.humanizer.short_pause()
                search_input.send_keys(keyword)

                self.humanizer.short_pause()
                search_input.send_keys(Keys.RETURN)
                self.humanizer.short_pause()

                try:
                    self._wait_for_results(previous_snapshot, timeout=20)
                except TimeoutException:
                    self.wait.until(EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "a[data-cy='card-title-link']"
                    )))

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
