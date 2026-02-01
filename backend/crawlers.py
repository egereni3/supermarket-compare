from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

def get_sainsburys_results(search_query):

    # Setup
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.5993.70 Safari/537.36"
    )
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.sainsburys.co.uk/")
    wait = WebDriverWait(driver, 20)


    # Accept cookies if shown 
    try: 
        cookie_btn = wait.until( EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Continue and accept')]")) ) 
        cookie_btn.click() 
    except: 
        pass 

    # Wait for cookie overlay to disappear
    WebDriverWait(driver, 20).until(
        EC.invisibility_of_element_located((By.CSS_SELECTOR, ".onetrust-pc-dark-filter"))
    )

    # Search
    search_input = wait.until(EC.presence_of_element_located((By.ID, "term")))
    search_input.clear()
    search_input.send_keys(search_query)

    search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='search-btn']")))
    search_button.click()

    # Wait for product grid
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article[data-testid^='product-tile-']")))
        time.sleep(2)
    except:
        driver.quit()
        return []

    # Extract
    products = driver.find_elements(By.CSS_SELECTOR, "article[data-testid^='product-tile-']")
    results = []

    for p in products:
        try:
            name_el = p.find_element(By.CSS_SELECTOR, "h2[data-testid='product-tile-description'] a")
            name = name_el.text.strip()
        except:
            name = "N/A"

        try:
            price_el = p.find_element(By.CSS_SELECTOR, "span[data-testid='pt-retail-price']")
            price = price_el.text.strip()
        except:
            price = "N/A"

        results.append([name, price])

    driver.quit()
    return results

def get_homebargains_results(search_query):
    # Setup
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    driver.get("https://home.bargains/")

    # Accept cookies
    try:
        cookie_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Accept All')]")
        ))
        cookie_btn.click()
    except:
        None

    # Search
    search_input = wait.until(EC.presence_of_element_located((By.ID, "autocomplete-0-input")))
    search_input.clear()
    search_input.send_keys(search_query)

    search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Submit']")))
    search_button.click()

    # Wait for results
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.ais-Hits-item")))
    except:
        driver.quit()
        return []

    # Extract
    items = []
    product_cards = driver.find_elements(By.CSS_SELECTOR, "li.ais-Hits-item")

    for card in product_cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, ".title").text.strip()
        except:
            name = None

        try:
            price = card.find_element(By.CSS_SELECTOR, ".price").text.strip()
        except:
            price = None

        if name and price:
            items.append([name,price])

    driver.quit()
    return items

def get_morrisons_results(search_query):
    # Setup
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    driver.get("https://groceries.morrisons.com/")

    # Accept cookies
    try:
        cookie_btn = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Accept All')]")
        ))
        cookie_btn.click()
    except:
        None

    # Search
    search_input = wait.until(EC.presence_of_element_located((By.ID, "search")))
    search_input.clear()
    search_input.send_keys(search_query)

    search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
    search_button.click()

    # Wait for the product page to load
    try:
        wait.until(EC.presence_of_element_located((By.ID, "product-page")))
        
    except:
        driver.quit()
        return []


    # Extract
    
    items = []
    time.sleep(2)
    product_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-retailer-anchor^='fop']")


    for card in product_cards:
        try:
            # Product name
            name = card.find_element(By.CSS_SELECTOR, "h3[data-test='fop-title']").text.strip()
        except:
            name = None

        try:
            # Product price
            price = card.find_element(By.CSS_SELECTOR, "span[data-test='fop-price']").text.strip()
        except:
            price = None

        if name and price:
            items.append([name, price])

    driver.quit()
    return items

#Add a synthetic website instead of sainsburys

#Modular scraping, changing circumstances
# Potential use of LLMs

#    "perfect": {
#        "objective": "Design and implement a CO₂ monitoring device achieving ±1% accuracy, logging every 60s to a secure dashboard, with a field-tested prototype demonstrated by Week 8.",
#        "json": {"S":10,"M":10,"A":10,"R":5,"T":5,"W":10,"total_50":50,"reason":"Explicit outcome, strong metrics, feasible scope, clear deadline, polished writing."}
#    },
#    "strong": {
#        "objective": "Develop a mobile dashboard to visualise lab temperature and humidity with <2s update latency, fully operational by the end of Semester 1.",
#        "json": {"S":8,"M":8,"A":8,"R":4,"T":3.5,"W":8,"total_50":39.5,"reason":"Clear deliverable and metrics; deadline less explicit than a dated week; feasible and well-written."}
#    },
#    "pass": {
#        "objective": "Design a user-friendly interface for sensor data.",
#        "json": {"S":4,"M":3.5,"A":4,"R":2.5,"T":0,"W":4,"total_50":18,"reason":"Outcome stated but subjective and no timeframe; measurability weak; writing acceptable."}
#    },
#    "weak": {
#        "objective": "Investigate algorithms using MATLAB.",
#        "json": {"S":2,"M":1,"A":2,"R":1,"T":0,"W":2,"total_50":8,"reason":"Process-focused, no metrics or deadline; rationale unclear; methodology jargon dominates."}
#    },
#    "subjective": {
#        "objective": "Evaluate system power use to achieve significant reduction compared to current solutions.",
#        "json": {"S":4,"M":3,"A":4,"R":2,"T":0,"W":4,"total_50":17,"reason":"Subjective 'significant' with no metric; no timeframe; feasibility unclear."}
#    },
#    "process_time": {
#        "objective": "Investigate scheduling algorithms and submit a brief summary report by Week 4.",
#        "json": {"S":3,"M":2,"A":3,"R":2,"T":5,"W":4,"total_50":19,"reason":"Process-focused; weak metrics; clear deadline improves T only."}
#    }
# fewshotting Gemini good option
