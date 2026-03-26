from __future__ import annotations

from collections.abc import Iterable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from .config_manager import DEFAULT_ZOHO_CREDENTIALS
from .utils.humanizer import wait_for_document_ready


class ZohoMailAutomation:
    MAIL_URL = "https://mail.zoho.com/zm/#mail/folder/inbox"

    NEW_MAIL_BUTTON_LOCATORS = [
        (By.CSS_SELECTOR, "[aria-label*='New Mail'], [title*='New Mail']"),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'new mail')]",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'new mail')]",
        ),
    ]
    OPTIONS_BUTTON_LOCATORS = [
        (
            By.CSS_SELECTOR,
            "button[data-testid='com_more_options'][aria-label='Options']",
        ),
        (
            By.XPATH,
            "//button[@data-testid='com_more_options' and @aria-label='Options']",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'options')]",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'options')]",
        ),
    ]
    INSERT_TEMPLATE_LOCATORS = [
        (
            By.XPATH,
            "//*[self::button or self::a or @role='menuitem' or @role='button'][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'insert template')]",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='menuitem' or @role='button'][contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'insert template')]",
        ),
    ]
    TEMPLATE_ROW_LOCATORS = [
        (By.CSS_SELECTOR, ".zm-ins-tmpl-grid-item__hdr"),
        (
            By.XPATH,
            "//div[contains(@class, 'zm-ins-tmpl-grid-item__hdr')]",
        ),
    ]
    TEMPLATE_INSERT_BUTTON_LOCATORS = [
        (
            By.XPATH,
            "//*[@role='dialog' or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dialog')]//*[self::button or self::a or @role='button'][normalize-space()='Insert']",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][normalize-space()='Insert']",
        ),
    ]
    RECIPIENT_FIELD_LOCATORS = [
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[data-placeholder*='To']"),
        (By.CSS_SELECTOR, "[contenteditable='true'][data-placeholder*='To']"),
        (
            By.XPATH,
            "//input[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'to')]",
        ),
        (
            By.XPATH,
            "//textarea[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'to')]",
        ),
        (
            By.XPATH,
            "//*[@contenteditable='true' and contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'to')]",
        ),
        (
            By.XPATH,
            "//input[contains(translate(@placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'to')]",
        ),
        (
            By.XPATH,
            "//*[@contenteditable='true' and contains(translate(@data-placeholder, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'to')]",
        ),
    ]
    SEND_BUTTON_LOCATORS = [
        (By.CSS_SELECTOR, "[aria-label='Send'], [title='Send']"),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][normalize-space()='Send']",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a or @role='button'][contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
        ),
    ]
    LOGIN_EMAIL_LOCATORS = [
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.CSS_SELECTOR, "input[name='LOGIN_ID']"),
        (By.CSS_SELECTOR, "input[id*='login_id']"),
    ]
    LOGIN_PASSWORD_LOCATORS = [
        (By.CSS_SELECTOR, "input[type='password']"),
        (By.CSS_SELECTOR, "input[name='PASSWORD']"),
    ]
    LOGIN_NEXT_BUTTON_LOCATORS = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.CSS_SELECTOR, "#nextbtn"),
        (
            By.XPATH,
            "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
        ),
    ]
    LOGIN_SUBMIT_BUTTON_LOCATORS = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (
            By.XPATH,
            "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]",
        ),
        (
            By.XPATH,
            "//*[self::button or self::a][contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]",
        ),
    ]
    TEMPLATE_CANDIDATE_LOCATORS = [
        (
            By.CSS_SELECTOR,
            ".zm-ins-tmpl__title[role='heading']",
        ),
        (
            By.XPATH,
            "//*[contains(@class, 'zm-ins-tmpl__title') and @role='heading']",
        ),
        (
            By.XPATH,
            "//*[@role='dialog' or @role='menu' or @role='listbox']//*[self::button or self::a or self::div or self::li or @role='option' or @role='menuitem'][normalize-space()]",
        ),
        (
            By.XPATH,
            "//*[contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'popup') or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'dialog') or contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'menu')]//*[self::button or self::a or self::div or self::li or @role='option' or @role='menuitem'][normalize-space()]",
        ),
    ]
    SENT_CONFIRMATION_LOCATORS = [
        (
            By.XPATH,
            "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'mail sent')]",
        ),
        (
            By.XPATH,
            "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'message sent')]",
        ),
        (
            By.XPATH,
            "//*[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sent successfully')]",
        ),
    ]

    def __init__(self, driver, wait, username, password, recipient_emails, humanizer):
        self.driver = driver
        self.wait = wait
        self.username = str(username or "").strip()
        self.password = str(password or "").strip()
        self.recipient_emails = self._normalize_recipient_emails(recipient_emails)
        self.humanizer = humanizer

    def _normalize_recipient_emails(self, recipient_emails):
        if isinstance(recipient_emails, str):
            raw_items = recipient_emails.splitlines()
        elif isinstance(recipient_emails, Iterable):
            raw_items = list(recipient_emails)
        else:
            raw_items = []

        normalized_items = []
        seen = set()
        for item in raw_items:
            normalized = "".join(str(item).split()).strip()
            if not normalized:
                continue

            normalized_key = normalized.lower()
            if normalized_key in seen:
                continue

            seen.add(normalized_key)
            normalized_items.append(normalized)

        return normalized_items

    def _has_configured_credentials(self) -> bool:
        return (
            bool(self.username)
            and bool(self.password)
            and self.username != DEFAULT_ZOHO_CREDENTIALS["username"]
            and self.password != DEFAULT_ZOHO_CREDENTIALS["password"]
        )

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
        except Exception:
            disabled = False

        return not disabled

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

    def _click_element(self, element, label: str) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        self.humanizer.short_pause()

        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

        print(f"Clicked {label}")
        self.humanizer.short_pause()

    def _click_button(self, label: str, locators, timeout=20, fallback_keys=None) -> None:
        try:
            button = self._wait_for_visible(
                locators,
                timeout=timeout,
                require_interactable=True,
            )
        except TimeoutException:
            if fallback_keys is not None:
                fallback_keys.send_keys(Keys.RETURN)
                print(f"Submitted {label} with Enter")
                self.humanizer.short_pause()
                return
            raise

        self._click_element(button, label)

    def _replace_text(self, element, value: str) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)

        self.humanizer.short_pause()
        try:
            element.send_keys(Keys.CONTROL, "a")
            element.send_keys(Keys.DELETE)
        except Exception:
            pass

        element.send_keys(value)
        self.humanizer.short_pause()

    def _page_debug_summary(self) -> str:
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

    def _wait_for_mail_home(self, timeout: int) -> bool:
        active_wait = type(self.wait)(self.driver, timeout)
        try:
            active_wait.until(
                lambda _driver: self._find_first_visible(
                    self.NEW_MAIL_BUTTON_LOCATORS,
                    require_interactable=True,
                )
                is not None
            )
            return True
        except TimeoutException:
            return False

    def _go_to_mail_home(self) -> None:
        self.driver.get(self.MAIL_URL)
        try:
            wait_for_document_ready(self.driver, timeout=20)
        except Exception:
            pass
        self.humanizer.page_pause()

        if not self._wait_for_mail_home(timeout=30):
            raise Exception("Zoho Mail inbox did not finish loading.")

    def login(self) -> bool:
        print("Navigating to Zoho Mail...")
        self.driver.get(self.MAIL_URL)
        try:
            wait_for_document_ready(self.driver, timeout=20)
        except Exception:
            pass
        self.humanizer.page_pause()

        if self._wait_for_mail_home(timeout=10):
            print("Zoho Mail session is already active")
            return True

        if self._has_configured_credentials():
            print("Attempting Zoho Mail login...")
            if self._attempt_login():
                print("Zoho Mail login completed")
                return True

        print("Waiting for manual Zoho Mail sign-in...")
        if self._wait_for_mail_home(timeout=120):
            print("Zoho Mail login completed")
            return True

        print("Zoho Mail login did not complete in time.")
        print(self._page_debug_summary())
        return False

    def _attempt_login(self) -> bool:
        try:
            email_input = self._wait_for_visible(
                self.LOGIN_EMAIL_LOCATORS,
                timeout=20,
                require_interactable=True,
            )
        except TimeoutException:
            return self._wait_for_mail_home(timeout=20)

        self._replace_text(email_input, self.username)
        try:
            self._click_button(
                "Zoho login next",
                self.LOGIN_NEXT_BUTTON_LOCATORS,
                timeout=10,
                fallback_keys=email_input,
            )
        except TimeoutException:
            return False

        try:
            password_input = self._wait_for_visible(
                self.LOGIN_PASSWORD_LOCATORS,
                timeout=20,
                require_interactable=True,
            )
        except TimeoutException:
            return self._wait_for_mail_home(timeout=60)

        self._replace_text(password_input, self.password)
        try:
            self._click_button(
                "Zoho sign in",
                self.LOGIN_SUBMIT_BUTTON_LOCATORS,
                timeout=10,
                fallback_keys=password_input,
            )
        except TimeoutException:
            return False

        return self._wait_for_mail_home(timeout=90)

    def _open_compose_window(self) -> None:
        self._click_button("New Mail", self.NEW_MAIL_BUTTON_LOCATORS, timeout=20)
        self._wait_for_visible(self.SEND_BUTTON_LOCATORS, timeout=20, require_interactable=True)

    def _open_insert_template_menu(self) -> None:
        self._click_button("Options", self.OPTIONS_BUTTON_LOCATORS, timeout=20)
        self._click_button("Insert Template", self.INSERT_TEMPLATE_LOCATORS, timeout=20)

    def _extract_element_label(self, element) -> str:
        for raw_value in (
            element.text,
            element.get_attribute("aria-label"),
            element.get_attribute("title"),
        ):
            normalized = " ".join(str(raw_value or "").split()).strip()
            if normalized:
                return normalized

        return ""

    def _collect_visible_template_rows(self):
        rows = []
        seen_labels = set()

        for by, value in self.TEMPLATE_ROW_LOCATORS:
            try:
                candidate_rows = self.driver.find_elements(by, value)
            except Exception:
                continue

            for row in candidate_rows:
                try:
                    if not row.is_displayed():
                        continue
                except Exception:
                    continue

                try:
                    heading = row.find_element(By.CSS_SELECTOR, ".zm-ins-tmpl__title[role='heading']")
                except Exception:
                    try:
                        heading = row.find_element(
                            By.XPATH,
                            ".//*[contains(@class, 'zm-ins-tmpl__title') and @role='heading']",
                        )
                    except Exception:
                        continue

                label = " ".join(self._extract_element_label(heading).split()).strip()
                if not label:
                    continue

                normalized_label = label.lower()
                if normalized_label in seen_labels:
                    continue

                seen_labels.add(normalized_label)
                rows.append((label, row, heading))

            if rows:
                break

        return rows

    def _is_template_dialog_active(self) -> bool:
        return (
            bool(self._collect_visible_template_rows())
            or self._find_first_visible(self.TEMPLATE_INSERT_BUTTON_LOCATORS) is not None
        )

    def _get_template_checkbox_state(self, template_row):
        return bool(
            self.driver.execute_script(
                """
                const row = arguments[0];
                const checkbox = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action input[type='checkbox']");
                return checkbox ? Boolean(checkbox.checked) : false;
                """,
                template_row,
            )
        )

    def _get_template_checkbox_state_by_label(self, label: str) -> dict[str, bool]:
        return self.driver.execute_script(
            """
            const desired = (arguments[0] || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const rows = Array.from(document.querySelectorAll(".zm-ins-tmpl-grid-item__hdr"));
            const row = rows.find((candidate) => {
                const heading = candidate.querySelector(".zm-ins-tmpl__title[role='heading']");
                return heading && normalize(heading.textContent) === desired;
            });

            if (!row) {
                return { exists: false, checked: false };
            }

            const checkbox = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action input[type='checkbox']");
            return { exists: true, checked: checkbox ? Boolean(checkbox.checked) : false };
            """,
            label,
        )

    def _click_template_checkbox(self, template_row, label: str) -> bool:
        checkbox_toggled = self.driver.execute_script(
            """
            const row = arguments[0];
            const action = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action");
            const wrapper = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action .jsCheckbox, .zm-ins-tmpl-grid-item__hdr__action .zmcheckbox__ld7ss9");
            const checkbox = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action input[type='checkbox']");
            const target = wrapper || action || checkbox;

            if (!checkbox || !target) {
                return { found: false, checked: false };
            }

            if (!checkbox.checked) {
                target.dispatchEvent(new MouseEvent('click', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                }));
            }

            return { found: true, checked: Boolean(checkbox.checked) };
            """,
            template_row,
        )

        if checkbox_toggled.get("found"):
            print(f"Tried to check Zoho template checkbox for '{label}'")
            self.humanizer.short_pause()

        return bool(checkbox_toggled.get("checked"))

    def _click_template_checkbox_by_label(self, label: str) -> bool:
        checkbox_toggled = self.driver.execute_script(
            """
            const desired = (arguments[0] || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const rows = Array.from(document.querySelectorAll(".zm-ins-tmpl-grid-item__hdr"));
            const row = rows.find((candidate) => {
                const heading = candidate.querySelector(".zm-ins-tmpl__title[role='heading']");
                return heading && normalize(heading.textContent) === desired;
            });

            if (!row) {
                return { found: false, checked: false };
            }

            const action = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action");
            const wrapper = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action .jsCheckbox, .zm-ins-tmpl-grid-item__hdr__action .zmcheckbox__ld7ss9");
            const checkbox = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action input[type='checkbox']");
            const target = wrapper || action || checkbox;

            if (!checkbox || !target) {
                return { found: false, checked: false };
            }

            if (!checkbox.checked) {
                target.click();
            }

            return { found: true, checked: Boolean(checkbox.checked) };
            """,
            label,
        )

        if checkbox_toggled.get("found"):
            print(f"Tried to check Zoho template checkbox for '{label}'")
            self.humanizer.short_pause()

        return bool(checkbox_toggled.get("checked"))

    def _force_template_checkbox_checked(self, template_row, label: str) -> bool:
        checkbox_checked = self.driver.execute_script(
            """
            const row = arguments[0];
            const checkbox = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action input[type='checkbox']");
            if (!checkbox) {
                return false;
            }

            if (!checkbox.checked) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }

            return Boolean(checkbox.checked);
            """,
            template_row,
        )

        if checkbox_checked:
            print(f"Forced Zoho template checkbox checked for '{label}'")
            self.humanizer.short_pause()

        return bool(checkbox_checked)

    def _force_template_checkbox_checked_by_label(self, label: str) -> bool:
        checkbox_checked = self.driver.execute_script(
            """
            const desired = (arguments[0] || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const rows = Array.from(document.querySelectorAll(".zm-ins-tmpl-grid-item__hdr"));
            const row = rows.find((candidate) => {
                const heading = candidate.querySelector(".zm-ins-tmpl__title[role='heading']");
                return heading && normalize(heading.textContent) === desired;
            });

            if (!row) {
                return false;
            }

            const checkbox = row.querySelector(".zm-ins-tmpl-grid-item__hdr__action input[type='checkbox']");
            if (!checkbox) {
                return false;
            }

            if (!checkbox.checked) {
                checkbox.checked = true;
                checkbox.dispatchEvent(new Event('input', { bubbles: true }));
                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
            }

            return Boolean(checkbox.checked);
            """,
            label,
        )

        if checkbox_checked:
            print(f"Forced Zoho template checkbox checked for '{label}'")
            self.humanizer.short_pause()

        return bool(checkbox_checked)

    def _double_click_template_heading_by_label(self, label: str) -> bool:
        heading_clicked = self.driver.execute_script(
            """
            const desired = (arguments[0] || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const headings = Array.from(document.querySelectorAll(".zm-ins-tmpl__title[role='heading']"));
            const heading = headings.find((candidate) => normalize(candidate.textContent) === desired);

            if (!heading) {
                return false;
            }

            heading.dispatchEvent(new MouseEvent('dblclick', {
                bubbles: true,
                cancelable: true,
                view: window
            }));
            return true;
            """,
            label,
        )

        if heading_clicked:
            print(f"Double-clicked Zoho template heading '{label}'")
            self.humanizer.short_pause()

        return bool(heading_clicked)

    def _click_template_heading_by_label(self, label: str) -> bool:
        heading_clicked = self.driver.execute_script(
            """
            const desired = (arguments[0] || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const headings = Array.from(document.querySelectorAll(".zm-ins-tmpl__title[role='heading']"));
            const heading = headings.find((candidate) => normalize(candidate.textContent) === desired);

            if (!heading) {
                return false;
            }

            heading.click();
            return true;
            """,
            label,
        )

        if heading_clicked:
            print(f"Clicked Zoho template heading '{label}'")
            self.humanizer.short_pause()

        return bool(heading_clicked)

    def _is_template_insert_ready(self) -> bool:
        return self._find_first_visible(
            self.TEMPLATE_INSERT_BUTTON_LOCATORS,
            require_interactable=True,
        ) is not None

    def _activate_template_selection(self, label: str, template_row, heading_element) -> bool:
        print(f"Found unique Zoho template: {label}")
        clicked = False
        try:
            self._click_element(heading_element, f"Zoho template heading '{label}'")
            clicked = True
        except Exception:
            clicked = self._click_template_heading_by_label(label)

        if not clicked:
            raise Exception(f"Could not click the Zoho template heading for '{label}'")

        active_wait = type(self.wait)(self.driver, 10)
        active_wait.until(lambda _driver: not self._is_template_dialog_active())

        print(f"Inserted Zoho template via heading click: {label}")
        return False

    def _focus_recipient_field(self) -> str:
        return str(
            self.driver.execute_script(
                """
                const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
                const isVisible = (element) => Boolean(element && (element.offsetParent || element.getClientRects().length));

                const allFields = Array.from(document.querySelectorAll("input, textarea, [contenteditable='true']"))
                    .filter(isVisible);

                const describe = (element) => (
                    element.getAttribute('aria-label')
                    || element.getAttribute('placeholder')
                    || element.getAttribute('data-placeholder')
                    || element.getAttribute('name')
                    || element.id
                    || element.tagName
                );

                const directMatch = allFields.find((element) => {
                    const labels = [
                        element.getAttribute('aria-label'),
                        element.getAttribute('placeholder'),
                        element.getAttribute('data-placeholder'),
                        element.getAttribute('name'),
                        element.id,
                    ].map(normalize).filter(Boolean);

                    return labels.some((value) =>
                        value === 'to'
                        || value.startsWith('to ')
                        || value.includes('recipient')
                    );
                });

                let target = directMatch;
                if (!target) {
                    const visibleToLabel = Array.from(document.querySelectorAll("label, div, span, button"))
                        .filter(isVisible)
                        .find((element) => normalize(element.textContent) === 'to');

                    if (visibleToLabel) {
                        const scopedRoot = visibleToLabel.closest("[role='dialog'], [class*='compose'], [data-testid*='compose']") || document;
                        target = Array.from(scopedRoot.querySelectorAll("input, textarea, [contenteditable='true']"))
                            .filter(isVisible)
                            .find((element) => {
                                const label = normalize(
                                    element.getAttribute('aria-label')
                                    || element.getAttribute('placeholder')
                                    || element.getAttribute('data-placeholder')
                                    || ''
                                );
                                return !label.includes('subject') && !label.includes('search');
                            }) || null;
                    }
                }

                if (!target) {
                    const composeRoots = Array.from(document.querySelectorAll("[role='dialog'], [class*='compose'], [data-testid*='compose']"))
                        .filter(isVisible);
                    for (const root of composeRoots) {
                        const candidate = Array.from(root.querySelectorAll("input, textarea, [contenteditable='true']"))
                            .filter(isVisible)
                            .find((element) => {
                                const label = normalize(
                                    element.getAttribute('aria-label')
                                    || element.getAttribute('placeholder')
                                    || element.getAttribute('data-placeholder')
                                    || ''
                                );
                                return !label.includes('subject') && !label.includes('search');
                            });
                        if (candidate) {
                            target = candidate;
                            break;
                        }
                    }
                }

                if (!target) {
                    return '';
                }

                target.focus();
                target.click();
                return describe(target);
                """
            )
        ).strip()

    def _recipient_present(self, recipient_email: str) -> bool:
        return bool(
            self.driver.execute_script(
                """
                const expected = (arguments[0] || "").trim().toLowerCase();
                const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim().toLowerCase();
                const isVisible = (element) => Boolean(element && (element.offsetParent || element.getClientRects().length));

                const values = [];
                for (const element of Array.from(document.querySelectorAll("input, textarea, [contenteditable='true'], span, div"))) {
                    if (!isVisible(element)) {
                        continue;
                    }

                    values.push(
                        normalize(element.value)
                        || normalize(element.textContent)
                        || normalize(element.getAttribute('aria-label'))
                        || normalize(element.getAttribute('title'))
                    );
                }

                return values.some((value) => value.includes(expected));
                """,
                recipient_email,
            )
        )

    def _select_only_template(self) -> str:
        last_labels: list[str] = []
        for _ in range(25):
            candidates = self._collect_visible_template_rows()
            last_labels = [label for label, _row, _heading in candidates]
            if len(candidates) == 1:
                label, template_row, heading_element = candidates[0]
                self._activate_template_selection(
                    label,
                    template_row,
                    heading_element,
                )
                return label

            self.humanizer.short_pause()

        if last_labels:
            raise Exception(
                "Expected exactly one visible Zoho template, "
                f"but found {len(last_labels)} candidates: {', '.join(last_labels)}"
            )

        raise Exception("No Zoho template option became visible after opening Insert Template.")

    def _enter_recipient(self, recipient_email: str) -> None:
        focused_description = self._focus_recipient_field()
        if focused_description:
            print(f"Focused Zoho recipient field: {focused_description}")
            recipient_field = self.driver.switch_to.active_element
        else:
            recipient_field = self._wait_for_visible(
                self.RECIPIENT_FIELD_LOCATORS,
                timeout=20,
                require_interactable=True,
            )

        self._replace_text(recipient_field, recipient_email)
        self.humanizer.short_pause()

        if not self._recipient_present(recipient_email):
            recipient_field.send_keys(Keys.TAB)
            self.humanizer.short_pause()

        if not self._recipient_present(recipient_email):
            recipient_field.send_keys(Keys.ENTER)
            self.humanizer.short_pause()

        if not self._recipient_present(recipient_email):
            raise Exception(f"Zoho recipient field did not accept {recipient_email}")

        print(f"Entered recipient email: {recipient_email}")

    def _wait_for_send_completion(self) -> None:
        active_wait = type(self.wait)(self.driver, 20)
        active_wait.until(
            lambda _driver: self._find_first_visible(self.SENT_CONFIRMATION_LOCATORS) is not None
            or self._find_first_visible(self.RECIPIENT_FIELD_LOCATORS) is None
        )
        self.humanizer.page_pause()

    def _send_template_email(self, recipient_email: str) -> None:
        self._go_to_mail_home()
        self._open_compose_window()
        self._open_insert_template_menu()
        selected_template = self._select_only_template()
        print(f"Inserted Zoho template: {selected_template}")
        self._enter_recipient(recipient_email)
        self._click_button("Send", self.SEND_BUTTON_LOCATORS, timeout=20)
        self._wait_for_send_completion()
        print(f"Zoho Mail sent successfully to {recipient_email}")

    def run(self) -> None:
        if not self.recipient_emails:
            raise ValueError("No Zoho Mail recipient emails were provided.")

        if not self.login():
            raise Exception("Zoho Mail login failed.")

        failures = []
        for index, recipient_email in enumerate(self.recipient_emails, start=1):
            print(
                f"\nSending Zoho Mail template email {index}/{len(self.recipient_emails)} to {recipient_email}..."
            )
            try:
                self._send_template_email(recipient_email)
            except Exception as exc:
                message = str(exc)
                failures.append((recipient_email, message))
                print(f"Failed to send Zoho Mail to {recipient_email}: {message}")

        sent_count = len(self.recipient_emails) - len(failures)
        print(
            f"\nZoho Mail completed. Sent {sent_count} emails out of {len(self.recipient_emails)} recipients."
        )

        if failures:
            failure_summary = "; ".join(
                f"{recipient}: {message}" for recipient, message in failures
            )
            raise Exception(f"Zoho Mail finished with failures. {failure_summary}")
