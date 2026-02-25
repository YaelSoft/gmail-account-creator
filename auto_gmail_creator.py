"""
Gmail Account Creator v3.0
Auto-generates Gmail accounts with randomised identities.
Only 5sim API key (optional) and a preferred password (optional) need manual config.
"""

import json
import os
import platform
import random
import re
import string
import subprocess
import sys
import time
import zipfile
from datetime import datetime

# ── Third-party ────────────────────────────────────────────────────────────────
import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from faker import Faker
from fake_useragent import UserAgent

# ── Config ─────────────────────────────────────────────────────────────────────
CONFIG_DIR = "config"
DATA_DIR = "data"

try:
    from config.config import (
        FIVESIM_API_KEY,
        FIVESIM_COUNTRY,
        FIVESIM_OPERATOR,
        YOUR_PASSWORD,
    )
except ImportError:
    FIVESIM_API_KEY = ""
    FIVESIM_COUNTRY = "usa"
    FIVESIM_OPERATOR = "any"
    YOUR_PASSWORD = ""

CONFIG = {
    "version": "3.0.0",
    "theme_color": "cyan",
    "secondary_color": "magenta",
    "success_color": "green",
    "error_color": "red",
    "warning_color": "yellow",
}

console = Console()

# ── Identity generators (library-backed, no static lists) ─────────────────────
_faker = Faker('en_US')

# UserAgent with graceful fallback in case the CDN is unreachable at first run
_ua = UserAgent(
    fallback='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)

# Window sizes matched to common screen resolutions — keeps UA + viewport consistent
_WINDOW_SIZES = [
    (1920, 1080),
    (1680, 1050),
    (1440, 900),
    (1366, 768),
    (1280, 800),
    (2560, 1440),
]


def get_random_user_agent() -> tuple[str, tuple[int, int]]:
    """Return a random Chrome UA string and a matching window size."""
    try:
        ua_string = _ua.chrome
    except Exception:
        ua_string = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        )
    window_size = random.choice(_WINDOW_SIZES)
    return ua_string, window_size


def generate_random_password(length: int = 14) -> str:
    """Generate a strong random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(random.choices(chars, k=length))
        # Ensure at least one of each required type
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


def generate_random_birthday() -> tuple[int, int, int]:
    """Return (month, day, year) for a random adult birthday (age 22–55)."""
    year = random.randint(datetime.now().year - 55, datetime.now().year - 22)
    month = random.randint(1, 12)
    max_day = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month]
    if month == 2 and year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
        max_day = 29
    day = random.randint(1, max_day)
    return month, day, year


def generate_random_gender() -> str:
    """Return '1' (Male) or '2' (Female) randomly."""
    return random.choice(["1", "2"])


def generate_realistic_name() -> tuple[str, str]:
    """Return a random (first_name, last_name) pair via Faker en_US locale."""
    return _faker.first_name(), _faker.last_name()


# ── Chrome driver ──────────────────────────────────────────────────────────────


def create_driver() -> webdriver.Chrome:
    """Build and return an anti-detection Chrome WebDriver instance."""
    ua_string, window_size = get_random_user_agent()
    width, height = window_size

    options = ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-webgl")
    options.add_argument("--disable-webgl2")
    options.add_argument("--disable-logging")
    options.add_argument("--log-level=3")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--no-experiments")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--no-first-run")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"--window-size={width},{height}")
    options.add_argument(f"--user-agent={ua_string}")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    for attempt in range(3):
        try:
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.maximize_window()
            driver.set_page_load_timeout(30)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            return driver
        except Exception as e:
            console.print(
                f"[{CONFIG['warning_color']}]Driver init attempt {attempt + 1}/3 failed: {e}[/]"
            )
            time.sleep(2)
    raise RuntimeError("Could not start Chrome WebDriver after 3 attempts.")


# ── Human-like interaction ─────────────────────────────────────────────────────


def human_typing(element, text: str, delay_range: tuple = (0.05, 0.18)) -> None:
    """Type text into element with human-like random delays."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(*delay_range))


