from __future__ import annotations

import time
from collections.abc import Iterable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .handlers.job_handler import JobHandler
from .handlers.search_filter_handler import SearchAndFilter
from .handlers.shadow_dom_handler import ShadowDOMHandler
from .job_filters import DiceJobFilter
from .utils.humanizer import wait_for_document_ready


class DiceAutomation:
    def __init__(self, driver, wait, username, password, keywords, max_applications, humanizer):
        self.driver = driver
        self.wait = wait
        self.username = username
        self.password = password
        self.search_keywords = self._normalize_keywords(keywords)
        self.max_applications = max_applications
        self.humanizer = humanizer
        self.job_filter = DiceJobFilter()
        self.failed_applications: list[dict[str, str]] = []

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

    def _wait_for_visible(self, locators, timeout=None):
        wait = self.wait if timeout is None else type(self.wait)(self.driver, timeout)
        return wait.until(lambda driver: self._find_first_visible(locators))

    def _click_button(self, button_name, locators, fallback_keys=None):
        button = self._find_first_visible(locators)
        if button:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            self.humanizer.short_pause()
            self.driver.execute_script("arguments[0].click();", button)
            print(f"Clicked {button_name} button")
            self.humanizer.short_pause()
            return True

        if fallback_keys is not None:
            fallback_keys.send_keys(Keys.RETURN)
            print(f"Submitted {button_name} step with Enter")
            self.humanizer.short_pause()
            return True

        return False

    def _login_debug_summary(self):
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

    def _jobs_debug_summary(self):
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

    def _get_first_listing_url(self):
        try:
            job_listings = self._collect_visible_job_listings()
        except Exception:
            return ""

        for listing in job_listings:
            url = listing.get("url", "").strip()
            if url:
                return url

        return ""

    def _go_to_next_results_page(self):
        current_url = self.driver.current_url
        current_first_listing_url = self._get_first_listing_url()
        next_page_locators = [
            (By.CSS_SELECTOR, "a[aria-label*='Next']"),
            (By.CSS_SELECTOR, "button[aria-label*='Next']"),
            (By.CSS_SELECTOR, "a[rel='next']"),
            (
                By.XPATH,
                "//a[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
            ),
            (
                By.XPATH,
                "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
            ),
        ]

        next_button = self._find_first_visible(next_page_locators)
        if next_button is None:
            return False

        try:
            disabled_state = (
                (next_button.get_attribute("aria-disabled") or "").lower() == "true"
                or (next_button.get_attribute("disabled") is not None)
            )
        except Exception:
            disabled_state = False

        if disabled_state:
            return False

        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        self.humanizer.short_pause()
        self.driver.execute_script("arguments[0].click();", next_button)
        self.humanizer.short_pause()

        page_wait = type(self.wait)(self.driver, 10)
        try:
            page_wait.until(
                lambda driver: driver.current_url != current_url
                or self._get_first_listing_url() not in {"", current_first_listing_url}
            )
            try:
                wait_for_document_ready(self.driver, timeout=10)
            except Exception:
                pass
            self.humanizer.page_pause()
            return True
        except TimeoutException:
            refreshed_first_listing_url = self._get_first_listing_url()
            if (
                self.driver.current_url == current_url
                and refreshed_first_listing_url in {"", current_first_listing_url}
            ):
                return False

            self.humanizer.page_pause()
            return True

    def _collect_visible_job_listings(self):
        return self.driver.execute_script(
            """
            const anchors = Array.from(document.querySelectorAll("a[data-cy='card-title-link'], a.card-title-link, a[href*='/job-detail/'], a[href*='/jobs/'], a[href*='/job/']"));
            const seen = new Set();
            const jobs = [];

            for (const anchor of anchors) {
                const href = anchor.href || "";
                const parentCard = anchor.closest("article, li, [data-cy='search-result-card'], .card, .search-card");
                const titleNode = parentCard
                    ? parentCard.querySelector("a[data-cy='card-title-link'], a.card-title-link, h2, h3")
                    : null;
                let rawText = (anchor.innerText || anchor.textContent || anchor.getAttribute("aria-label") || "").trim();
                if (titleNode) {
                    rawText = (titleNode.innerText || titleNode.textContent || rawText).trim();
                }
                const isVisible = Boolean(anchor.offsetParent || anchor.getClientRects().length);
                const looksLikeJobLink = /\\/job-detail\\//i.test(href) || /\\/jobs\\//i.test(href) || /\\/job\\//i.test(href);
                const lowerText = rawText.toLowerCase();

                if (
                    !isVisible
                    || !looksLikeJobLink
                    || rawText.length < 8
                    || ["easy apply", "apply", "quick apply", "view details"].includes(lowerText)
                    || seen.has(href)
                ) {
                    continue;
                }

                seen.add(href);
                jobs.push({
                    title: rawText,
                    url: href
                });
            }

            return jobs;
            """
        )

    def login(self):
        """Handle login process"""
        email_locators = [
            (By.CSS_SELECTOR, "input[placeholder='Please enter your email']"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name='email']"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (
                By.XPATH,
                "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'email')]",
            ),
        ]
        continue_button_locators = [
            (By.XPATH, "//button[normalize-space()='Continue']"),
            (By.XPATH, "//button[.//span[normalize-space()='Continue']]"),
            (By.XPATH, "//button[@type='submit']"),
        ]
        password_locators = [
            (By.CSS_SELECTOR, "input[type='password']"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
            (
                By.XPATH,
                "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'password')]",
            ),
        ]
        sign_in_button_locators = [
            (By.XPATH, "//button[normalize-space()='Sign In']"),
            (By.XPATH, "//button[.//span[normalize-space()='Sign In']]"),
            (By.XPATH, "//button[@type='submit']"),
        ]

        try:
            print("Navigating to Dice login page...")
            self.driver.get("https://www.dice.com/dashboard/login")

            wait_for_document_ready(self.driver, timeout=45)
            self.humanizer.page_pause()
            print("Logging in...")

            email_input = self._wait_for_visible(email_locators, timeout=45)
            email_input.clear()
            email_input.send_keys(self.username)
            self.humanizer.short_pause()

            self._click_button("Continue", continue_button_locators, fallback_keys=email_input)
            password_input = self._wait_for_visible(password_locators, timeout=45)
            password_input.clear()
            password_input.send_keys(self.password)
            self.humanizer.short_pause()

            self._click_button("Sign In", sign_in_button_locators, fallback_keys=password_input)
            self.humanizer.page_pause()
            return True

        except TimeoutException:
            print("Login page did not become ready in time.")
            print(self._login_debug_summary())
            return False
        except Exception as e:
            print(f"Login failed: {str(e)}")
            print(self._login_debug_summary())
            return False

    def get_job_listings(self):
        """Get all job listings from the current page"""
        end_time = time.time() + 15
        while time.time() < end_time:
            try:
                job_listings = self._collect_visible_job_listings()
                if job_listings:
                    return job_listings

                body_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(
                    phrase in body_text
                    for phrase in (
                        "no jobs found",
                        "no matching jobs",
                        "no results",
                        "try removing filters",
                    )
                ):
                    return []
            except Exception as e:
                print(f"Error reading job listings: {str(e)}")

            time.sleep(0.5)

        print("Timed out waiting for visible job listings.")
        print(self._jobs_debug_summary())
        return []

    def _record_failed_application(self, title: str, url: str, reason: str) -> None:
        normalized_title = title or "Unknown job"
        normalized_url = url or "URL unavailable"
        normalized_reason = reason or "unknown error"
        self.failed_applications.append(
            {
                "title": normalized_title,
                "url": normalized_url,
                "reason": normalized_reason,
            }
        )

    def _print_failed_application_summary(self) -> None:
        if not self.failed_applications:
            print("\nDice failure summary: no failed applications were recorded.")
            return

        print(f"\nDice failure summary: {len(self.failed_applications)} job(s) could not be applied.")
        for index, failed_job in enumerate(self.failed_applications, start=1):
            print(
                f"{index}. {failed_job['title']} | {failed_job['url']} | {failed_job['reason']}"
            )

    def _process_search_results(self, keyword, job_handler, seen_urls, remaining_applications):
        applications_submitted = 0
        jobs_processed = 0
        page_index = 1
        max_jobs_to_scan = max(remaining_applications * 10, 60)

        while applications_submitted < remaining_applications and jobs_processed < max_jobs_to_scan:
            print(f"Collecting filtered job listings for '{keyword}' from results page {page_index}...")
            job_listings = self.get_job_listings()
            if not job_listings:
                if jobs_processed == 0:
                    print(f"No jobs found with current filters for '{keyword}'")
                else:
                    print(f"No more job listings found for '{keyword}' on subsequent pages")
                break

            print(f"Found {len(job_listings)} visible job links on page {page_index}")
            fresh_job_listings = []
            for listing in job_listings:
                url = listing.get("url", "").strip()
                if not url or url in seen_urls:
                    continue

                fresh_job_listings.append({
                    "title": listing.get("title", "Unknown job"),
                    "url": url,
                })

            if page_index == 1:
                print("Dice may report more total jobs than are visible on one page. The automation will keep paging automatically.")

            if not fresh_job_listings:
                print("No new job links found on this page.")
            else:
                print(f"Queued {len(fresh_job_listings)} new job links from page {page_index}")

            for listing in fresh_job_listings:
                if (
                    applications_submitted >= remaining_applications
                    or jobs_processed >= max_jobs_to_scan
                ):
                    break

                title = "Unknown job"
                url = ""
                try:
                    title = listing.get("title", "Unknown job")
                    url = listing.get("url", "")
                    seen_urls.add(url)

                    title_filter_decision = self.job_filter.evaluate_title_only(title)
                    if title_filter_decision.should_skip:
                        print(
                            f"Skipping job due to smart title filter ({title_filter_decision.reason}): "
                            f"{title} | {url}"
                        )
                        jobs_processed += 1
                        continue

                    print(f"\nTrying job {jobs_processed + 1} for '{keyword}': {title}")

                    self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                    self.humanizer.short_pause()

                    application_result = job_handler.apply_to_job(title, url)
                    if application_result.was_submitted:
                        applications_submitted += 1
                    elif application_result.is_failure:
                        self._record_failed_application(
                            title,
                            url,
                            application_result.reason,
                        )

                    jobs_processed += 1
                    self.humanizer.short_pause()

                except Exception as e:
                    message = str(e)
                    print(f"Error processing job listing: {message}")
                    self._record_failed_application(title, url, message)
                    jobs_processed += 1
                    continue

            if applications_submitted >= remaining_applications or jobs_processed >= max_jobs_to_scan:
                break

            print("Trying to move to the next results page...")
            if not self._go_to_next_results_page():
                print("No additional results pages found")
                break

            page_index += 1
            self.humanizer.page_pause()

        if jobs_processed >= max_jobs_to_scan and applications_submitted < remaining_applications:
            print(f"Reached the scan limit of {max_jobs_to_scan} listings for '{keyword}' before hitting the application target.")

        return applications_submitted, jobs_processed

    def run(self):
        """Main method to run the automation"""
        try:
            if not self.login():
                raise Exception("Login failed")

            if not self.search_keywords:
                raise Exception("No valid search keywords were provided")

            search_filter = SearchAndFilter(self.driver, self.wait, self.humanizer)
            shadow_dom_handler = ShadowDOMHandler(self.driver, self.wait, self.humanizer)
            job_handler = JobHandler(
                self.driver,
                self.wait,
                shadow_dom_handler,
                self.humanizer,
                eligibility_filter=self.job_filter,
            )

            applications_submitted = 0
            jobs_processed = 0
            seen_urls = set()

            for keyword_index, keyword in enumerate(self.search_keywords, start=1):
                if applications_submitted >= self.max_applications:
                    break

                print(f"\nStarting search {keyword_index}/{len(self.search_keywords)} with keyword: {keyword}")
                if not search_filter.perform_search(keyword):
                    print(f"Skipping keyword because search failed: {keyword}")
                    continue

                if not search_filter.apply_filters():
                    print(f"Skipping keyword because filters could not be applied: {keyword}")
                    continue

                keyword_applications, keyword_jobs_processed = self._process_search_results(
                    keyword,
                    job_handler,
                    seen_urls,
                    self.max_applications - applications_submitted,
                )
                applications_submitted += keyword_applications
                jobs_processed += keyword_jobs_processed

            print(f"\nCompleted! Applied to {applications_submitted} jobs, processed {jobs_processed} listings")
            self._print_failed_application_summary()

        except Exception as e:
            print(f"An error occurred: {str(e)}")
            self._print_failed_application_summary()
