"""
Auto Apply Service - Automatically apply to jobs on Naukri
Handles Radio Buttons (Notice Period, Yes/No, etc.)
"""

import asyncio
import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class AutoApplyService:
    def __init__(self, email: str, password: str, user_profile: dict = None):
        self.email = email
        self.password = password

        # Never invent eligibility facts. The router normally passes the
        # logged-in user's real profile. Empty defaults are intentionally
        # conservative if a field is missing.
        self.user_profile = user_profile or {
            "years_of_experience": "",
            "current_role": "",
            "current_company": "",
            "skills": [],
            "highest_education": "",
            "full_name": "",
            "location": "",
            "current_salary": "",
            "expected_salary": "",
            "notice_period": "",
        }

        self.driver = None
        self.is_logged_in = False
        self.applied_job_ids = []

    # ------------------------------------------------------------------
    # ELIGIBILITY GATE
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, tuple, set)):
            return " ".join(str(item) for item in value if item is not None)
        return str(value)

    @staticmethod
    def _parse_years(value):
        """
        Convert profile experience such as:
            0, 1.5, "2 years", "Fresher"
        into a float. Return None when genuinely unknown.
        """
        if value is None:
            return None

        text = str(value).strip().lower()

        if not text:
            return None

        if any(word in text for word in ("fresher", "fresh graduate", "no experience")):
            return 0.0

        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if not match:
            return None

        try:
            return float(match.group(1))
        except ValueError:
            return None

    def _profile_evidence_text(self) -> str:
        """
        Searchable text made only from the supplied profile. This is used
        for conservative checks; it does not invent resume facts.
        """
        keys = (
            "current_role",
            "current_company",
            "skills",
            "highest_education",
            "highest_qualification",
            "degree",
            "branch",
            "bio",
            "resume_text",
            "experience_type",
        )

        parts = []
        for key in keys:
            value = self.user_profile.get(key)
            if value:
                parts.append(self._normalise_text(value))

        return " ".join(parts).lower()

    @staticmethod
    def _extract_stored_required_experience(job_text: str):
        """
        Read CareerSync's own normalized DB field only.

        Examples:
            Required Experience: 8-13  -> 8.0
            Required Experience: 2-3   -> 2.0
            Required Experience: 6+    -> 6.0

        Returns None when the normalized field is genuinely absent.
        """
        text = job_text or ""

        match = re.search(
            r"(?:^|[\\n\\r])\\s*Required\\s+Experience\\s*:\\s*"
            r"(\\d+(?:\\.\\d+)?)"
            r"(?:\\s*(?:-|–|—|to)\\s*(\\d+(?:\\.\\d+)?))?"
            r"(?:\\s*\\+)?"
            r"(?:\\s*(?:years?|yrs?))?",
            text,
            flags=re.I,
        )

        # job_text may have been assembled with spaces, so also allow the field
        # away from a newline boundary.
        if not match:
            match = re.search(
                r"Required\\s+Experience\\s*:\\s*"
                r"(\\d+(?:\\.\\d+)?)"
                r"(?:\\s*(?:-|–|—|to)\\s*(\\d+(?:\\.\\d+)?))?"
                r"(?:\\s*\\+)?"
                r"(?:\\s*(?:years?|yrs?))?",
                text,
                flags=re.I,
            )

        if not match:
            return None

        return float(match.group(1))

    @staticmethod
    def _extract_min_experience_years(job_text: str):
        """
        Extract the HARD minimum experience from the DB/JD text.

        IMPORTANT: when CareerSync has already normalized the scraper output as
        `Required Experience: 4-7`, the minimum is ALWAYS the left side (4),
        never the upper bound (7). Explicit normalized fields are trusted first.
        """
        text = (job_text or "").lower()

        # 1) CareerSync normalized field -- highest priority.
        # Examples: Required Experience: 4-7 / 0-2 / 5 to 9 / 2 years / 6+ years
        normalized = re.search(
            r"required\s+experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:(?:-|–|—|to)\s*(\d+(?:\.\d+)?)|\+)?(?:\s*(?:years?|yrs?))?",
            text,
            flags=re.I,
        )
        if normalized:
            return float(normalized.group(1))

        # 2) Internshala/common structured experience fields.
        structured_patterns = [
            r"experience\s+range\s*:\s*(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?",
            r"total\s+experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?",
            r"experience\s*:\s*(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?",
            r"experience\s*:\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
        ]
        for pattern in structured_patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return float(match.group(1))

        # 3) Explicit hard wording in the JD. We return the first clear hard
        # minimum instead of max(all numbers), which previously could turn
        # a 4-7 range into an incorrect 7-year requirement.
        hard_patterns = [
            r"(?:minimum|min\.?|at least)\s+(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b[^.\n]{0,80}(?:experience|exp\b)",
            r"(\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b[^.\n]{0,80}(?:experience|exp\b|in\s+[a-z])",
            r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\s*(?:years?|yrs?)\b[^.\n]{0,80}(?:experience|exp\b)",
            r"(?:experience|exp\b)[^.\n]{0,45}(?:minimum|min\.?|at least)?\s*(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
            r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b[^.\n]{0,35}(?:professional|relevant|hands-on|industry|work)\s+experience",
        ]

        for pattern in hard_patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                return float(match.group(1))

        return None

    @staticmethod
    def _explicit_degree_requirements(job_text: str) -> list[str]:
        """
        Return only clearly required degree levels. 'Preferred' degree
        wording is not used to reject a candidate.
        """
        text = (job_text or "").lower()
        hard_lines = []

        for line in re.split(r"[\n\r•]+", text):
            cleaned = line.strip()
            if not cleaned:
                continue

            required_signal = any(
                token in cleaned
                for token in (
                    "required",
                    "mandatory",
                    "must have",
                    "minimum qualification",
                    "minimum education",
                    "qualification:",
                    "education:",
                )
            )

            preferred_signal = any(
                token in cleaned
                for token in ("preferred", "nice to have", "desirable")
            )

            if required_signal and not preferred_signal:
                hard_lines.append(cleaned)

        hard_text = " ".join(hard_lines)

        levels = []
        if re.search(r"\b(ph\.?d|doctorate|doctoral)\b", hard_text):
            levels.append("doctorate")
        if re.search(r"\b(master'?s|masters|m\.tech|mtech|mca|m\.s\.?|msc|mba)\b", hard_text):
            levels.append("masters")
        if re.search(r"\b(bachelor'?s|bachelors|b\.tech|btech|b\.e\.?|be\b|bca|b\.s\.?|bsc)\b", hard_text):
            levels.append("bachelors")

        return levels

    @staticmethod
    def _education_level(profile_text: str):
        text = (profile_text or "").lower()

        if re.search(r"\b(ph\.?d|doctorate|doctoral)\b", text):
            return 3

        if re.search(r"\b(master'?s|masters|m\.tech|mtech|mca|m\.s\.?|msc|mba)\b", text):
            return 2

        if re.search(r"\b(bachelor'?s|bachelors|b\.tech|btech|b\.e\.?|bca|b\.s\.?|bsc)\b", text):
            return 1

        return None

    def check_job_eligibility(self, job: dict) -> dict:
        """
        Conservative pre-apply gate.

        Returns one of:
          eligible
          not_eligible
          needs_review

        Only hard, factual requirements are used to block auto-apply.
        Semantic match score is intentionally NOT treated as eligibility.
        """
        job_text = " ".join(
            self._normalise_text(job.get(key))
            for key in (
                "title",
                "description",
                "job_description",
                "requirements",
                "skills",
                "skill_query",
                "experience",
                "education",
            )
            if job.get(key) is not None
        )

        if not job_text.strip():
            return {
                "status": "needs_review",
                "reason": "Job requirements are missing, so eligibility cannot be confirmed safely.",
            }

        reasons_passed = []

        # -------- Experience --------
        stored_required_years = self._extract_stored_required_experience(job_text)
        required_years = (
            stored_required_years
            if stored_required_years is not None
            else self._extract_min_experience_years(job_text)
        )

        raw_profile_experience = self.user_profile.get("years_of_experience")
        user_years = self._parse_years(raw_profile_experience)

        # Console/debug output BEFORE Selenium/Naukri is opened.
        normalized_exp = re.search(
            r"Required\s+Experience\s*:\s*([^\n\r|]+)",
            job_text,
            flags=re.I,
        )
        logger.info("=" * 72)
        logger.info("🔎 PRE-APPLY ELIGIBILITY CHECK (DB/JD ONLY)")
        logger.info("   🆔 Job ID                 : %s", job.get("id"))
        logger.info("   💼 Job                    : %s", job.get("title", "Unknown"))
        logger.info("   📝 DB Required Experience : %s", normalized_exp.group(1).strip() if normalized_exp else "not found")
        logger.info("   🧮 Stored field minimum    : %s", stored_required_years)
        logger.info("   👤 Profile raw experience : %r", raw_profile_experience)
        logger.info("   👤 Profile parsed years   : %s", user_years)
        logger.info("   🎯 Minimum required years : %s", required_years)

        if required_years is not None:
            if user_years is None:
                return {
                    "status": "needs_review",
                    "reason": (
                        f"Job requires at least {required_years:g} years of experience, "
                        "but the profile does not contain a reliable experience value."
                    ),
                }

            if user_years < required_years:
                logger.warning(
                    "   ❌ REJECTED: profile experience %.1f < required %.1f years",
                    user_years,
                    required_years,
                )
                return {
                    "status": "not_eligible",
                    "reason": (
                        f"Requires at least {required_years:g} years of experience; "
                        f"profile has {user_years:g} years."
                    ),
                }

            logger.info(
                "   ✅ EXPERIENCE PASSED: profile experience %.1f >= required %.1f years",
                user_years,
                required_years,
            )
            reasons_passed.append(
                f"Experience requirement passed ({user_years:g} >= {required_years:g} years)."
            )
        else:
            logger.info("   ℹ️ No hard minimum experience found in the job text; experience did not reject this job.")

        # -------- Degree --------
        required_degrees = self._explicit_degree_requirements(job_text)

        if required_degrees:
            profile_education = " ".join(
                filter(
                    None,
                    [
                        self._normalise_text(self.user_profile.get("highest_education")),
                        self._normalise_text(self.user_profile.get("highest_qualification")),
                        self._normalise_text(self.user_profile.get("degree")),
                    ],
                )
            )

            user_level = self._education_level(profile_education)

            level_map = {
                "bachelors": 1,
                "masters": 2,
                "doctorate": 3,
            }

            required_level = max(level_map[level] for level in required_degrees)

            if user_level is None:
                return {
                    "status": "needs_review",
                    "reason": (
                        "Job has a mandatory degree requirement, but the user's "
                        "education level cannot be confirmed from the profile."
                    ),
                }

            if user_level < required_level:
                readable = {
                    1: "Bachelor's",
                    2: "Master's",
                    3: "Doctorate",
                }[required_level]

                return {
                    "status": "not_eligible",
                    "reason": (
                        f"Job requires {readable} level education; "
                        "the profile does not meet that level."
                    ),
                }

            reasons_passed.append("Mandatory degree requirement passed.")

        return {
            "status": "eligible",
            "reason": (
                "Hard eligibility checks passed."
                if not reasons_passed
                else " ".join(reasons_passed)
            ),
        }

    def _answer_yes_no_question(self, question_text: str):
        """
        Answer only factual Yes/No questions we can support from profile data.
        Return None when the answer is unknown; unknown questions are NEVER
        guessed as Yes.
        """
        question = (question_text or "").lower()

        # Experience threshold questions
        required_years = self._extract_min_experience_years(question)
        if required_years is not None:
            user_years = self._parse_years(
                self.user_profile.get("years_of_experience")
            )
            if user_years is None:
                return None
            return "yes" if user_years >= required_years else "no"

        # Degree questions
        if any(token in question for token in ("bachelor", "b.tech", "btech", "degree")):
            profile_education = " ".join(
                filter(
                    None,
                    [
                        self._normalise_text(self.user_profile.get("highest_education")),
                        self._normalise_text(self.user_profile.get("highest_qualification")),
                        self._normalise_text(self.user_profile.get("degree")),
                    ],
                )
            )
            user_level = self._education_level(profile_education)
            if user_level is None:
                return None

            if any(token in question for token in ("master", "m.tech", "mtech", "mca", "mba")):
                return "yes" if user_level >= 2 else "no"

            return "yes" if user_level >= 1 else "no"

        # Unknown legal/work-authorization/visa/sponsorship and other
        # application-specific facts must be reviewed by the user.
        return None

    def get_driver(self):
        """Create stealth Chrome driver"""
        options = webdriver.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--lang=en")
        options.add_argument("--start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return driver
    
    def login_to_naukri(self):
        """Login to Naukri"""
        try:
            logger.info("🔐 Logging into Naukri...")
            self.driver.get("https://www.naukri.com/nlogin/login")
            time.sleep(3)
            
            email_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "usernameField"))
            )
            email_input.clear()
            email_input.send_keys(self.email)
            
            password_input = self.driver.find_element(By.ID, "passwordField")
            password_input.clear()
            password_input.send_keys(self.password)
            
            login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login')]")
            login_btn.click()
            
            time.sleep(5)
            
            if "login" not in self.driver.current_url:
                self.is_logged_in = True
                logger.info("✅ Successfully logged into Naukri")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def click_apply_button(self):
        """Click apply button"""
        try:
            time.sleep(2)
            
            selectors = [
                "#apply-button",
                ".apply-button",
                "button.apply-button",
                "//button[contains(text(), 'Apply')]"
            ]
            
            for selector in selectors:
                try:
                    if selector.startswith("//"):
                        btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        btn = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    if btn and btn.is_displayed():
                        btn_text = btn.text.lower()
                        if "applied" in btn_text:
                            logger.info("Already applied")
                            return "already_applied"
                        
                        btn.click()
                        logger.info("✅ Clicked apply button")
                        return "clicked"
                except:
                    continue
            return "not_found"
        except Exception as e:
            logger.error(f"Failed to click apply: {e}")
            return "error"
    
    def handle_radio_buttons(self):
        """
        Handle a visible Naukri radio-question conservatively.

        Known profile-backed questions may be answered. Unknown Yes/No
        questions are left untouched so the application falls back to
        pending_manual instead of inventing an answer.
        """
        try:
            radio_containers = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".singleselect-radiobutton, .ssrc__radio-btn-container",
            )

            for container in radio_containers:
                try:
                    radios = container.find_elements(
                        By.CSS_SELECTOR,
                        "input[type='radio']",
                    )

                    if not radios:
                        continue

                    question_text = ""

                    # Try a few nearby locations for the bot/question text.
                    question_xpaths = [
                        "..//preceding-sibling::*[contains(@class, 'botMsg')][1]//span",
                        "../preceding-sibling::*[contains(@class, 'botMsg')][1]//span",
                        "ancestor::*[contains(@class, 'chatbot') or contains(@class, 'conversation')][1]//*[contains(@class, 'botMsg')][last()]//span",
                    ]

                    for xpath in question_xpaths:
                        try:
                            elem = container.find_element(By.XPATH, xpath)
                            if elem and elem.text.strip():
                                question_text = elem.text.strip().lower()
                                break
                        except Exception:
                            continue

                    logger.info(
                        "🤖 Question: %s",
                        question_text[:160] if question_text else "Unknown radio question",
                    )

                    options = []

                    for radio in radios:
                        radio_id = radio.get_attribute("id")
                        radio_value = (radio.get_attribute("value") or "").strip()

                        label = ""

                        if radio_id:
                            try:
                                label_elem = self.driver.find_element(
                                    By.CSS_SELECTOR,
                                    f"label[for='{radio_id}']",
                                )
                                label = (label_elem.text or "").strip()
                            except Exception:
                                pass

                        if not label:
                            try:
                                label = (
                                    radio.find_element(
                                        By.XPATH,
                                        "following-sibling::label[1]",
                                    ).text
                                    or ""
                                ).strip()
                            except Exception:
                                pass

                        if not label:
                            label = radio_value

                        options.append((radio, label.lower()))

                    # Notice period is a profile-backed factual field.
                    if "notice" in question_text or "joining" in question_text:
                        user_notice = str(
                            self.user_profile.get("notice_period") or ""
                        ).strip().lower()

                        if not user_notice:
                            logger.warning(
                                "⚠️ Notice period missing; leaving question for manual review."
                            )
                            return False

                        for radio, label in options:
                            if (
                                ("immediate" in user_notice and "immediate" in label)
                                or ("15" in user_notice and "15" in label)
                                or ("30" in user_notice and "30" in label)
                                or ("60" in user_notice and "60" in label)
                                or ("90" in user_notice and "90" in label)
                            ):
                                radio.click()
                                logger.info("✅ Selected radio: %s", label)
                                time.sleep(1)
                                return True

                        logger.warning(
                            "⚠️ No notice-period option matches profile value '%s'.",
                            user_notice,
                        )
                        return False

                    # Yes/No: only answer when supported by profile data.
                    labels = [label for _, label in options]
                    has_yes = any("yes" == label or label.startswith("yes") for label in labels)
                    has_no = any("no" == label or label.startswith("no") for label in labels)

                    if has_yes and has_no:
                        answer = self._answer_yes_no_question(question_text)

                        if answer is None:
                            logger.warning(
                                "⚠️ Unknown Yes/No question; not guessing: %s",
                                question_text[:160],
                            )
                            return False

                        for radio, label in options:
                            if label == answer or label.startswith(answer):
                                radio.click()
                                logger.info(
                                    "✅ Selected profile-supported answer: %s",
                                    label,
                                )
                                time.sleep(1)
                                return True

                    logger.warning(
                        "⚠️ Radio question is not safely answerable automatically."
                    )
                    return False

                except Exception as exc:
                    logger.debug("Radio container error: %s", exc)
                    continue

            return False

        except Exception as exc:
            logger.error("Radio button handling error: %s", exc)
            return False
    def handle_text_input(self):
        """
        Fill only profile-backed text answers. Unknown free-text questions
        are not answered with a fake default such as "Yes".
        """
        try:
            input_div = self.driver.find_element(
                By.CSS_SELECTOR,
                ".textArea[contenteditable='true']",
            )

            if not input_div or not input_div.is_displayed():
                return False

            question = ""

            try:
                bot_msgs = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".botMsg span",
                )
                if bot_msgs:
                    question = (bot_msgs[-1].text or "").strip().lower()
            except Exception:
                pass

            answer = None

            if "experience" in question:
                years = self._parse_years(
                    self.user_profile.get("years_of_experience")
                )
                if years is not None:
                    answer = f"{years:g} years"

            elif "skills" in question or "technologies" in question:
                skills = self.user_profile.get("skills") or []
                if isinstance(skills, str):
                    skills = [
                        item.strip()
                        for item in skills.split(",")
                        if item.strip()
                    ]
                if skills:
                    answer = ", ".join(str(item) for item in skills[:8])

            elif "location" in question or "city" in question:
                value = self.user_profile.get("location")
                if value:
                    answer = str(value)

            elif "salary" in question or "ctc" in question:
                value = (
                    self.user_profile.get("expected_salary")
                    or self.user_profile.get("expected_ctc")
                )
                if value:
                    answer = str(value)

            elif "current role" in question or "designation" in question:
                value = self.user_profile.get("current_role")
                if value:
                    answer = str(value)

            elif "company" in question or "organization" in question:
                value = self.user_profile.get("current_company")
                if value:
                    answer = str(value)

            if not answer:
                logger.warning(
                    "⚠️ Unknown free-text question; leaving for manual review: %s",
                    question[:160] if question else "unidentified question",
                )
                return False

            input_div.click()

            # contenteditable elements do not reliably support .clear()
            try:
                self.driver.execute_script(
                    "arguments[0].innerHTML = '';",
                    input_div,
                )
            except Exception:
                pass

            input_div.send_keys(answer)
            time.sleep(0.5)

            try:
                send_btn = self.driver.find_element(
                    By.CSS_SELECTOR,
                    ".sendMsg, .send",
                )
                send_btn.click()
            except Exception:
                input_div.send_keys("\n")

            logger.info("✅ Sent profile-backed answer: %s", answer)
            return True

        except Exception:
            return False
    def click_save_submit(self):
        """Click Save/Submit button"""
        try:
            save_selectors = [
                "//button[contains(text(), 'Save')]",
                "//button[contains(text(), 'Submit')]",
                "//button[contains(text(), 'Continue')]",
                ".sendMsg",
                ".send"
            ]
            
            for selector in save_selectors:
                try:
                    if selector.startswith("//"):
                        btn = self.driver.find_element(By.XPATH, selector)
                    else:
                        btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if btn and btn.is_displayed():
                        self.driver.execute_script("arguments[0].click();", btn)
                        logger.info(f"✅ Clicked Save/Submit")
                        time.sleep(2)
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.error(f"Save click error: {e}")
            return False
    
    def close_chatbot(self):
        """Close chatbot drawer"""
        try:
            close_btn = self.driver.find_element(By.CSS_SELECTOR, ".crossIcon, .chatBot-ic-cross")
            if close_btn and close_btn.is_displayed():
                close_btn.click()
                logger.info("✅ Closed chatbot")
                time.sleep(1)
                return True
            return False
        except:
            return False
    
    def handle_chatbot(self):
        """
        Handle Naukri's application chatbot.

        Returns True only when a real successful submission or completion
        state can be detected. Unknown required questions stop automation
        and fall back to pending_manual.
        """
        try:
            max_attempts = 20

            for attempt in range(max_attempts):
                time.sleep(2)

                page_text = self.driver.page_source.lower()

                success_markers = [
                    "application submitted",
                    "successfully applied",
                    "application has been submitted",
                    "you have successfully applied",
                    "thank you for applying",
                    "application sent",
                ]

                if any(marker in page_text for marker in success_markers):
                    logger.info("🎉 Application successful!")
                    return True

                if self.handle_radio_buttons():
                    time.sleep(1)
                    continue

                if self.handle_text_input():
                    time.sleep(1)
                    continue

                # If a visible unanswered question is present and our safe
                # handlers could not answer it, do NOT click Submit/Continue.
                try:
                    visible_unanswered = False

                    radios = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "input[type='radio']",
                    )

                    visible_radios = [
                        radio
                        for radio in radios
                        if radio.is_displayed()
                    ]

                    if visible_radios and not any(
                        radio.is_selected()
                        for radio in visible_radios
                    ):
                        visible_unanswered = True

                    text_inputs = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        ".textArea[contenteditable='true']",
                    )

                    for field in text_inputs:
                        if (
                            field.is_displayed()
                            and not (field.text or "").strip()
                        ):
                            visible_unanswered = True
                            break

                    if visible_unanswered:
                        logger.warning(
                            "⚠️ Unanswered application question requires manual review; "
                            "stopping before submit."
                        )
                        return False

                except Exception:
                    pass

                if self.click_save_submit():
                    time.sleep(1)
                    continue

                if "thank you" in page_text:
                    logger.info("✅ Chatbot conversation ended")
                    return True

                if attempt > 5:
                    break

            logger.warning(
                "Could not confirm application submission from chatbot"
            )
            return False

        except Exception as e:
            logger.error(f"Chatbot handling error: {e}")
            return False
    def _is_naukri_url(self, url: str) -> bool:
        """Return True when URL belongs to Naukri."""
        try:
            host = (urlparse(url).hostname or "").lower()
            return host == "naukri.com" or host.endswith(".naukri.com")
        except Exception:
            return False

    def _find_external_window_url(self, original_handles: set) -> str | None:
        """
        Detect an external company website opened in a new tab/window.
        """
        try:
            current_handles = set(self.driver.window_handles)
            new_handles = current_handles - original_handles

            for handle in new_handles:
                try:
                    self.driver.switch_to.window(handle)
                    time.sleep(1)

                    current_url = self.driver.current_url

                    if current_url and not self._is_naukri_url(current_url):
                        return current_url

                except Exception:
                    continue

            return None

        except Exception:
            return None

    def apply_to_job(self, job_url: str, job_title: str):
        """
        Apply to a single job.

        Returns:
            ("success", None)
            ("already_applied", None)
            ("pending_manual", external_or_job_url)
            ("failed", None)
            ("error", None)
        """
        try:
            logger.info(f"📌 Opening: {job_title}")

            self.driver.get(job_url)
            time.sleep(5)

            original_handles = set(self.driver.window_handles)
            naukri_job_url = self.driver.current_url

            apply_result = self.click_apply_button()

            if apply_result == "already_applied":
                logger.info(f"Already applied: {job_title}")
                return "already_applied", None

            if apply_result != "clicked":
                logger.warning(f"No apply button: {job_title}")
                return "failed", None

            time.sleep(3)

            # New external tab/window
            external_url = self._find_external_window_url(
                original_handles
            )

            if external_url:
                logger.info(f"↗ External application detected: {external_url}")
                return "pending_manual", external_url

            # Same-tab external redirect
            current_url = self.driver.current_url

            if (
                current_url
                and current_url != naukri_job_url
                and not self._is_naukri_url(current_url)
            ):
                logger.info(f"↗ External redirect detected: {current_url}")
                return "pending_manual", current_url

            page_text = self.driver.page_source.lower()

            success_markers = [
                "application submitted",
                "successfully applied",
                "application has been submitted",
                "you have successfully applied",
                "thank you for applying",
                "application sent",
            ]

            if any(marker in page_text for marker in success_markers):
                logger.info(f"✅ Applied: {job_title}")
                return "success", None

            chatbot_success = self.handle_chatbot()

            self.close_chatbot()
            time.sleep(2)

            page_text = self.driver.page_source.lower()

            if (
                chatbot_success
                or any(marker in page_text for marker in success_markers)
            ):
                logger.info(f"✅ Applied: {job_title}")
                return "success", None

            logger.warning(f"Manual completion required: {job_title}")
            return "pending_manual", job_url

        except Exception as e:
            logger.error(f"Failed: {job_title}: {e}")
            return "error", None

    def run_auto_apply(self, jobs_list: list, max_applies: int = 5):
        """
        Evaluate ranked Naukri jobs in order and auto-apply only when
        eligibility is confirmed.

        not_eligible and needs_review jobs do NOT consume the auto-apply
        quota, so the service keeps checking lower-ranked jobs until it has
        attempted at most max_applies eligible jobs.
        """
        results = []

        logger.warning(
            "[AUTO-APPLY SERVICE INPUT] count=%d ids=%s titles=%s",
            len(jobs_list),
            [str(job.get("id")) for job in jobs_list],
            [job.get("title") for job in jobs_list],
        )

        logger.info("🚀 Starting Auto-Apply Service with eligibility gate...")

        successful_jobs = []
        eligible_attempts = 0

        # Eligibility does not require a browser/login, so evaluate first.
        # This also avoids opening Naukri when there is nothing safe to apply.
        evaluated = []

        for job in jobs_list:
            if eligible_attempts >= max_applies:
                break

            job_url = job.get("url")
            job_title = job.get("title", "Unknown")
            job_id = job.get("id")

            if not job_url:
                logger.warning("   ⛔ NOT OPENING NAUKRI for this job: %s", eligibility_reason)
                logger.info("=" * 72)
                results.append({
                    "title": job_title,
                    "url": None,
                    "manual_url": None,
                    "job_id": job_id,
                    "success": False,
                    "status": "failed",
                    "message": "Job URL is missing.",
                    "reason": "Job URL is missing.",
                    "applied_at": datetime.now().isoformat(),
                })
                continue

            eligibility = self.check_job_eligibility(job)
            eligibility_status = eligibility.get("status", "needs_review")
            eligibility_reason = eligibility.get(
                "reason",
                "Eligibility could not be confirmed.",
            )

            logger.info("=" * 60)
            logger.info("📌 Eligibility check: %s", job_title)
            logger.info(
                "🧾 %s — %s",
                eligibility_status,
                eligibility_reason,
            )
            logger.info("=" * 60)

            if eligibility_status in ("not_eligible", "needs_review"):
                results.append({
                    "title": job_title,
                    "url": job_url,
                    "manual_url": job_url if eligibility_status == "needs_review" else None,
                    "job_id": job_id,
                    "success": False,
                    "status": eligibility_status,
                    "message": eligibility_reason,
                    "reason": eligibility_reason,
                    "eligibility_status": eligibility_status,
                    "eligibility_reason": eligibility_reason,
                    "applied_at": None,
                })
                continue

            logger.info("   ✅ ELIGIBLE: only now will this job be queued for Naukri apply.")
            logger.info("=" * 72)
            evaluated.append(job)
            eligible_attempts += 1

        if not evaluated:
            logger.info(
                "No jobs passed the eligibility gate; Naukri login was not started."
            )
            return results, successful_jobs

        self.driver = self.get_driver()

        if not self.login_to_naukri():
            if self.driver:
                self.driver.quit()
                self.driver = None

            # Eligible jobs could not be attempted because login failed.
            for job in evaluated:
                results.append({
                    "title": job.get("title", "Unknown"),
                    "url": job.get("url"),
                    "manual_url": job.get("url"),
                    "job_id": job.get("id"),
                    "success": False,
                    "status": "failed",
                    "message": "Naukri login failed; auto-apply was not attempted.",
                    "reason": "Naukri login failed.",
                    "eligibility_status": "eligible",
                    "eligibility_reason": "Hard eligibility checks passed.",
                    "applied_at": None,
                })

            return results, successful_jobs

        try:
            for index, job in enumerate(evaluated, start=1):
                job_url = job.get("url")
                job_title = job.get("title", "Unknown")
                job_id = job.get("id")

                logger.info("=" * 60)
                logger.info(
                    "📌 Eligible job %s/%s: %s",
                    index,
                    len(evaluated),
                    job_title,
                )
                logger.info("=" * 60)

                status, manual_url = self.apply_to_job(
                    job_url,
                    job_title,
                )

                is_success = status in [
                    "success",
                    "already_applied",
                ]

                if status == "pending_manual":
                    message = (
                        "Eligibility passed, but external/manual application "
                        "is required. Open the provided link to complete it."
                    )
                elif status == "already_applied":
                    message = "This job was already applied on Naukri."
                elif status == "success":
                    message = "Application submitted successfully on Naukri."
                elif status == "failed":
                    message = "Could not find or complete the Apply action."
                else:
                    message = "Auto-apply failed because of an unexpected error."

                results.append({
                    "title": job_title,
                    "url": job_url,
                    "manual_url": manual_url,
                    "job_id": job_id,
                    "success": is_success,
                    "status": status,
                    "message": message,
                    "reason": message,
                    "eligibility_status": "eligible",
                    "eligibility_reason": "Hard eligibility checks passed.",
                    "applied_at": (
                        datetime.now().isoformat()
                        if is_success
                        else None
                    ),
                })

                if is_success:
                    successful_jobs.append(job_id)

                time.sleep(10)

        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

        logger.info("=" * 60)
        logger.info("🎉 Auto-Apply Complete!")
        logger.info(
            "✅ Successfully applied: %s/%s eligible attempts",
            len(successful_jobs),
            len(evaluated),
        )
        logger.info("=" * 60)

        return results, successful_jobs

async def start_auto_apply(user_email: str, user_password: str, jobs: list, user_profile: dict, max_applies: int = 5):
    """Start auto-apply process"""
    service = AutoApplyService(user_email, user_password, user_profile)
    loop = asyncio.get_event_loop()
    results, successful_jobs = await loop.run_in_executor(None, service.run_auto_apply, jobs, max_applies)
    return results, successful_jobs