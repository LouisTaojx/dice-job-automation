from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import time


class JobHandler:
    def __init__(self, driver, wait, shadow_dom_handler):
        self.driver = driver
        self.wait = wait
        self.shadow_dom_handler = shadow_dom_handler

    def apply_to_job(self, job_title="", job_url=""):
        """Handle the application process for a single job"""
        new_tab = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_tab)

        try:
            print("Waiting for page to load completely...")
            time.sleep(4)

            if self.shadow_dom_handler.find_and_click_easy_apply():
                time.sleep(1)

                print("Looking for Next button...")
                next_button = self.wait.until(EC.element_to_be_clickable(
                    (By.XPATH, "//span[text()='Next']")
                ))
                print("Clicking Next button...")
                next_button.click()
                time.sleep(1)

                print("Looking for Submit button...")
                submit_button = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.seds-button-primary.btn-next")
                ))
                print("Clicking Submit button...")
                submit_button.click()
                time.sleep(1)

                print(f"Application submitted: {job_title}")
                return True

            print(f"Skipping job - already applied or not available for easy apply: {job_title} | {job_url}")
            return False

        except Exception as e:
            print(f"Could not process job: {job_title} | {job_url} | {str(e)}")
            return False
        finally:
            print("Closing job tab...")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            time.sleep(0.75)
