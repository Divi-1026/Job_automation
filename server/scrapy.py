from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
import time

def scrape_naukri_jobs(skill):
    skill_query = skill.replace(" ", "-")
    url = f"https://www.naukri.com/{skill_query}-jobs"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    # 🕵️ Apply stealth
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
    )
    
    driver.get(url)
    
    # ⏳ Wait for full load
    time.sleep(12)
    
    jobs = []
    
    job_cards = driver.find_elements(By.CSS_SELECTOR, "article.jobTuple")
    
    print("Jobs found:", len(job_cards))
    
    for job in job_cards:
        try:
            title = job.find_element(By.CSS_SELECTOR, "a.title").text
            company = job.find_element(By.CSS_SELECTOR, "a.subTitle").text
            location = job.find_element(By.CSS_SELECTOR, ".location").text
            experience = job.find_element(By.CSS_SELECTOR, ".experience").text
            
            jobs.append({
                "title": title,
                "company": company,
                "location": location,
                "experience": experience
            })
        except:
            continue
    
    input("Press ENTER to close browser...")
    driver.quit()
    
    return jobs


if __name__ == "__main__":
    skill = input("Enter skill: ")
    
    jobs = scrape_naukri_jobs(skill)
    
    for i, job in enumerate(jobs, 1):
        print(f"\nJob {i}")
        print(job)