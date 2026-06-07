"""
Auto Apply Service - Automatically apply to jobs on Naukri
Handles Radio Buttons (Notice Period, Yes/No, etc.)
"""

import asyncio
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from datetime import datetime

logger = logging.getLogger(__name__)


class AutoApplyService:
    def __init__(self, email: str, password: str, user_profile: dict = None):
        self.email = email
        self.password = password
        self.user_profile = user_profile or {
            'years_of_experience': '2',
            'current_role': 'Software Engineer',
            'current_company': 'Tech Solutions',
            'skills': ['Python', 'Java', 'React', 'JavaScript', 'Node.js'],
            'highest_education': "Bachelor of Technology",
            'full_name': 'Divya Dubey',
            'location': 'Bangalore',
            'current_salary': '8 LPA',
            'expected_salary': '12 LPA',
            'notice_period': '15 - 30 Days'
        }
        self.driver = None
        self.is_logged_in = False
        self.applied_job_ids = []
    
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
        """Handle all radio button types (Notice Period, Yes/No, etc.)"""
        try:
            # Find radio button container
            radio_containers = self.driver.find_elements(By.CSS_SELECTOR, ".singleselect-radiobutton, .ssrc__radio-btn-container")
            
            for container in radio_containers:
                try:
                    # Find all radio buttons in this container
                    radios = container.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                    
                    if not radios:
                        continue
                    
                    # Get the question/context
                    question_text = ""
                    try:
                        parent = container.find_element(By.XPATH, "..")
                        question_elem = parent.find_element(By.XPATH, "preceding-sibling::*[contains(@class, 'botMsg')]//span")
                        question_text = question_elem.text.lower()
                    except:
                        pass
                    
                    logger.info(f"🤖 Question: {question_text[:100] if question_text else 'Notice Period'}")
                    
                    # Determine which radio to select based on question
                    selected = False
                    
                    for radio in radios:
                        radio_id = radio.get_attribute("id")
                        radio_value = radio.get_attribute("value")
                        
                        # Get label text
                        label = ""
                        try:
                            label_elem = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                            label = label_elem.text.lower()
                        except:
                            label = radio_value.lower()
                        
                        # ========== NOTICE PERIOD SELECTION ==========
                        if "notice" in question_text or "joining" in question_text:
                            user_notice = self.user_profile.get('notice_period', '15 - 30 Days').lower()
                            
                            if "immediate" in label and ("immediate" in user_notice or "immediate" in user_notice):
                                radio.click()
                                selected = True
                                logger.info(f"✅ Selected radio: {label}")
                                break
                            elif "15" in label and "15" in user_notice:
                                radio.click()
                                selected = True
                                logger.info(f"✅ Selected radio: {label}")
                                break
                            elif "30" in label and "30" in user_notice:
                                radio.click()
                                selected = True
                                logger.info(f"✅ Selected radio: {label}")
                                break
                            elif "60" in label and "60" in user_notice:
                                radio.click()
                                selected = True
                                logger.info(f"✅ Selected radio: {label}")
                                break
                        
                        # ========== YES/NO SELECTION ==========
                        elif "yes" in label or "no" in label:
                            if "yes" in label:
                                radio.click()
                                selected = True
                                logger.info(f"✅ Selected radio: {label}")
                                break
                        
                        # ========== DEFAULT: Select first option ==========
                        if not selected and radios:
                            radios[0].click()
                            selected = True
                            logger.info(f"✅ Selected first radio: {radios[0].get_attribute('value')}")
                            break
                    
                    if selected:
                        time.sleep(1)
                        return True
                        
                except Exception as e:
                    logger.debug(f"Container error: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Radio button handling error: {e}")
            return False
    
    def handle_text_input(self):
        """Handle text input fields"""
        try:
            input_div = self.driver.find_element(By.CSS_SELECTOR, ".textArea[contenteditable='true']")
            
            if input_div and input_div.is_displayed():
                # Get question
                question = ""
                try:
                    bot_msg = self.driver.find_element(By.CSS_SELECTOR, ".botMsg span")
                    question = bot_msg.text.lower()
                except:
                    pass
                
                # Generate answer
                answer = "Yes"
                if "experience" in question:
                    answer = f"{self.user_profile.get('years_of_experience', '2')} years"
                elif "skills" in question:
                    answer = ', '.join(self.user_profile.get('skills', ['Python', 'Java'])[:3])
                elif "location" in question:
                    answer = self.user_profile.get('location', 'Bangalore')
                elif "salary" in question:
                    answer = self.user_profile.get('expected_salary', '12 LPA')
                else:
                    answer = "Yes"
                
                input_div.click()
                input_div.clear()
                input_div.send_keys(answer)
                time.sleep(0.5)
                
                # Click send
                try:
                    send_btn = self.driver.find_element(By.CSS_SELECTOR, ".sendMsg, .send")
                    send_btn.click()
                except:
                    input_div.send_keys("\n")
                
                logger.info(f"✅ Sent answer: {answer}")
                return True
            
            return False
        except:
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
        """Main chatbot handler"""
        try:
            max_attempts = 20
            
            for attempt in range(max_attempts):
                time.sleep(2)
                
                # Check success
                page_text = self.driver.page_source.lower()
                if "application submitted" in page_text or "successfully applied" in page_text:
                    logger.info("🎉 Application successful!")
                    return True
                
                # Handle radio buttons
                if self.handle_radio_buttons():
                    time.sleep(1)
                    continue
                
                # Handle text input
                if self.handle_text_input():
                    time.sleep(1)
                    continue
                
                # Click Save/Submit
                if self.click_save_submit():
                    continue
                
                # Check if done
                if "thank you" in page_text:
                    logger.info("✅ Chatbot conversation ended")
                    return True
                
                # Break if no activity
                if attempt > 5:
                    break
            
            return True
        except Exception as e:
            logger.error(f"Chatbot handling error: {e}")
            return False
    
    def apply_to_job(self, job_url: str, job_title: str):
        """Apply to a single job"""
        try:
            logger.info(f"📌 Opening: {job_title}")
            self.driver.get(job_url)
            time.sleep(5)
            
            apply_result = self.click_apply_button()
            
            if apply_result == "already_applied":
                logger.info(f"Already applied: {job_title}")
                return "already_applied"
            
            if apply_result != "clicked":
                logger.warning(f"No apply button: {job_title}")
                return "failed"
            
            time.sleep(3)
            
            # Handle chatbot
            self.handle_chatbot()
            
            # Close chatbot if still open
            self.close_chatbot()
            
            time.sleep(2)
            
            logger.info(f"✅ Applied: {job_title}")
            return "success"
            
        except Exception as e:
            logger.error(f"Failed: {job_title}: {e}")
            return "error"
    
    def run_auto_apply(self, jobs_list: list, max_applies: int = 5):
        """Run auto-apply on multiple jobs"""
        results = []
        
        logger.info("🚀 Starting Auto-Apply Service...")
        self.driver = self.get_driver()
        
        if not self.login_to_naukri():
            if self.driver:
                self.driver.quit()
            return results, []
        
        applied_count = 0
        successful_jobs = []
        
        for job in jobs_list:
            if applied_count >= max_applies:
                break
            
            job_url = job.get("url")
            job_title = job.get("title", "Unknown")
            job_id = job.get("id")
            
            if not job_url:
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📌 Job {applied_count + 1}/{max_applies}: {job_title}")
            logger.info(f"{'='*60}")
            
            status = self.apply_to_job(job_url, job_title)
            
            results.append({
                "title": job_title,
                "url": job_url,
                "job_id": job_id,
                "success": status in ["success", "already_applied"],
                "status": status,
                "applied_at": datetime.now().isoformat()
            })
            
            if status in ["success", "already_applied"]:
                applied_count += 1
                successful_jobs.append(job_id)
            
            time.sleep(10)
        
        if self.driver:
            self.driver.quit()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🎉 Auto-Apply Complete!")
        logger.info(f"✅ Successfully applied: {applied_count}/{max_applies}")
        logger.info(f"{'='*60}")
        
        return results, successful_jobs


async def start_auto_apply(user_email: str, user_password: str, jobs: list, user_profile: dict, max_applies: int = 5):
    """Start auto-apply process"""
    service = AutoApplyService(user_email, user_password, user_profile)
    loop = asyncio.get_event_loop()
    results, successful_jobs = await loop.run_in_executor(None, service.run_auto_apply, jobs, max_applies)
    return results, successful_jobs