def human_click(driver, element) -> None:
    """Click element with human-like ActionChains motion."""
    ActionChains(driver).move_to_element(element).pause(
        random.uniform(0.2, 0.5)
    ).click().perform()
    time.sleep(random.uniform(0.5, 1.2))


def warm_up_session(driver) -> None:
    """Visit neutral sites to warm up the browser session before hitting Google."""
    sites = [
        "https://www.google.com",
        "https://www.wikipedia.org",
        "https://www.bbc.com",
    ]
    for site in sites:
        try:
            driver.get(site)
            time.sleep(random.uniform(1.5, 3.0))
        except Exception:
            pass


def safe_click(driver, element, retries: int = 3) -> bool:
    """Attempt multiple click strategies on an element."""
    for _ in range(retries):
        try:
            driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            pass
        try:
            ActionChains(driver).move_to_element(element).click().perform()
            return True
        except Exception:
            pass
        try:
            element.click()
            return True
        except Exception:
            time.sleep(0.5)
    return False


def smart_find_element(driver, selectors: list, timeout: int = 5):
    """Try multiple (By, value) selectors and return the first found element."""
    for by, value in selectors:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception:
            pass
    return None


def fill_field_smart(driver, element, value: str) -> bool:
    """Fill a form field using multiple fallback strategies."""
    try:
        element.clear()
        element.send_keys(value)
        return True
    except Exception:
        pass
    try:
        driver.execute_script(
            "arguments[0].value = arguments[1]; "
            "arguments[0].dispatchEvent(new Event('input', {bubbles: true})); "
            "arguments[0].dispatchEvent(new Event('change', {bubbles: true}));",
            element,
            value,
        )
        return True
    except Exception:
        pass
    try:
        ActionChains(driver).move_to_element(element).click().send_keys(value).perform()
        return True
    except Exception:
        return False


def click_next_button(driver) -> bool:
    """Click the Next / Continue button on Google signup forms."""
    selectors = [
        "//button[.//span[contains(text(), 'Next')]]",
        "//button[@jsname='LgbsSe']",
        "//div[@jsname='QkNstf']//button",
        "//button[contains(@class, 'VfPpkd-LgbsSe')]",
    ]
    for xpath in selectors:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.5)
            return True
        except Exception:
            pass
    return False


# ── Birthday / gender selectors ────────────────────────────────────────────────

MONTH_NAMES = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def set_birthday(driver, month: int, day: int, year: int) -> None:
    """Fill the birthday fields on the Google signup form.

    Google renders month as a Material listbox (not a native <select>).
    Strategy: click the trigger → wait for listbox → click the right option.
    Day and year are plain text inputs.
    """
    month_names = [
        'January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December',
    ]
    target_month = month_names[month - 1]

    # ── Month (Material listbox) ────────────────────────────────────────────
    month_filled = False

    # Strategy 1: native <select id="month"> (older form variants)
    try:
        sel = Select(WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, 'month'))
        ))
        sel.select_by_value(str(month))
        month_filled = True
    except Exception:
        pass

    # Strategy 2: exact trigger XPATH provided from live DOM inspection
    if not month_filled:
        try:
            trigger = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="month"]/div/div[1]/div'))
            )
            driver.execute_script('arguments[0].click();', trigger)
            time.sleep(0.6)
            option_xpaths = [
                f"//li[@data-value='{month}']",
                f"//li[normalize-space(.)='{target_month}']",
                f"//div[@role='option' and .//span[text()='{target_month}']]",
                f"//li[@role='option' and contains(.,'{target_month}')]",
            ]
            for opt_xpath in option_xpaths:
                try:
                    opt = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, opt_xpath))
                    )
                    driver.execute_script('arguments[0].click();', opt)
                    month_filled = True
                    break
                except Exception:
                    pass
        except Exception:
            pass
    time.sleep(0.4)

    # ── Day (plain text input) ──────────────────────────────────────────────
    day_field = smart_find_element(
        driver,
        [
            (By.ID, 'day'),
            (By.XPATH, "//input[@name='day']"),
            (By.XPATH, "//*[@aria-label='Day']"),
        ],
    )
    if day_field:
        fill_field_smart(driver, day_field, str(day))

    time.sleep(0.3)

    # ── Year (plain text input) ─────────────────────────────────────────────
    year_field = smart_find_element(
        driver,
        [
            (By.ID, 'year'),
            (By.XPATH, "//input[@name='year']"),
            (By.XPATH, "//*[@aria-label='Year']"),
        ],
    )
    if year_field:
        fill_field_smart(driver, year_field, str(year))


