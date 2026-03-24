from __future__ import annotations

import time
from collections.abc import Iterable
from urllib.parse import urlencode

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from .utils.humanizer import wait_for_document_ready


class LinkedInAutomation:
    RESULTS_PAGE_SIZE = 25
    EMPTY_RESULTS_MARKERS = (
        "no matching jobs found",
        "no jobs found",
        "try broadening your search",
        "we couldn't find a match",
        "there are no jobs that match your search",
    )

    def __init__(self, driver, wait, username, password, keywords, max_applications, humanizer):
        self.driver = driver
        self.wait = wait
        self.username = username
        self.password = password
        self.search_keywords = self._normalize_keywords(keywords)
        self.max_applications = max_applications
        self.humanizer = humanizer

    def _normalize_keywords(self, keywords):
        if isinstance(keywords, str):
            return [keywords.strip()] if keywords.strip() else []

        if isinstance(keywords, Iterable):
            normalized_keywords = []
            for keyword in keywords:
                normalized_keyword = str(keyword).strip()
                if normalized_keyword:
                    normalized_keywords.append(normalized_keyword)
            return normalized_keywords

        return []

    def _normalize_job_url(self, url: str) -> str:
        return str(url or "").split("?", 1)[0].strip()

    def _is_interactable(self, element) -> bool:
        try:
            if not element.is_displayed():
                return False
        except Exception:
            return False

        try:
            disabled = (
                (element.get_attribute("disabled") is not None)
                or (element.get_attribute("aria-disabled") or "").lower() == "true"
            )
            return not disabled
        except Exception:
            return True

    def _find_first_visible(self, locators, require_interactable=False):
        for by, value in locators:
            try:
                elements = self.driver.find_elements(by, value)
            except Exception:
                continue

            for element in elements:
                try:
                    if not element.is_displayed():
                        continue
                    if require_interactable and not self._is_interactable(element):
                        continue
                    return element
                except Exception:
                    continue

        return None

    def _wait_for_visible(self, locators, timeout=None, require_interactable=False):
        active_wait = self.wait if timeout is None else type(self.wait)(self.driver, timeout)
        return active_wait.until(
            lambda _driver: self._find_first_visible(
                locators,
                require_interactable=require_interactable,
            )
        )

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

    def _build_search_url(self, keyword, start=0):
        query_params = [
            ("keywords", keyword),
            ("f_AL", "true"),
            ("f_JT", "C"),
            ("f_TPR", "r86400"),
        ]
        if start:
            query_params.append(("start", str(start)))
        return f"https://www.linkedin.com/jobs/search/?{urlencode(query_params)}"

    def _hydrate_results_list(self, passes=5):
        for _ in range(passes):
            try:
                self.driver.execute_script(
                    """
                    const candidates = Array.from(document.querySelectorAll(
                        ".jobs-search-results-list, .jobs-search-results-list__list, .scaffold-layout__list, ul.scaffold-layout__list-container"
                    ));
                    const container = candidates.find((node) => node && node.scrollHeight > node.clientHeight + 80)
                        || document.scrollingElement;
                    if (!container) {
                        return false;
                    }

                    container.scrollTop = container.scrollHeight;
                    return true;
                    """
                )
            except Exception:
                return

            time.sleep(0.2)

    def _collect_visible_job_listings(self):
        job_listings = self.driver.execute_script(
            """
            const resultsRoot = document.querySelector(
                ".jobs-search-results-list, .jobs-search__results-list, ul.scaffold-layout__list-container"
            ) || document;
            const anchors = Array.from(resultsRoot.querySelectorAll(
                "a[href*='/jobs/view/'], a.job-card-container__link, a.job-card-list__title"
            ));
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
            const seen = new Set();
            const jobs = [];

            for (const anchor of anchors) {
                const href = (anchor.href || "").split("?")[0];
                if (!href || seen.has(href) || !/\\/jobs\\/view\\//i.test(href)) {
                    continue;
                }

                const card = anchor.closest(
                    "li, .jobs-search-results__list-item, .scaffold-layout__list-item, .job-card-container"
                ) || anchor.parentElement;

                const titleNode = card
                    ? card.querySelector(
                        "a.job-card-list__title, a.job-card-container__link, strong, h3, .job-card-list__title"
                    )
                    : anchor;
                const title = normalize(
                    (titleNode && (titleNode.innerText || titleNode.textContent))
                    || anchor.innerText
                    || anchor.textContent
                    || anchor.getAttribute("aria-label")
                );

                if (title.length < 4) {
                    continue;
                }

                const summary = normalize(card ? (card.innerText || card.textContent) : title);
                const lowerSummary = summary.toLowerCase();
                seen.add(href);
                jobs.push({
                    title,
                    url: href,
                    summary,
                    reposted: /\\breposted\\b/i.test(lowerSummary),
                    alreadyApplied: /\\bapplied\\b/i.test(lowerSummary),
                });
            }

            return jobs;
            """
        )

        for listing in job_listings:
            listing["url"] = self._normalize_job_url(listing.get("url", ""))

        return job_listings

    def _get_results_snapshot(self):
        try:
            job_listings = self._collect_visible_job_listings()
        except Exception:
            job_listings = []

        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            body_text = ""

        return {
            "url": self.driver.current_url,
            "firstListingUrl": job_listings[0]["url"] if job_listings else "",
            "listingCount": len(job_listings),
            "noResults": any(marker in body_text for marker in self.EMPTY_RESULTS_MARKERS),
        }

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

    def _go_to_results_page(self, keyword, page_index):
        previous_snapshot = self._get_results_snapshot()
        previous_first_listing = previous_snapshot["firstListingUrl"]
        target_url = self._build_search_url(
            keyword,
            start=max(page_index - 1, 0) * self.RESULTS_PAGE_SIZE,
        )

        self.driver.get(target_url)
        try:
            wait_for_document_ready(self.driver, timeout=25)
        except Exception:
            pass

        try:
            snapshot = self._wait_for_results(previous_snapshot, timeout=20)
        except TimeoutException:
            snapshot = self._get_results_snapshot()

        if snapshot["noResults"] or snapshot["listingCount"] == 0:
            return False

        if page_index > 1 and snapshot["firstListingUrl"] == previous_first_listing:
            return False

        self.humanizer.page_pause()
        return True

    def login(self):
        email_locators = [
            (By.CSS_SELECTOR, "input#username"),
            (By.CSS_SELECTOR, "input[name='session_key']"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.CSS_SELECTOR, "input[type='email']"),
        ]
        password_locators = [
            (By.CSS_SELECTOR, "input#password"),
            (By.CSS_SELECTOR, "input[name='session_password']"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ]
        sign_in_button_locators = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (
                By.XPATH,
                "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
            ),
        ]

        try:
            print("Navigating to LinkedIn login page...")
            self.driver.get("https://www.linkedin.com/login")
            wait_for_document_ready(self.driver, timeout=45)
            self.humanizer.page_pause()

            try:
                email_input = self._wait_for_visible(email_locators, timeout=20, require_interactable=True)
            except TimeoutException:
                current_url = self.driver.current_url.lower()
                if "/feed" in current_url or "/jobs" in current_url:
                    print("LinkedIn session is already active")
                    self.driver.get("https://www.linkedin.com/jobs/")
                    wait_for_document_ready(self.driver, timeout=30)
                    self.humanizer.page_pause()
                    return True
                print("LinkedIn login form did not appear in time.")
                print(self._page_debug_summary())
                return False

            password_input = self._wait_for_visible(password_locators, timeout=20, require_interactable=True)
            email_input.clear()
            email_input.send_keys(self.username)
            self.humanizer.micro_pause()
            password_input.clear()
            password_input.send_keys(self.password)
            self.humanizer.micro_pause()

            sign_in_button = self._wait_for_visible(
                sign_in_button_locators,
                timeout=10,
                require_interactable=True,
            )
            self.driver.execute_script("arguments[0].click();", sign_in_button)

            post_login_wait = type(self.wait)(self.driver, 45)
            post_login_wait.until(
                lambda driver: (
                    "/feed" in driver.current_url.lower()
                    or "/jobs" in driver.current_url.lower()
                    or "/checkpoint/" in driver.current_url.lower()
                )
            )

            if "/checkpoint/" in self.driver.current_url.lower():
                print("LinkedIn requested additional verification. Complete it manually and rerun.")
                print(self._page_debug_summary())
                return False

            self.driver.get("https://www.linkedin.com/jobs/")
            wait_for_document_ready(self.driver, timeout=30)
            self.humanizer.page_pause()
            print("LinkedIn login completed")
            return True

        except TimeoutException:
            print("LinkedIn login timed out.")
            print(self._page_debug_summary())
            return False
        except Exception as e:
            print(f"LinkedIn login failed: {str(e)}")
            print(self._page_debug_summary())
            return False

    def perform_search(self, keyword):
        try:
            print(
                f"Opening LinkedIn search for '{keyword}' with Easy Apply, Contract, and Past 24 hours filters..."
            )
            previous_snapshot = self._get_results_snapshot()
            self.driver.get(self._build_search_url(keyword))
            wait_for_document_ready(self.driver, timeout=30)
            self._wait_for_results(previous_snapshot, timeout=25)
            self.humanizer.page_pause()
            return True
        except TimeoutException:
            print(f"LinkedIn search timed out for '{keyword}'")
            print(self._page_debug_summary())
            return False
        except Exception as e:
            print(f"Error performing LinkedIn search for '{keyword}': {str(e)}")
            print(self._page_debug_summary())
            return False

    def get_job_listings(self):
        end_time = time.time() + 12
        while time.time() < end_time:
            try:
                self._hydrate_results_list()
                job_listings = self._collect_visible_job_listings()
                if job_listings:
                    return job_listings

                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(marker in body_text for marker in self.EMPTY_RESULTS_MARKERS):
                    return []
            except Exception as e:
                print(f"Error reading LinkedIn job listings: {str(e)}")

            time.sleep(0.25)

        print("Timed out waiting for LinkedIn job listings.")
        print(self._page_debug_summary())
        return []

    def _find_easy_apply_button(self):
        locators = [
            (By.CSS_SELECTOR, "button.jobs-apply-button"),
            (By.CSS_SELECTOR, "button[aria-label*='Easy Apply']"),
            (By.CSS_SELECTOR, "button[aria-label*='easy apply']"),
            (
                By.XPATH,
                "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]",
            ),
            (
                By.XPATH,
                "//*[@role='button' and contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'easy apply')]",
            ),
        ]

        for by, value in locators:
            try:
                elements = self.driver.find_elements(by, value)
            except Exception:
                continue

            for element in elements:
                if not self._is_interactable(element):
                    continue

                try:
                    text = " ".join(
                        filter(
                            None,
                            [
                                element.text,
                                element.get_attribute("aria-label"),
                                element.get_attribute("textContent"),
                            ],
                        )
                    ).lower()
                except Exception:
                    text = ""

                if "easy apply" in text:
                    return element

        return None

    def _has_existing_application(self):
        exact_terms = ["applied"]
        phrase_terms = [
            "already applied",
            "application submitted",
            "you've applied",
            "you have applied",
            "application sent",
            "submitted application",
        ]

        try:
            marker = self.driver.execute_script(
                """
                const exactTerms = arguments[0];
                const phraseTerms = arguments[1];
                const normalize = (value) => (value || "").toLowerCase().replace(/\\s+/g, " ").trim();
                const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));
                const candidates = document.querySelectorAll(
                    "button, a, [role='button'], [aria-label], span, div"
                );

                for (const candidate of candidates) {
                    if (!isVisible(candidate)) {
                        continue;
                    }

                    const text = normalize([
                        candidate.innerText,
                        candidate.textContent,
                        candidate.getAttribute("aria-label"),
                        candidate.value
                    ].filter(Boolean).join(" "));

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

                return "";
                """,
                exact_terms,
                phrase_terms,
            )
        except Exception:
            return False

        return bool(marker)

    def _is_application_complete(self):
        try:
            body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        except Exception:
            return False

        success_markers = (
            "application submitted",
            "your application was sent",
            "you've applied",
            "application sent",
            "thanks for applying",
        )
        return any(marker in body_text for marker in success_markers)

    def _wait_for_application_modal(self, timeout=10):
        locators = [
            (By.CSS_SELECTOR, "div[role='dialog']"),
            (By.CSS_SELECTOR, "dialog"),
            (By.CSS_SELECTOR, ".jobs-easy-apply-modal"),
            (By.CSS_SELECTOR, ".artdeco-modal"),
        ]
        return self._wait_for_visible(locators, timeout=timeout)

    def _click_modal_action(self, actions, timeout=5):
        normalized_actions = [
            {"name": name, "variants": [variant.lower() for variant in text_variants]}
            for name, text_variants in actions
        ]

        clicked_action = self.driver.execute_script(
            """
            const actions = arguments[0];
            const normalize = (value) => (value || "").toLowerCase().replace(/\\s+/g, " ").trim();
            const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));
            const isDisabled = (node) => Boolean(
                !node
                || node.disabled === true
                || (node.getAttribute("disabled") !== null)
                || normalize(node.getAttribute("aria-disabled")) === "true"
            );
            const dialogRoots = Array.from(
                document.querySelectorAll("[role='dialog'], dialog, .jobs-easy-apply-modal, .artdeco-modal")
            ).filter(isVisible);
            const queue = dialogRoots.length ? [...dialogRoots] : [document];
            const visited = new Set();

            while (queue.length) {
                const root = queue.shift();
                if (!root || visited.has(root)) {
                    continue;
                }
                visited.add(root);

                const candidates = root.querySelectorAll(
                    "button, a, [role='button'], input[type='submit'], input[type='button'], span"
                );

                for (const candidate of candidates) {
                    const clickable = candidate.closest(
                        "button, a, [role='button'], input[type='submit'], input[type='button']"
                    ) || candidate;

                    if (!isVisible(clickable) || isDisabled(clickable)) {
                        continue;
                    }

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

                    if (!text) {
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
            }

            return "";
            """,
            normalized_actions,
        )

        if clicked_action:
            print(f"Clicked {clicked_action} button")
            self.humanizer.micro_pause()
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

                button = self._find_first_visible(locators, require_interactable=True)
                if button is None:
                    continue

                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                self.humanizer.micro_pause()
                self.driver.execute_script("arguments[0].click();", button)
                print(f"Clicked {action['name']} button")
                self.humanizer.micro_pause()
                return action["name"]

            time.sleep(0.2)

        return None

    def _modal_blocking_reason(self):
        try:
            return str(
                self.driver.execute_script(
                    """
                    const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
                    const isVisible = (node) => Boolean(node && (node.offsetParent || node.getClientRects().length));
                    const dialogs = Array.from(
                        document.querySelectorAll("[role='dialog'], dialog, .jobs-easy-apply-modal, .artdeco-modal")
                    ).filter(isVisible);
                    if (!dialogs.length) {
                        return "";
                    }

                    const dialog = dialogs[dialogs.length - 1];
                    const explicitError = Array.from(dialog.querySelectorAll(
                        "[aria-invalid='true'], .artdeco-inline-feedback__message, .jobs-easy-apply-form-element__error"
                    )).find(isVisible);
                    if (explicitError) {
                        return normalize(
                            explicitError.innerText
                            || explicitError.textContent
                            || explicitError.getAttribute("aria-label")
                        );
                    }

                    const requiredFields = Array.from(dialog.querySelectorAll("input, textarea, select")).filter((field) => {
                        if (!isVisible(field)) {
                            return false;
                        }

                        const type = normalize(field.type).toLowerCase();
                        if (["hidden", "submit", "button", "checkbox", "radio"].includes(type)) {
                            return false;
                        }

                        const required = field.required === true || normalize(field.getAttribute("aria-required")).toLowerCase() === "true";
                        const value = normalize(field.value);
                        return required && !value;
                    });
                    if (requiredFields.length) {
                        return "required fields need manual input";
                    }

                    const uploadPrompt = Array.from(dialog.querySelectorAll("input[type='file'], button, span, div")).find((node) => {
                        if (!isVisible(node)) {
                            return false;
                        }

                        const text = normalize(
                            node.innerText
                            || node.textContent
                            || node.getAttribute("aria-label")
                            || node.value
                        ).toLowerCase();
                        return text.includes("upload resume") || text.includes("upload cover letter");
                    });
                    if (uploadPrompt) {
                        return "resume upload is required";
                    }

                    return "";
                    """
                )
            ).strip()
        except Exception:
            return ""

    def apply_to_job(self, job_title="", job_url=""):
        new_tab = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_tab)

        try:
            print("Waiting for LinkedIn job page to load...")
            try:
                wait_for_document_ready(self.driver, timeout=25)
            except Exception:
                pass
            self.humanizer.page_pause()

            if self._has_existing_application():
                print(f"Skipping LinkedIn job - already applied: {job_title} | {job_url}")
                return False

            easy_apply_button = self._find_easy_apply_button()
            if easy_apply_button is None:
                print(f"Skipping LinkedIn job - Easy Apply was not available: {job_title} | {job_url}")
                return False

            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", easy_apply_button)
            self.humanizer.micro_pause()
            self.driver.execute_script("arguments[0].click();", easy_apply_button)
            self.humanizer.micro_pause()

            try:
                self._wait_for_application_modal(timeout=10)
            except TimeoutException:
                if self._has_existing_application() or self._is_application_complete():
                    print(f"Application submitted: {job_title}")
                    return True
                print(f"LinkedIn application modal did not open: {job_title} | {job_url}")
                print(self._page_debug_summary())
                return False

            prioritized_actions = [
                ("Submit", ["submit application", "submit", "send application"]),
                ("Review", ["review your application", "review application", "review"]),
                ("Next", ["continue to next step", "next", "continue"]),
            ]

            for _ in range(8):
                if self._is_application_complete() or self._has_existing_application():
                    print(f"Application submitted: {job_title}")
                    return True

                clicked_action = self._click_modal_action(prioritized_actions, timeout=4)
                if clicked_action in {"Next", "Review"}:
                    self.humanizer.short_pause()
                    continue

                if clicked_action == "Submit":
                    self.humanizer.page_pause()
                    if self._is_application_complete() or self._has_existing_application():
                        print(f"Application submitted: {job_title}")
                    else:
                        print(f"Submit clicked for LinkedIn job: {job_title}")
                    return True

                blocking_reason = self._modal_blocking_reason()
                if blocking_reason:
                    print(f"Skipping LinkedIn job - manual input required: {job_title} | {blocking_reason}")
                else:
                    print(f"Could not find another LinkedIn application action button: {job_title} | {job_url}")
                    print(self._page_debug_summary())
                return False

            print(f"Reached the maximum LinkedIn application step count for: {job_title} | {job_url}")
            print(self._page_debug_summary())
            return False

        except Exception as e:
            message = getattr(e, "msg", str(e)).splitlines()[0]
            print(f"Could not process LinkedIn job: {job_title} | {job_url} | {message}")
            print(self._page_debug_summary())
            return False
        finally:
            print("Closing LinkedIn job tab...")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            self.humanizer.micro_pause()

    def _process_search_results(self, keyword, seen_urls, remaining_applications):
        applications_submitted = 0
        jobs_processed = 0
        page_index = 1
        max_jobs_to_scan = max(remaining_applications * 12, 75)

        while applications_submitted < remaining_applications and jobs_processed < max_jobs_to_scan:
            if page_index > 1:
                print(f"Opening LinkedIn results page {page_index} for '{keyword}'...")
                if not self._go_to_results_page(keyword, page_index):
                    print("No additional LinkedIn results pages found")
                    break

            print(f"Collecting LinkedIn job listings for '{keyword}' from results page {page_index}...")
            job_listings = self.get_job_listings()
            if not job_listings:
                if jobs_processed == 0:
                    print(f"No LinkedIn jobs found with current filters for '{keyword}'")
                else:
                    print(f"No more LinkedIn job listings found for '{keyword}'")
                break

            print(f"Found {len(job_listings)} visible LinkedIn job links on page {page_index}")
            fresh_job_listings = []
            for listing in job_listings:
                url = self._normalize_job_url(listing.get("url", ""))
                if not url or url in seen_urls:
                    continue

                fresh_job_listings.append({
                    "title": listing.get("title", "Unknown job"),
                    "url": url,
                    "summary": listing.get("summary", ""),
                    "reposted": bool(listing.get("reposted", False)),
                    "already_applied": bool(listing.get("alreadyApplied", False)),
                })

            if not fresh_job_listings:
                print("No new LinkedIn job links found on this page.")
            else:
                print(f"Queued {len(fresh_job_listings)} new LinkedIn job links from page {page_index}")

            for listing in fresh_job_listings:
                if (
                    applications_submitted >= remaining_applications
                    or jobs_processed >= max_jobs_to_scan
                ):
                    break

                title = listing["title"]
                url = listing["url"]
                seen_urls.add(url)

                if listing["reposted"]:
                    print(f"Skipping LinkedIn reposted job: {title} | {url}")
                    jobs_processed += 1
                    continue

                if listing["already_applied"]:
                    print(f"Skipping LinkedIn job marked as applied: {title} | {url}")
                    jobs_processed += 1
                    continue

                print(f"\nTrying LinkedIn job {jobs_processed + 1} for '{keyword}': {title}")
                self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                self.humanizer.micro_pause()

                if self.apply_to_job(title, url):
                    applications_submitted += 1

                jobs_processed += 1
                self.humanizer.short_pause()

            if applications_submitted >= remaining_applications or jobs_processed >= max_jobs_to_scan:
                break

            if len(job_listings) < self.RESULTS_PAGE_SIZE:
                print("Reached the last visible LinkedIn results page")
                break

            page_index += 1

        if jobs_processed >= max_jobs_to_scan and applications_submitted < remaining_applications:
            print(
                f"Reached the LinkedIn scan limit of {max_jobs_to_scan} listings for '{keyword}' before hitting the application target."
            )

        return applications_submitted, jobs_processed

    def run(self):
        try:
            if not self.login():
                raise Exception("LinkedIn login failed")

            if not self.search_keywords:
                raise Exception("No valid search keywords were provided")

            applications_submitted = 0
            jobs_processed = 0
            seen_urls = set()

            for keyword_index, keyword in enumerate(self.search_keywords, start=1):
                if applications_submitted >= self.max_applications:
                    break

                print(
                    f"\nStarting LinkedIn search {keyword_index}/{len(self.search_keywords)} with keyword: {keyword}"
                )
                if not self.perform_search(keyword):
                    print(f"Skipping LinkedIn keyword because search failed: {keyword}")
                    continue

                keyword_applications, keyword_jobs_processed = self._process_search_results(
                    keyword,
                    seen_urls,
                    self.max_applications - applications_submitted,
                )
                applications_submitted += keyword_applications
                jobs_processed += keyword_jobs_processed

            print(
                f"\nLinkedIn completed! Applied to {applications_submitted} jobs, processed {jobs_processed} listings"
            )

        except Exception as e:
            print(f"LinkedIn automation error: {str(e)}")
