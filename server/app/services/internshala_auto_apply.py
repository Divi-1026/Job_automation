"""
CareerSync - Internshala Auto Apply Service

Flow
----
1. Login to Internshala
2. Open internship/job page
3. Click "Apply now"
4. If Internshala opens the resume intermediate page:
      click "Proceed to application"
5. On the final application form:
      - fill cover letter
      - handle availability only when it is explicitly known
      - leave existing uploaded resume untouched
      - answer only questions that can be answered safely from user profile
6. Submit
7. Confirm success

Safety
------
- CAPTCHA / OTP / account verification are never bypassed.
- Unknown questions are never guessed.
- Unknown availability becomes pending_manual.
- If eligibility cannot be confirmed, the job is not auto-submitted.

This service reuses CareerSync's existing Naukri eligibility gate:
    AutoApplyService.check_job_eligibility(job)

Expected return status values:
    success
    already_applied
    pending_manual
    not_eligible
    needs_review
    error
"""

import logging
import os
import time
from datetime import datetime
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

from app.services.auto_apply import AutoApplyService


logger = logging.getLogger(__name__)


class InternshalaAutoApplyService:
    """
    Site-specific Internshala auto-apply service.

    Parameters
    ----------
    email:
        Saved Internshala login email.

    password:
        Decrypted Internshala login password.

    user_profile:
        Known factual user data.

        Supported fields used by this service:
            full_name
            years_of_experience
            skills
            highest_education
            location
            availability
            available_immediately
            current_role
            current_company
            notice_period

        IMPORTANT:
        availability / available_immediately should only be set when
        explicitly provided by the user.
    """

    def __init__(
        self,
        email: str,
        password: str,
        user_profile: Optional[dict] = None,
    ):
        self.email = email
        self.password = password
        self.user_profile = user_profile or {}

        self.driver = None
        self.wait = None

        try:
            self.debug_hold_seconds = max(
                0,
                int(os.getenv("INTERNSHALA_DEBUG_HOLD_SECONDS", "5")),
            )
        except (TypeError, ValueError):
            self.debug_hold_seconds = 5

        # Reuse CareerSync's existing eligibility gate.
        # AutoApplyService does not launch a browser in __init__.
        self.eligibility_checker = AutoApplyService(
            email="",
            password="",
            user_profile=self.user_profile,
        )

    def _log(self, message: str):
        """Always show important automation progress in the Uvicorn terminal."""
        print(message, flush=True)
        try:
            logger.info(message)
        except Exception:
            pass

    # =========================================================
    # DRIVER
    # =========================================================

    def get_driver(self):
        self._log("🌐 [Internshala] Launching visible Chrome...")

        options = webdriver.ChromeOptions()
        # Browser intentionally visible: no --headless flag.
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument("--lang=en")

        options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation", "enable-logging"],
        )
        options.add_experimental_option("useAutomationExtension", False)

        self._log("🧩 [Internshala] Preparing ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            driver.maximize_window()
        except Exception:
            pass

        try:
            driver.execute_script(
                """
                Object.defineProperty(
                    navigator,
                    'webdriver',
                    {get: () => undefined}
                );
                """
            )
        except JavascriptException:
            pass

        try:
            stealth(
                driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
        except Exception as exc:
            self._log(f"ℹ️ [Internshala] selenium-stealth failed; continuing: {exc}")

        self.wait = WebDriverWait(driver, 15)
        self._log("✅ [Internshala] Chrome opened successfully.")
        return driver

    # =========================================================
    # GENERIC HELPERS
    # =========================================================

    def _page_source_lower(self) -> str:
        try:
            return (
                self.driver.page_source
                or ""
            ).lower()
        except Exception:
            return ""

    def _current_url(self) -> str:
        try:
            return (
                self.driver.current_url
                or ""
            )
        except Exception:
            return ""

    def _body_text(self) -> str:
        try:
            body = self.driver.find_element(
                By.TAG_NAME,
                "body",
            )
            return (
                body.text
                or ""
            ).lower()
        except Exception:
            return self._page_source_lower()

    def _find_visible(
        self,
        candidates: list[tuple[str, str]],
    ) -> Optional[WebElement]:
        for by, selector in candidates:
            try:
                elements = (
                    self.driver.find_elements(
                        by,
                        selector,
                    )
                )

                for element in elements:
                    try:
                        if (
                            element.is_displayed()
                            and element.is_enabled()
                        ):
                            return element
                    except StaleElementReferenceException:
                        continue

            except Exception:
                continue

        return None

    def _all_visible(
        self,
        candidates: list[tuple[str, str]],
    ) -> list[WebElement]:
        output = []

        for by, selector in candidates:
            try:
                elements = (
                    self.driver.find_elements(
                        by,
                        selector,
                    )
                )

                for element in elements:
                    try:
                        if (
                            element.is_displayed()
                            and element.is_enabled()
                        ):
                            output.append(
                                element
                            )
                    except StaleElementReferenceException:
                        continue

            except Exception:
                continue

        return output

    def _safe_click(
        self,
        element: WebElement,
    ) -> bool:
        try:
            self.driver.execute_script(
                """
                arguments[0].scrollIntoView({
                    block: 'center',
                    inline: 'center'
                });
                """,
                element,
            )
            time.sleep(0.5)
        except Exception:
            pass

        try:
            element.click()
            return True

        except (
            ElementClickInterceptedException,
            WebDriverException,
        ):
            try:
                self.driver.execute_script(
                    "arguments[0].click();",
                    element,
                )
                return True
            except Exception:
                return False

    def _wait_for_page_change(
        self,
        old_url: str,
        timeout: int = 10,
    ):
        try:
            WebDriverWait(
                self.driver,
                timeout,
            ).until(
                lambda d:
                    d.current_url != old_url
                    or d.execute_script(
                        "return document.readyState"
                    ) == "complete"
            )
        except Exception:
            pass

        time.sleep(2)

    # =========================================================
    # BLOCKERS / SUCCESS
    # =========================================================

    def _detect_blocker(
        self,
    ) -> Optional[str]:
        """
        Detect only a real, user-visible verification blocker.

        Internshala may load reCAPTCHA iframes/scripts on the login page even
        when no challenge is shown. A plain reCAPTCHA iframe therefore MUST
        NOT be treated as a blocker by itself.
        """

        body = self._body_text()

        # 1) Strong visible text signals
        captcha_text_markers = [
            "i'm not a robot",
            "i am not a robot",
            "complete the captcha",
            "solve the captcha",
            "captcha verification",
            "verify you are human",
            "verify that you are human",
            "please verify you are a human",
            "security check",
        ]

        if any(marker in body for marker in captcha_text_markers):
            self._log(
                "⚠️ [Internshala] Visible CAPTCHA/verification text detected."
            )
            return "CAPTCHA requires manual action."

        # 2) Strong visible challenge UI signals.
        # Do NOT use generic iframe[src*='recaptcha'] because reCAPTCHA can
        # inject badge/background frames even when no challenge is shown.
        challenge_selectors = [
            (By.CSS_SELECTOR, "iframe[title*='challenge']"),
            (By.CSS_SELECTOR, "iframe[title*='Challenge']"),
            (By.CSS_SELECTOR, ".g-recaptcha-bubble-arrow"),
            (By.CSS_SELECTOR, ".rc-imageselect"),
            (By.CSS_SELECTOR, ".rc-audiochallenge"),
            (By.CSS_SELECTOR, ".hcaptcha-challenge"),
            (By.CSS_SELECTOR, "[role='dialog'] iframe[src*='captcha']"),
            (By.CSS_SELECTOR, "[role='dialog'] iframe[src*='recaptcha']"),
        ]

        for by, selector in challenge_selectors:
            try:
                elements = self.driver.find_elements(by, selector)

                for element in elements:
                    try:
                        if not element.is_displayed():
                            continue

                        size = element.size or {}
                        width = int(size.get("width") or 0)
                        height = int(size.get("height") or 0)

                        # Ignore tiny/badge/background elements.
                        if width < 120 or height < 80:
                            continue

                        self._log(
                            f"⚠️ [Internshala] Visible CAPTCHA challenge detected: "
                            f"{selector} ({width}x{height})"
                        )
                        return "CAPTCHA requires manual action."

                    except StaleElementReferenceException:
                        continue
                    except Exception:
                        continue

            except Exception:
                continue

        # 3) OTP / account-verification blockers based on visible body text.
        visible_blockers = [
            (
                [
                    "enter otp",
                    "one time password",
                    "one-time password",
                ],
                "OTP verification requires manual action.",
            ),
            (
                [
                    "verification code",
                ],
                "Verification requires manual action.",
            ),
            (
                [
                    "verify your email",
                    "confirm your email",
                ],
                "Email verification requires manual action.",
            ),
            (
                [
                    "verify your mobile",
                    "verify mobile",
                ],
                "Mobile verification requires manual action.",
            ),
        ]

        for markers, reason in visible_blockers:
            if any(marker in body for marker in markers):
                self._log(
                    f"⚠️ [Internshala] Visible verification blocker: {reason}"
                )
                return reason

        self._log("✅ [Internshala] No visible verification blocker detected.")
        return None

    def _success_detected(
        self,
    ) -> bool:
        text = (
            self._page_source_lower()
        )

        markers = [
            "application submitted",
            "successfully applied",
            "application has been submitted",
            "your application has been submitted",
            "application sent",
            "you have applied",
            "already applied",
        ]

        return any(
            marker in text
            for marker in markers
        )

    # =========================================================
    # LOGIN
    # =========================================================

    def login(
        self,
    ) -> tuple[bool, Optional[str]]:
        self._log("🔐 [Internshala] Starting login...")

        login_urls = [
            "https://internshala.com/login/student",
            "https://internshala.com/login",
        ]

        for login_url in login_urls:
            try:
                self._log(f"➡️ [Internshala] Opening login page: {login_url}")
                self.driver.get(login_url)
                time.sleep(3)
                self._log(f"📍 [Internshala] Login page URL: {self._current_url()}")

                blocker = (
                    self._detect_blocker()
                )

                if blocker:
                    return False, blocker

                email_input = (
                    self._find_visible([
                        (
                            By.ID,
                            "email",
                        ),
                        (
                            By.NAME,
                            "email",
                        ),
                        (
                            By.CSS_SELECTOR,
                            "input[type='email']",
                        ),
                        (
                            By.CSS_SELECTOR,
                            "input[autocomplete='username']",
                        ),
                    ])
                )

                password_input = (
                    self._find_visible([
                        (
                            By.ID,
                            "password",
                        ),
                        (
                            By.NAME,
                            "password",
                        ),
                        (
                            By.CSS_SELECTOR,
                            "input[type='password']",
                        ),
                        (
                            By.CSS_SELECTOR,
                            "input[autocomplete='current-password']",
                        ),
                    ])
                )

                if (
                    not email_input
                    or not password_input
                ):
                    logger.warning(
                        "Internshala login inputs not found at %s",
                        login_url,
                    )
                    continue

                email_input.clear()
                email_input.send_keys(
                    self.email
                )

                password_input.clear()
                password_input.send_keys(
                    self.password
                )

                login_button = (
                    self._find_visible([
                        (
                            By.ID,
                            "login_submit",
                        ),
                        (
                            By.CSS_SELECTOR,
                            "button[type='submit']",
                        ),
                        (
                            By.XPATH,
                            "//button[contains("
                            "translate(normalize-space(.),"
                            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                            "'abcdefghijklmnopqrstuvwxyz'),"
                            "'login')]",
                        ),
                        (
                            By.XPATH,
                            "//button[contains("
                            "translate(normalize-space(.),"
                            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                            "'abcdefghijklmnopqrstuvwxyz'),"
                            "'sign in')]",
                        ),
                    ])
                )

                if not login_button:
                    self._log("⚠️ [Internshala] Login button not found.")
                    continue

                old_url = (
                    self._current_url()
                )

                if not self._safe_click(
                    login_button
                ):
                    continue

                self._wait_for_page_change(
                    old_url,
                    timeout=12,
                )

                blocker = (
                    self._detect_blocker()
                )

                if blocker:
                    return False, blocker

                text = (
                    self._page_source_lower()
                )

                invalid_markers = [
                    "incorrect password",
                    "invalid password",
                    "invalid credentials",
                    "email/password combination",
                    "wrong password",
                ]

                if any(
                    marker in text
                    for marker in invalid_markers
                ):
                    return (
                        False,
                        "Internshala rejected the saved email/password.",
                    )

                # Strong login evidence #1:
                # login page URL is gone.
                current_url = (
                    self._current_url()
                    .lower()
                )

                if (
                    "/login" not in current_url
                ):
                    self._log("✅ [Internshala] Login confirmed by URL.")
                    return True, None

                # Strong login evidence #2:
                # password input disappeared.
                visible_password = (
                    self._find_visible([
                        (
                            By.CSS_SELECTOR,
                            "input[type='password']",
                        )
                    ])
                )

                if not visible_password:
                    self._log("✅ [Internshala] Login confirmed; login form disappeared.")
                    return True, None

                # Strong login evidence #3:
                # authenticated navigation markers.
                authenticated_element = (
                    self._find_visible([
                        (
                            By.XPATH,
                            "//*[contains("
                            "translate(normalize-space(.),"
                            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                            "'abcdefghijklmnopqrstuvwxyz'),"
                            "'logout')]",
                        ),
                        (
                            By.XPATH,
                            "//*[contains("
                            "translate(normalize-space(.),"
                            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                            "'abcdefghijklmnopqrstuvwxyz'),"
                            "'my applications')]",
                        ),
                        (
                            By.XPATH,
                            "//*[contains("
                            "translate(normalize-space(.),"
                            "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                            "'abcdefghijklmnopqrstuvwxyz'),"
                            "'profile')]",
                        ),
                    ])
                )

                if authenticated_element:
                    self._log("✅ [Internshala] Login confirmed by authenticated UI.")
                    return True, None

            except Exception as exc:
                logger.exception(
                    "Internshala login attempt failed: %s",
                    exc,
                )

        return (
            False,
            "Internshala login could not be confirmed.",
        )

    # =========================================================
    # STEP 1 - JOB PAGE
    # =========================================================

    def click_apply_now(
        self,
    ) -> str:
        """
        Return:
            clicked
            already_applied
            not_found
            error
        """

        text = (
            self._page_source_lower()
        )

        if (
            "already applied" in text
        ):
            return "already_applied"

        button = (
            self._find_visible([
                (
                    By.ID,
                    "apply_now_button",
                ),
                (
                    By.CSS_SELECTOR,
                    "#apply_now_button",
                ),
                (
                    By.CSS_SELECTOR,
                    "button.apply_now_button",
                ),
                (
                    By.CSS_SELECTOR,
                    "a.apply_now_button",
                ),
                (
                    By.XPATH,
                    "//button[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'apply now')]",
                ),
                (
                    By.XPATH,
                    "//a[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'apply now')]",
                ),
            ])
        )

        if not button:
            self._log("❌ [Internshala] Apply now button not found.")
            return "not_found"

        old_url = (
            self._current_url()
        )

        self._log("🖱️ [Internshala] Clicking Apply now...")
        if not self._safe_click(button):
            self._log("❌ [Internshala] Apply now click failed.")
            return "error"

        self._wait_for_page_change(
            old_url,
            timeout=10,
        )

        self._log(f"✅ [Internshala] Apply now clicked. Current URL: {self._current_url()}")
        return "clicked"

    # =========================================================
    # STEP 2 - RESUME INTERMEDIATE PAGE
    # =========================================================

    def is_resume_intermediate_page(
        self,
    ) -> bool:
        current_url = (
            self._current_url()
            .lower()
        )

        text = (
            self._page_source_lower()
        )

        return (
            "resume_intermediate"
            in current_url
            or "proceed to application"
            in text
        )

    def click_proceed_to_application(
        self,
    ) -> bool:
        """
        Handles page similar to:
        /student/resume?detail_source=resume_intermediate
        """

        button = (
            self._find_visible([
                (
                    By.ID,
                    "proceed_to_application",
                ),
                (
                    By.CSS_SELECTOR,
                    "#proceed_to_application",
                ),
                (
                    By.CSS_SELECTOR,
                    "button[type='submit']",
                ),
                (
                    By.XPATH,
                    "//button[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'proceed to application')]",
                ),
                (
                    By.XPATH,
                    "//a[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'proceed to application')]",
                ),
            ])
        )

        if not button:
            self._log("❌ [Internshala] Proceed to application button not found.")
            return False

        old_url = (
            self._current_url()
        )

        self._log("🖱️ [Internshala] Clicking Proceed to application...")
        if not self._safe_click(button):
            self._log("❌ [Internshala] Proceed to application click failed.")
            return False

        self._wait_for_page_change(
            old_url,
            timeout=12,
        )

        self._log(f"✅ [Internshala] Proceeded to application. Current URL: {self._current_url()}")
        return True

    # =========================================================
    # FINAL APPLICATION FORM
    # =========================================================

    def _get_question_context(
        self,
        element: WebElement,
    ) -> str:
        parts = []

        # label[for=id]
        try:
            element_id = (
                element.get_attribute(
                    "id"
                )
                or ""
            )

            if element_id:
                labels = (
                    self.driver
                    .find_elements(
                        By.CSS_SELECTOR,
                        f"label[for='{element_id}']",
                    )
                )

                for label in labels:
                    if label.text:
                        parts.append(
                            label.text
                        )
        except Exception:
            pass

        # closest form group / container
        for xpath in [
            "./ancestor::*[contains(@class,'form-group')][1]",
            "./ancestor::*[contains(@class,'form_question')][1]",
            "./ancestor::*[self::div or self::section][1]",
        ]:
            try:
                parent = (
                    element.find_element(
                        By.XPATH,
                        xpath,
                    )
                )

                if parent.text:
                    parts.append(
                        parent.text
                    )
                    break

            except Exception:
                continue

        return (
            " ".join(parts)
            .strip()
            .lower()
        )

    def build_cover_letter(
        self,
        job: dict,
    ) -> str:
        """
        Conservative personalized cover letter using only known facts.
        """

        full_name = (
            self.user_profile.get(
                "full_name"
            )
            or ""
        )

        education = (
            self.user_profile.get(
                "highest_education"
            )
            or ""
        )

        role = (
            self.user_profile.get(
                "current_role"
            )
            or ""
        )

        skills = (
            self.user_profile.get(
                "skills"
            )
            or []
        )

        if isinstance(
            skills,
            str,
        ):
            skills = [
                item.strip()
                for item in
                skills.split(",")
                if item.strip()
            ]

        skill_text = (
            ", ".join(
                skills[:7]
            )
            if skills
            else "relevant technical skills"
        )

        job_title = (
            job.get("title")
            or "this role"
        )

        company = (
            job.get("company")
            or "your organization"
        )

        intro = (
            f"I am {full_name}. "
            if full_name
            else ""
        )

        education_text = (
            f"I am pursuing/have completed {education}. "
            if education
            else ""
        )

        role_text = (
            f"My current role/background includes {role}. "
            if role
            else ""
        )

        return (
            f"{intro}"
            f"{education_text}"
            f"{role_text}"
            f"My skills include {skill_text}. "
            f"I am interested in the {job_title} opportunity at {company} "
            f"because it aligns with my technical background and project experience. "
            f"I am comfortable learning quickly, working collaboratively, "
            f"and taking ownership of assigned responsibilities."
        )

    def fill_cover_letter(
        self,
        job: dict,
    ) -> tuple[bool, Optional[str]]:
        """
        Finds Internshala's cover-letter textarea and fills it.
        """

        textarea = (
            self._find_visible([
                (
                    By.NAME,
                    "cover_letter",
                ),
                (
                    By.ID,
                    "cover_letter",
                ),
                (
                    By.CSS_SELECTOR,
                    "textarea[name*='cover']",
                ),
                (
                    By.CSS_SELECTOR,
                    "textarea[id*='cover']",
                ),
                (
                    By.CSS_SELECTOR,
                    "textarea",
                ),
            ])
        )

        if not textarea:
            return (
                False,
                "Cover letter field could not be identified safely.",
            )

        try:
            current = (
                textarea.get_attribute(
                    "value"
                )
                or ""
            ).strip()

            if current:
                return True, None

            answer = (
                self.build_cover_letter(
                    job
                )
            )

            textarea.clear()
            textarea.send_keys(
                answer
            )

            self._log("✅ [Internshala] Cover letter filled.")

            return True, None

        except Exception as exc:
            return (
                False,
                f"Could not fill cover letter: {exc}",
            )

    # =========================================================
    # AVAILABILITY
    # =========================================================

    def _known_availability(
        self,
    ):
        """
        Returns:
            True  -> explicitly available immediately
            False -> explicitly not available immediately
            None  -> unknown
        """

        explicit_bool = (
            self.user_profile.get(
                "available_immediately"
            )
        )

        if isinstance(
            explicit_bool,
            bool,
        ):
            return explicit_bool

        availability = (
            self.user_profile.get(
                "availability"
            )
        )

        if availability is None:
            return None

        text = (
            str(availability)
            .strip()
            .lower()
        )

        yes_markers = [
            "immediately",
            "immediate",
            "available now",
            "join now",
        ]

        no_markers = [
            "not immediately",
            "after ",
            "notice",
            "days",
            "weeks",
            "months",
        ]

        if (
            "not immediately"
            in text
        ):
            return False

        if any(
            marker in text
            for marker in yes_markers
        ):
            return True

        if any(
            marker in text
            for marker in no_markers
        ):
            return False

        return None

    def handle_availability(
        self,
    ) -> tuple[bool, Optional[str]]:
        """
        The screenshots show:
        - Yes, I am available to join immediately
        - No (Please specify your availability)

        We do NOT guess this answer.
        """

        page_text = (
            self._body_text()
        )

        if (
            "confirm your availability"
            not in page_text
        ):
            return True, None

        known = (
            self._known_availability()
        )

        if known is None:
            return (
                False,
                (
                    "Internshala asks to confirm availability, "
                    "but CareerSync does not have an explicit saved availability answer."
                ),
            )

        radios = (
            self._all_visible([
                (
                    By.CSS_SELECTOR,
                    "input[type='radio']",
                )
            ])
        )

        if not radios:
            return (
                False,
                "Availability radio buttons could not be identified.",
            )

        yes_radio = None
        no_radio = None

        for radio in radios:
            context = (
                self._get_question_context(
                    radio
                )
            )

            value = (
                radio.get_attribute(
                    "value"
                )
                or ""
            ).lower()

            combined = (
                context
                + " "
                + value
            )

            if (
                "available to join immediately"
                in combined
                or "immediately"
                in combined
            ):
                yes_radio = radio

            if (
                "please specify your availability"
                in combined
                or "not available"
                in combined
                or "no"
                in value
            ):
                no_radio = radio

        if known is True:
            target = (
                yes_radio
                or (
                    radios[0]
                    if len(radios) >= 1
                    else None
                )
            )

            if (
                target
                and self._safe_click(
                    target
                )
            ):
                self._log("✅ [Internshala] Availability set: immediate.")
                return True, None

            return (
                False,
                "Could not select immediate availability.",
            )

        # known is False:
        # We only choose No if we also have the actual availability text.
        target = no_radio

        availability_text = (
            self.user_profile.get(
                "availability"
            )
            or self.user_profile.get(
                "notice_period"
            )
        )

        if not target:
            return (
                False,
                "Could not identify the 'No' availability option safely.",
            )

        if not availability_text:
            return (
                False,
                (
                    "User is not immediately available, "
                    "but the actual availability/notice period is missing."
                ),
            )

        if not self._safe_click(
            target
        ):
            return (
                False,
                "Could not select non-immediate availability.",
            )

        time.sleep(1)

        detail_input = (
            self._find_visible([
                (
                    By.CSS_SELECTOR,
                    "input[type='text']",
                ),
                (
                    By.CSS_SELECTOR,
                    "textarea",
                ),
            ])
        )

        if not detail_input:
            return (
                False,
                (
                    "Internshala asks for availability details "
                    "but the input field could not be identified safely."
                ),
            )

        try:
            detail_input.clear()
            detail_input.send_keys(
                str(
                    availability_text
                )
            )
            return True, None

        except Exception:
            return (
                False,
                "Could not fill availability details.",
            )

    # =========================================================
    # OTHER APPLICATION QUESTIONS
    # =========================================================

    def _known_answer_for_question(
        self,
        question: str,
    ) -> Optional[str]:
        q = (
            question
            or ""
        ).lower()

        # These are safe factual mappings only.

        if (
            "full name" in q
            or "your name" in q
            or "candidate name" in q
        ):
            return (
                self.user_profile.get(
                    "full_name"
                )
                or None
            )

        if (
            "current location" in q
            or "your city" in q
        ):
            return (
                self.user_profile.get(
                    "location"
                )
                or None
            )

        if (
            "years of experience" in q
            or "work experience" in q
        ):
            years = (
                self.user_profile.get(
                    "years_of_experience"
                )
            )

            if years is not None:
                return f"{years} years"

        if (
            "skills" in q
            or "technologies" in q
        ):
            skills = (
                self.user_profile.get(
                    "skills"
                )
                or []
            )

            if isinstance(
                skills,
                list,
            ):
                answer = ", ".join(
                    skills
                )
                return (
                    answer
                    if answer
                    else None
                )

            return (
                str(skills)
                if skills
                else None
            )

        if (
            "highest qualification"
            in q
            or "education" in q
        ):
            return (
                self.user_profile.get(
                    "highest_education"
                )
                or None
            )

        # Intentionally NOT guessed:
        # salary, relocation, legal authorization, commitments,
        # notice period, "are you available" yes/no, subjective answers.
        return None

    def fill_additional_text_questions(
        self,
        cover_letter_element: Optional[WebElement] = None,
    ) -> tuple[bool, Optional[str]]:
        """
        Fill only additional empty text/textarea questions for which
        profile facts give an explicit answer.

        Unknown fields -> pending_manual.
        """

        unresolved = []

        candidates = []

        try:
            candidates.extend(
                self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "textarea",
                )
            )
        except Exception:
            pass

        try:
            candidates.extend(
                self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "input[type='text']",
                )
            )
        except Exception:
            pass

        for field in candidates:
            try:
                if (
                    not field.is_displayed()
                    or not field.is_enabled()
                ):
                    continue

                if (
                    cover_letter_element is not None
                    and field == cover_letter_element
                ):
                    continue

                current = (
                    field.get_attribute(
                        "value"
                    )
                    or ""
                ).strip()

                if current:
                    continue

                placeholder = (
                    field.get_attribute(
                        "placeholder"
                    )
                    or ""
                ).lower()

                question = (
                    self._get_question_context(
                        field
                    )
                )

                combined = (
                    question
                    + " "
                    + placeholder
                ).strip()

                # Skip availability detail field here;
                # it is handled separately.
                if (
                    "availability"
                    in combined
                ):
                    continue

                # Skip search/navigation.
                if any(
                    token in combined
                    for token in [
                        "search",
                        "filter",
                    ]
                ):
                    continue

                # Skip empty/no-context decorative inputs.
                if not combined:
                    continue

                answer = (
                    self._known_answer_for_question(
                        combined
                    )
                )

                if answer is None:
                    unresolved.append(
                        combined[:180]
                    )
                    continue

                field.clear()
                field.send_keys(
                    answer
                )

            except StaleElementReferenceException:
                continue
            except Exception:
                continue

        if unresolved:
            return (
                False,
                (
                    "Internshala has application question(s) "
                    "that CareerSync cannot answer safely: "
                    + " | ".join(
                        unresolved[:3]
                    )
                ),
            )

        return True, None

    # =========================================================
    # SUBMIT
    # =========================================================

    def click_final_submit(
        self,
    ) -> tuple[str, str]:
        blocker = (
            self._detect_blocker()
        )

        if blocker:
            return (
                "pending_manual",
                blocker,
            )

        if self._success_detected():
            return (
                "success",
                "Application already appears to be submitted.",
            )

        submit_button = (
            self._find_visible([
                (
                    By.ID,
                    "submit",
                ),
                (
                    By.ID,
                    "submit_button",
                ),
                (
                    By.CSS_SELECTOR,
                    "button[type='submit']",
                ),
                (
                    By.XPATH,
                    "//button[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'submit')]",
                ),
                (
                    By.XPATH,
                    "//button[contains("
                    "translate(normalize-space(.),"
                    "'ABCDEFGHIJKLMNOPQRSTUVWXYZ',"
                    "'abcdefghijklmnopqrstuvwxyz'),"
                    "'submit application')]",
                ),
            ])
        )

        if not submit_button:
            self._log("❌ [Internshala] Final Submit button not found.")
            return (
                "pending_manual",
                "Could not safely identify the final Internshala Submit button.",
            )

        old_url = (
            self._current_url()
        )

        self._log("🖱️ [Internshala] Clicking final Submit...")
        if not self._safe_click(submit_button):
            return (
                "pending_manual",
                "Could not click the final Internshala Submit button.",
            )

        self._wait_for_page_change(
            old_url,
            timeout=12,
        )

        time.sleep(2)

        if self._success_detected():
            self._log("🎉 [Internshala] Application submission confirmed.")
            return (
                "success",
                "Application submitted successfully on Internshala.",
            )

        blocker = (
            self._detect_blocker()
        )

        if blocker:
            return (
                "pending_manual",
                blocker,
            )

        # Validation errors usually keep user on same form.
        body = (
            self._body_text()
        )

        validation_markers = [
            "this field is required",
            "required field",
            "please answer",
            "please fill",
        ]

        if any(
            marker in body
            for marker in validation_markers
        ):
            return (
                "pending_manual",
                "Internshala requires additional form information before submission.",
            )

        return (
            "pending_manual",
            (
                "CareerSync clicked Submit but could not confirm successful submission. "
                "Please review the saved Internshala application link."
            ),
        )

    # =========================================================
    # ONE JOB
    # =========================================================

    def apply_to_job(
        self,
        job: dict,
    ) -> tuple[str, str, Optional[str]]:
        """
        Three-step Internshala application flow.
        """

        job_url = (
            job.get("url")
        )

        job_title = (
            job.get("title")
            or "Unknown"
        )

        if not job_url:
            return (
                "error",
                "Job URL is missing.",
                None,
            )

        try:
            self._log("============================================================")
            self._log(f"📌 [Internshala] Job: {job_title}")
            self._log(f"🔗 [Internshala] URL: {job_url}")

            # -------------------------------------------------
            # STEP 1: Job detail page
            # -------------------------------------------------

            self._log("➡️ [Internshala] Opening job detail page...")
            self.driver.get(job_url)
            time.sleep(4)
            self._log(f"📍 [Internshala] Job page loaded: {self._current_url()}")

            blocker = (
                self._detect_blocker()
            )

            if blocker:
                return (
                    "pending_manual",
                    blocker,
                    job_url,
                )

            if self._success_detected():
                return (
                    "already_applied",
                    "This opportunity already appears to be applied.",
                    None,
                )

            apply_result = (
                self.click_apply_now()
            )

            if (
                apply_result
                == "already_applied"
            ):
                return (
                    "already_applied",
                    "This opportunity was already applied on Internshala.",
                    None,
                )

            if (
                apply_result
                != "clicked"
            ):
                return (
                    "pending_manual",
                    "Could not safely locate/click Internshala's Apply now button.",
                    job_url,
                )

            blocker = (
                self._detect_blocker()
            )

            if blocker:
                return (
                    "pending_manual",
                    blocker,
                    job_url,
                )

            # -------------------------------------------------
            # STEP 2: Resume intermediate page
            # -------------------------------------------------

            if (
                self.is_resume_intermediate_page()
            ):
                self._log("📄 [Internshala] Resume intermediate page detected.")

                proceeded = (
                    self.click_proceed_to_application()
                )

                if not proceeded:
                    return (
                        "pending_manual",
                        (
                            "Internshala opened the resume step, "
                            "but CareerSync could not click 'Proceed to application'."
                        ),
                        job_url,
                    )

                time.sleep(3)

            blocker = (
                self._detect_blocker()
            )

            if blocker:
                return (
                    "pending_manual",
                    blocker,
                    job_url,
                )

            # -------------------------------------------------
            # STEP 3: Final application form
            # -------------------------------------------------

            self._log("📝 [Internshala] Looking for final application form...")
            cover_letter_textarea = (
                self._find_visible([
                    (
                        By.NAME,
                        "cover_letter",
                    ),
                    (
                        By.ID,
                        "cover_letter",
                    ),
                    (
                        By.CSS_SELECTOR,
                        "textarea[name*='cover']",
                    ),
                    (
                        By.CSS_SELECTOR,
                        "textarea[id*='cover']",
                    ),
                    (
                        By.CSS_SELECTOR,
                        "textarea",
                    ),
                ])
            )

            if not cover_letter_textarea:
                # It is possible Internshala changed the flow.
                if self._success_detected():
                    return (
                        "success",
                        "Application submitted successfully.",
                        None,
                    )

                return (
                    "pending_manual",
                    (
                        "Final Internshala application form could not be "
                        "identified after the Apply/Resume steps."
                    ),
                    job_url,
                )

            self._log("✅ [Internshala] Final application form detected.")
            self._log("✍️ [Internshala] Filling cover letter...")
            cover_ok, cover_reason = self.fill_cover_letter(job)

            if not cover_ok:
                return (
                    "pending_manual",
                    cover_reason
                    or "Cover letter requires manual input.",
                    job_url,
                )

            self._log("📅 [Internshala] Checking availability question...")
            availability_ok, availability_reason = self.handle_availability()

            if not availability_ok:
                return (
                    "pending_manual",
                    availability_reason
                    or "Availability requires manual confirmation.",
                    job_url,
                )

            self._log("🔎 [Internshala] Checking additional questions...")
            extra_ok, extra_reason = (
                self.fill_additional_text_questions(
                    cover_letter_element=(
                        cover_letter_textarea
                    )
                )
            )

            if not extra_ok:
                return (
                    "pending_manual",
                    extra_reason
                    or "Additional questions require manual answers.",
                    job_url,
                )

            # Existing custom resume is intentionally untouched.
            # Browser security prevents arbitrary file selection,
            # and Internshala already remembers the user's resume.

            submit_status, submit_message = (
                self.click_final_submit()
            )

            manual_url = (
                job_url
                if submit_status
                == "pending_manual"
                else None
            )

            return (
                submit_status,
                submit_message,
                manual_url,
            )

        except Exception as exc:
            logger.exception(
                "Internshala auto-apply failed for %s: %s",
                job_title,
                exc,
            )

            return (
                "error",
                (
                    "Unexpected Internshala automation error: "
                    f"{exc}"
                ),
                job_url,
            )

    # =========================================================
    # MULTIPLE JOBS
    # =========================================================

    def run_auto_apply(
        self,
        jobs_list: list,
        max_applies: int = 5,
    ):
        """
        Process jobs in semantic-ranked order.

        Not Eligible / Needs Review do NOT consume the requested
        number of actual application attempts.

        Example:
            max_applies=3
            job 1 not eligible
            job 2 eligible -> attempt
            job 3 needs review
            job 4 eligible -> attempt
            job 5 eligible -> attempt

        Actual eligible attempts = 3.
        """

        self._log("🚀 [Internshala] Auto-apply service started.")
        self._log(f"📦 [Internshala] Ranked jobs received: {len(jobs_list)} | requested applies: {max_applies}")

        results = []
        successful_job_ids = []

        eligible_jobs = []

        # -----------------------------------------------------
        # Eligibility before browser/login
        # -----------------------------------------------------

        for job in jobs_list:
            try:
                eligibility = (
                    self.eligibility_checker
                    .check_job_eligibility(
                        job
                    )
                )
            except Exception as exc:
                logger.exception(
                    "Eligibility check failed for %s: %s",
                    job.get("title"),
                    exc,
                )

                eligibility = {
                    "status":
                        "needs_review",
                    "reason":
                        "Eligibility could not be verified safely.",
                }

            eligibility_status = (
                eligibility.get(
                    "status",
                    "needs_review",
                )
            )

            eligibility_reason = (
                eligibility.get(
                    "reason",
                    "Eligibility could not be verified safely.",
                )
            )

            if (
                eligibility_status
                in [
                    "not_eligible",
                    "needs_review",
                ]
            ):
                results.append({
                    "title":
                        job.get(
                            "title",
                            "Unknown",
                        ),

                    "url":
                        job.get(
                            "url"
                        ),

                    "manual_url":
                        (
                            job.get(
                                "url"
                            )
                            if eligibility_status
                            == "needs_review"
                            else None
                        ),

                    "job_id":
                        job.get(
                            "id"
                        ),

                    "success":
                        False,

                    "status":
                        eligibility_status,

                    "message":
                        eligibility_reason,

                    "reason":
                        eligibility_reason,

                    "eligibility_status":
                        eligibility_status,

                    "eligibility_reason":
                        eligibility_reason,

                    "applied_at":
                        datetime.now()
                        .isoformat(),
                })

                continue

            eligible_jobs.append(
                job
            )

        self._log(f"✅ [Internshala] Eligible jobs after gate: {len(eligible_jobs)}")
        if not eligible_jobs:
            self._log("ℹ️ [Internshala] No job passed the eligibility gate.")

            return (
                results,
                successful_job_ids,
            )

        # -----------------------------------------------------
        # Start browser
        # -----------------------------------------------------

        self._log("🌐 [Internshala] Starting browser stage...")
        self.driver = self.get_driver()

        try:
            login_ok, login_reason = (
                self.login()
            )
            self._log(f"🔐 [Internshala] Login result: {'SUCCESS' if login_ok else 'FAILED'}")
            if login_reason:
                self._log(f"   ↳ reason: {login_reason}")

            if not login_ok:
                # Only the first max_applies eligible jobs are marked
                # pending, because those are the ones user requested.
                for job in (
                    eligible_jobs[
                        :max_applies
                    ]
                ):
                    results.append({
                        "title":
                            job.get(
                                "title",
                                "Unknown",
                            ),

                        "url":
                            job.get(
                                "url"
                            ),

                        "manual_url":
                            job.get(
                                "url"
                            ),

                        "job_id":
                            job.get(
                                "id"
                            ),

                        "success":
                            False,

                        "status":
                            "pending_manual",

                        "message":
                            (
                                login_reason
                                or
                                "Internshala login could not be confirmed."
                            ),

                        "eligibility_status":
                            "eligible",

                        "eligibility_reason":
                            "Eligibility gate passed.",

                        "applied_at":
                            datetime.now()
                            .isoformat(),
                    })

                return (
                    results,
                    successful_job_ids,
                )

            # -------------------------------------------------
            # Apply to requested number of eligible jobs
            # -------------------------------------------------

            attempted = 0

            for job in eligible_jobs:
                if (
                    attempted
                    >= max_applies
                ):
                    break

                attempted += 1

                logger.info(
                    "=============================================="
                )

                logger.info(
                    "Internshala attempt %s/%s: %s",
                    attempted,
                    max_applies,
                    job.get(
                        "title",
                        "Unknown",
                    ),
                )

                status, message, manual_url = (
                    self.apply_to_job(
                        job
                    )
                )
                self._log(f"📋 [Internshala] Result: status={status} | message={message}")

                is_success = (
                    status
                    in [
                        "success",
                        "already_applied",
                    ]
                )

                results.append({
                    "title":
                        job.get(
                            "title",
                            "Unknown",
                        ),

                    "url":
                        job.get(
                            "url"
                        ),

                    "manual_url":
                        manual_url,

                    "job_id":
                        job.get(
                            "id"
                        ),

                    "success":
                        is_success,

                    "status":
                        status,

                    "message":
                        message,

                    "reason":
                        message,

                    "eligibility_status":
                        "eligible",

                    "eligibility_reason":
                        "Eligibility gate passed.",

                    "applied_at":
                        datetime.now()
                        .isoformat(),
                })

                if is_success:
                    successful_job_ids.append(
                        job.get(
                            "id"
                        )
                    )

                # Avoid hammering Internshala.
                time.sleep(5)

        finally:
            if self.driver:
                try:
                    if self.debug_hold_seconds > 0:
                        self._log(
                            f"⏳ [Internshala] Keeping browser visible for {self.debug_hold_seconds}s before closing..."
                        )
                        time.sleep(self.debug_hold_seconds)
                    self._log("🛑 [Internshala] Closing Chrome.")
                    self.driver.quit()
                except Exception as exc:
                    self._log(f"⚠️ [Internshala] Browser close warning: {exc}")

        return (
            results,
            successful_job_ids,
        )