def set_gender(driver, gender: str) -> None:
    """Fill the gender field on the Google signup form.

    Google renders gender as a Material listbox (not a native <select>).
    Strategy: click the trigger → wait for listbox → click the right option.
    """
    gender_map = {'1': ('Male', '1'), '2': ('Female', '2'), '3': ('Rather not say', '3')}
    gender_text, gender_value = gender_map.get(gender, ('Male', '1'))

    gender_filled = False

    # Strategy 1: native <select id="gender"> (older form variants)
    try:
        sel = Select(WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.ID, 'gender'))
        ))
        sel.select_by_value(gender_value)
        gender_filled = True
    except Exception:
        pass

    # Strategy 2: exact trigger XPATH provided from live DOM inspection
    if not gender_filled:
        try:
            trigger = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="gender"]/div/div[1]/div'))
            )
            driver.execute_script('arguments[0].click();', trigger)
            time.sleep(0.6)
            option_xpaths = [
                f"//li[@data-value='{gender_value}']",
                f"//li[normalize-space(.)='{gender_text}']",
                f"//div[@role='option' and .//span[text()='{gender_text}']]",
                f"//li[@role='option' and contains(.,'{gender_text}')]",
            ]
            for opt_xpath in option_xpaths:
                try:
                    opt = WebDriverWait(driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, opt_xpath))
                    )
                    driver.execute_script('arguments[0].click();', opt)
                    gender_filled = True
                    break
                except Exception:
                    pass
        except Exception:
            pass
    # Strategy 3: JS value injection as last resort
    if not gender_filled:
        try:
            driver.execute_script(
                "var s=document.getElementById('gender');",
                "if(s){s.value=arguments[0];",
                "s.dispatchEvent(new Event('change',{bubbles:true}));}",
                gender_value,
            )
        except Exception:
            pass

# ── 5sim phone verification ────────────────────────────────────────────────────


