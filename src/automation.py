from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException
import time

from .handlers.shadow_dom_handler import ShadowDOMHandler
from .handlers.job_handler import JobHandler
from .handlers.search_filter_handler import SearchAndFilter

class DiceAutomation:
    def __init__(self, driver, wait, username, password, keyword, max_applications):
        self.driver = driver
        self.wait = wait
        self.username = username
        self.password = password
        self.search_keyword = keyword
        self.max_applications = max_applications

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
            self.driver.execute_script("arguments[0].click();", button)
            print(f"Clicked {button_name} button")
            return True

        if fallback_keys is not None:
            fallback_keys.send_keys(Keys.RETURN)
            print(f"Submitted {button_name} step with Enter")
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

    def _collect_visible_job_listings(self):
        return self.driver.execute_script(
            """
            const anchors = Array.from(document.querySelectorAll("a"));
            const seen = new Set();
            const jobs = [];

            for (const anchor of anchors) {
                const href = anchor.href || "";
                const rawText = (anchor.innerText || anchor.textContent || anchor.getAttribute("aria-label") || "").trim();
                const isVisible = Boolean(anchor.offsetParent || anchor.getClientRects().length);
                const looksLikeJobLink = /\\/jobs\\//i.test(href) || /\\/job\\//i.test(href) || /\\/job-detail\\//i.test(href);

                if (!isVisible || !looksLikeJobLink || rawText.length < 6 || seen.has(href)) {
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

            self.wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
            print("Logging in...")

            email_input = self._wait_for_visible(email_locators, timeout=45)
            email_input.clear()
            email_input.send_keys(self.username)
            time.sleep(1)

            self._click_button("Continue", continue_button_locators, fallback_keys=email_input)
            password_input = self._wait_for_visible(password_locators, timeout=45)
            password_input.clear()
            password_input.send_keys(self.password)
            time.sleep(1)

            self._click_button("Sign In", sign_in_button_locators, fallback_keys=password_input)
            time.sleep(3)
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

    def run(self):
        """Main method to run the automation"""
        try:
            if not self.login():
                raise Exception("Login failed")

            search_filter = SearchAndFilter(self.driver, self.wait)
            if not search_filter.perform_search(self.search_keyword):
                raise Exception("Search failed")

            if not search_filter.apply_filters():
                raise Exception("Filter application failed")

            shadow_dom_handler = ShadowDOMHandler(self.driver, self.wait)
            job_handler = JobHandler(self.driver, self.wait, shadow_dom_handler)

            print("Collecting filtered job listings...")
            job_listings = self.get_job_listings()
            if not job_listings:
                print("No jobs found with current filters")
                return
             
            applications_submitted = 0
            jobs_processed = 0
            job_index = 0
             
            while (
                applications_submitted < self.max_applications
                and jobs_processed < min(30, len(job_listings))
            ):
                try:
                    if job_index >= len(job_listings):
                        print("No more job listings to process")
                        break

                    listing = job_listings[job_index]
                    title = listing.get("title", "Unknown job")
                    url = listing.get("url", "")
                    print(f"\nTrying job {job_index + 1} of {len(job_listings)}: {title}")

                    self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                    time.sleep(0.75)

                    if job_handler.apply_to_job(title, url):
                        applications_submitted += 1
                     
                    jobs_processed += 1
                    job_index += 1
                    time.sleep(0.5)
                     
                except Exception as e:
                    print(f"Error processing job listing: {str(e)}")
                    job_index += 1
                    jobs_processed += 1
                    continue
            
            print(f"\nCompleted! Applied to {applications_submitted} jobs, processed {jobs_processed} listings")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