def get_5sim_phone_number() -> dict | None:
    """Buy a virtual phone number from 5sim for Google verification."""
    if not FIVESIM_API_KEY:
        return None
    try:
        url = f"https://5sim.net/v1/user/buy/activation/{FIVESIM_COUNTRY}/{FIVESIM_OPERATOR}/google"
        headers = {
            "Authorization": f"Bearer {FIVESIM_API_KEY}",
            "Accept": "application/json",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            phone = data.get("phone", "").replace("+", "")
            return {"phone": phone, "order_id": data.get("id"), "service": "5sim"}
    except Exception as e:
        console.print(f"[{CONFIG['error_color']}]5sim error: {e}[/]")
    return None


def get_5sim_verification_code(order_id: int, max_wait: int = 120) -> str | None:
    """Poll 5sim until an SMS code arrives (up to max_wait seconds)."""
    headers = {
        "Authorization": f"Bearer {FIVESIM_API_KEY}",
        "Accept": "application/json",
    }
    url = f"https://5sim.net/v1/user/check/{order_id}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                sms_list = data.get("sms", [])
                for sms in sms_list:
                    text = sms.get("text", "")
                    match = re.search(r"\b(\d{6})\b", text)
                    if match:
                        return match.group(1)
        except Exception:
            pass
        time.sleep(5)
    return None


# ── Phone verification flow ────────────────────────────────────────────────────


def bypass_phone_verification(driver, wait) -> bool:
    """Try to skip phone verification by clicking Skip / Not now."""
    skip_xpaths = [
        "//button[.//span[contains(text(),'Skip')]]",
        "//button[contains(text(),'Skip')]",
        "//a[contains(text(),'Skip')]",
        "//span[contains(text(),'Not now')]",
        "//button[.//span[contains(text(),'Not now')]]",
        "//button[contains(@jsname,'LgbsSe') and not(contains(.,'Next'))]",
    ]
    for xpath in skip_xpaths:
        try:
            btn = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(1.5)
            return True
        except Exception:
            pass
    return False


def handle_verification_smart(driver, wait, progress=None) -> bool:
    """Handle phone verification: try skip first, then fall back to 5sim."""
    # Try to skip
    if bypass_phone_verification(driver, wait):
        return True

    # Check if phone field is actually present
    phone_field = smart_find_element(
        driver,
        [
            (By.ID, "phoneNumberId"),
            (By.XPATH, "//input[@type='tel']"),
        ],
        timeout=5,
    )

    if phone_field is None:
        return True  # No phone step, we're through

    # Try 5sim
    phone_data = get_5sim_phone_number()
    if not phone_data:
        console.print(
            f"[{CONFIG['warning_color']}]⚠ Phone required but 5sim not configured — skipping[/]"
        )
        return False

    try:
        fill_field_smart(driver, phone_field, phone_data["phone"])
        click_next_button(driver)
        time.sleep(3)

        code = get_5sim_verification_code(phone_data["order_id"])
        if not code:
            console.print(
                f"[{CONFIG['error_color']}]✗ No SMS code received from 5sim[/]"
            )
            return False

        code_field = smart_find_element(
            driver,
            [
                (By.ID, "code"),
                (By.XPATH, "//input[@type='tel' and @maxlength='6']"),
                (By.XPATH, "//input[@name='code']"),
            ],
            timeout=10,
        )
        if code_field:
            fill_field_smart(driver, code_field, code)
            click_next_button(driver)
            time.sleep(2)
            return True
    except Exception as e:
        console.print(f"[{CONFIG['error_color']}]✗ Verification error: {e}[/]")
    return False


# ── Account persistence ────────────────────────────────────────────────────────


def save_account(email: str, password: str) -> None:
    """Append created account credentials to data/accounts.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "accounts.json")

    accounts = []
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                accounts = json.load(f)
        except (json.JSONDecodeError, IOError):
            accounts = []

    accounts.append(
        {
            "email": email,
            "password": password,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active",
        }
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(accounts, f, indent=2)


def load_accounts() -> list[dict]:
    """Load all saved accounts from data/accounts.json."""
    path = os.path.join(DATA_DIR, "accounts.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# ── Statistics / views ─────────────────────────────────────────────────────────


def view_statistics() -> None:
    """Display a rich table of all saved accounts."""
    accounts = load_accounts()
    if not accounts:
        console.print(f"[{CONFIG['warning_color']}]No accounts saved yet.[/]")
        return

    table = Table(
        title="📊 Saved Accounts",
        show_header=True,
        header_style=f"bold {CONFIG['theme_color']}",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Email", style=CONFIG["theme_color"])
    table.add_column("Password", style=CONFIG["secondary_color"])
    table.add_column("Created At", style="white")
    table.add_column("Status", style=CONFIG["success_color"])

    for i, acc in enumerate(accounts, 1):
        table.add_row(
            str(i),
            acc.get("email", "—"),
            acc.get("password", "—"),
            acc.get("created_at", "—"),
            acc.get("status", "active"),
        )

    console.print(table)
    console.print(f"\n[bold]Total accounts:[/] {len(accounts)}")


# ── Main creation flow ─────────────────────────────────────────────────────────


def create_account(
    driver,
    wait,
    progress,
    task_id,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
) -> bool:
    """
    Execute the full Gmail account creation flow.
    Returns True on success, False on failure.
    """
    month, day, year = generate_random_birthday()
    gender = generate_random_gender()

    def step(msg: str, pct: int) -> None:
        if progress and task_id is not None:
            progress.update(task_id, description=f"[cyan]{msg}[/]", completed=pct)

    try:
        step("Opening signup page…", 5)
        driver.get(
            "https://accounts.google.com/signup/v2/webcreateaccount"
            "?flowName=GlifWebSignIn&flowEntry=SignUp"
        )
        time.sleep(random.uniform(2, 3))

        # ── First + last name ──────────────────────────────────────────────────
        step("Entering name…", 15)
        first_field = smart_find_element(
            driver,
            [
                (By.ID, "firstName"),
                (By.XPATH, "//input[@name='firstName']"),
            ],
        )
        last_field = smart_find_element(
            driver,
            [
                (By.ID, "lastName"),
                (By.XPATH, "//input[@name='lastName']"),
            ],
        )
        if first_field:
            fill_field_smart(driver, first_field, first_name)
        if last_field:
            fill_field_smart(driver, last_field, last_name)
        time.sleep(0.5)
        click_next_button(driver)
        time.sleep(random.uniform(1.5, 2.5))

        # ── Birthday + gender ──────────────────────────────────────────────────
        step("Entering birthday & gender…", 30)
        set_birthday(driver, month, day, year)
        time.sleep(0.5)
        set_gender(driver, gender)
        time.sleep(0.5)
        click_next_button(driver)
        time.sleep(random.uniform(1.5, 2.5))

        # ── Choose Gmail address ───────────────────────────────────────────────
        step("Choosing Gmail address…", 45)
        # Try "Create your own" option first
        custom_xpaths = [
            "//div[contains(text(), 'Create your own')]",
            "//span[contains(text(), 'Create your own')]",
            "//label[contains(., 'Create your own')]",
        ]
        for xpath in custom_xpaths:
            try:
                el = WebDriverWait(driver, 4).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                driver.execute_script("arguments[0].click();", el)
                time.sleep(1)
                break
            except Exception:
                pass

        username_field = smart_find_element(
            driver,
            [
                (By.XPATH, "//input[@name='Username']"),
                (By.XPATH, "//input[@aria-label='Username']"),
                (By.ID, "username"),
            ],
        )
        if not username_field:
            console.print(
                f"[{CONFIG['error_color']}]✗ Could not find username field[/]"
            )
            return False
        fill_field_smart(driver, username_field, username)
        time.sleep(0.5)
        click_next_button(driver)
        time.sleep(random.uniform(1.5, 2.5))

        # ── Password ───────────────────────────────────────────────────────────
        step("Setting password…", 60)
        pass_field = smart_find_element(
            driver,
            [
                (By.NAME, "Passwd"),
                (By.XPATH, "//input[@type='password']"),
            ],
        )
        pass_confirm_field = smart_find_element(
            driver,
            [
                (By.NAME, "PasswdAgain"),
                (By.XPATH, "(//input[@type='password'])[2]"),
            ],
        )
        if not pass_field:
            console.print(
                f"[{CONFIG['error_color']}]✗ Could not find password field[/]"
            )
            return False

        human_typing(pass_field, password)
        if pass_confirm_field:
            human_typing(pass_confirm_field, password)
        time.sleep(0.5)

        submit_btn = smart_find_element(
            driver,
            [
                (By.XPATH, "//button[contains(@class,'VfPpkd-LgbsSe')]"),
                (By.XPATH, "//button[@type='submit']"),
            ],
        )
        if submit_btn:
            safe_click(driver, submit_btn)
        time.sleep(random.uniform(2, 3))

        # ── Phone verification ─────────────────────────────────────────────────
        step("Handling verification…", 75)
        handle_verification_smart(driver, wait, progress)
        time.sleep(random.uniform(2, 3))

        # ── Finish ─────────────────────────────────────────────────────────────
        step("Finalising…", 90)
        # Accept any remaining prompts (privacy, terms, etc.)
        for _ in range(3):
            for xpath in [
                "//button[.//span[contains(text(),'I agree')]]",
                "//button[.//span[contains(text(),'Confirm')]]",
                "//button[.//span[contains(text(),'Done')]]",
                "//button[.//span[contains(text(),'Next')]]",
            ]:
                try:
                    btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.XPATH, xpath))
                    )
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1.5)
                except Exception:
                    pass

        save_account(f"{username}@gmail.com", password)
        step("Done!", 100)
        console.print(
            f"[{CONFIG['success_color']}]✓ Account created: {username}@gmail.com[/]"
        )
        return True

    except Exception as e:
        console.print(f"[{CONFIG['error_color']}]✗ Creation failed: {e}[/]")
        return False


# ── Banner / UI ────────────────────────────────────────────────────────────────


def show_banner() -> None:
    """Display the application banner."""
    banner = Text()
    banner.append("  ██████╗  ███╗   ███╗ █████╗ ██╗██╗     \n", style="bold cyan")
    banner.append("  ██╔════╝ ████╗ ████║██╔══██╗██║██║     \n", style="bold cyan")
    banner.append("  ██║  ███╗██╔████╔██║███████║██║██║     \n", style="bold cyan")
    banner.append("  ██║   ██║██║╚██╔╝██║██╔══██║██║██║     \n", style="bold cyan")
    banner.append("  ╚██████╔╝██║ ╚═╝ ██║██║  ██║██║███████╗\n", style="bold cyan")
    banner.append("   ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═╝╚══════╝\n", style="bold cyan")
    banner.append("\n  Gmail Account Creator ", style="bold white")
    banner.append(f"v{CONFIG['version']}", style="bold magenta")
    banner.append("\n  Fully automated · Zero manual config required\n", style="dim")

    console.print(Panel(banner, border_style="cyan"))


def show_menu() -> None:
    """Print the main menu."""
    tc = CONFIG["theme_color"]
    sc = CONFIG["secondary_color"]
    console.print(f"\n[bold {tc}]  ┌─────────────────────────────┐[/]")
    console.print(
        f"[bold {tc}]  │[/]  [bold white]  MAIN MENU[/]                [bold {tc}]│[/]"
    )
    console.print(f"[bold {tc}]  ├─────────────────────────────┤[/]")
    console.print(
        f"[bold {tc}]  │[/]  [bold {sc}]1.[/] Create Gmail accounts   [bold {tc}]│[/]"
    )
    console.print(
        f"[bold {tc}]  │[/]  [bold {sc}]2.[/] View saved accounts     [bold {tc}]│[/]"
    )
    console.print(
        f"[bold {tc}]  │[/]  [bold {sc}]3.[/] Export accounts to CSV  [bold {tc}]│[/]"
    )
    console.print(
        f"[bold {tc}]  │[/]  [bold {sc}]4.[/] Show current config     [bold {tc}]│[/]"
    )
    console.print(
        f"[bold {tc}]  │[/]  [bold {sc}]5.[/] Exit                    [bold {tc}]│[/]"
    )
    console.print(f"[bold {tc}]  └─────────────────────────────┘[/]\n")


def export_accounts_csv() -> None:
    """Export saved accounts to a CSV file."""
    accounts = load_accounts()
    if not accounts:
        console.print(f"[{CONFIG['warning_color']}]No accounts to export.[/]")
        return
    path = os.path.join(DATA_DIR, "accounts.csv")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("email,password,created_at,status\n")
        for acc in accounts:
            f.write(
                f"{acc.get('email', '')},{acc.get('password', '')}"
                f",{acc.get('created_at', '')},{acc.get('status', '')}\n"
            )
    console.print(
        f"[{CONFIG['success_color']}]✓ Exported {len(accounts)} accounts → {path}[/]"
    )


def show_config() -> None:
    """Display the current effective configuration."""
    table = Table(
        title="Current Configuration",
        show_header=True,
        header_style=f"bold {CONFIG['theme_color']}",
    )
    table.add_column("Setting", style="bold white")
    table.add_column("Value", style=CONFIG["theme_color"])

    pwd_display = (
        YOUR_PASSWORD
        if YOUR_PASSWORD
        else "[dim](random — generated per account)[/dim]"
    )
    key_display = (
        (FIVESIM_API_KEY[:8] + "…")
        if FIVESIM_API_KEY
        else "[dim](not set — phone step skipped)[/dim]"
    )

    table.add_row("Password", pwd_display)
    table.add_row("5sim API Key", key_display)
    table.add_row("5sim Country", FIVESIM_COUNTRY)
    table.add_row("5sim Operator", FIVESIM_OPERATOR)
    table.add_row("Name pool", "Faker en_US (unlimited, dynamic)")
    table.add_row("Birthday", "Random (age 22–55)")
    table.add_row("Gender", "Random")

    console.print(table)
    console.print(
        f"\n[dim]Edit [bold]config/config.py[/bold] to set your 5sim API key or a fixed password.[/dim]\n"
    )


# ── Entry point ────────────────────────────────────────────────────────────────


def main() -> None:
    """Application entry point — interactive menu loop."""
    driver = None

    while True:
        os.system("cls" if platform.system() == "Windows" else "clear")
        show_banner()
        show_menu()

        choice = Prompt.ask(
            f"[bold {CONFIG['theme_color']}]  Enter choice[/]",
            choices=["1", "2", "3", "4", "5"],
            default="1",
        )

        if choice == "1":
            try:
                num_str = Prompt.ask(
                    f"[bold {CONFIG['theme_color']}]How many accounts to create[/]",
                    default="1",
                )
                num_accounts = max(1, int(num_str))
            except ValueError:
                num_accounts = 1

            created = 0
            failed = 0

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                overall = progress.add_task(
                    f"[cyan]Overall progress[/]",
                    total=num_accounts,
                )

                for i in range(num_accounts):
                    first, last = generate_realistic_name()
                    suffix = random.randint(1000, 9999)
                    username = f"{first.lower()}{last.lower()}{suffix}"
                    password = (
                        YOUR_PASSWORD if YOUR_PASSWORD else generate_random_password()
                    )

                    acc_task = progress.add_task(
                        f"[cyan]Account {i + 1}/{num_accounts}[/]",
                        total=100,
                    )

                    try:
                        driver = create_driver()
                        wait = WebDriverWait(driver, 15)
                        warm_up_session(driver)

                        success = create_account(
                            driver,
                            wait,
                            progress,
                            acc_task,
                            username,
                            password,
                            first,
                            last,
                        )
                        if success:
                            created += 1
                        else:
                            failed += 1
                    except Exception as e:
                        console.print(
                            f"[{CONFIG['error_color']}]✗ Account {i + 1} error: {e}[/]"
                        )
                        failed += 1
                    finally:
                        if driver:
                            try:
                                driver.quit()
                            except Exception:
                                pass
                            driver = None

                    progress.update(overall, advance=1)
                    progress.remove_task(acc_task)

                    if i < num_accounts - 1:
                        time.sleep(random.uniform(3, 7))

            c = CONFIG["success_color"]
            e = CONFIG["error_color"]
            console.print(
                f"\n[bold]Results:[/] [{c}]{created} created[/] · [{e}]{failed} failed[/]\n"
            )
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "2":
            view_statistics()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "3":
            export_accounts_csv()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "4":
            show_config()
            Prompt.ask("[dim]Press Enter to continue[/dim]", default="")

        elif choice == "5":
            console.print(f"\n[{CONFIG['theme_color']}]Goodbye! 👋[/]\n")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n[{CONFIG['warning_color']}]Interrupted. Goodbye![/]\n")
        sys.exit(0)
