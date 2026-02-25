# AGENTS.md — Gmail Account Creator

Guidance for AI coding agents working in this repository.

---

## Project Overview

A single-file Python automation tool that creates Gmail accounts using Selenium + Chrome,
with anti-detection evasion, optional 5sim phone verification, and a rich TUI.
Everything is randomised at runtime — name, birthday, gender, and password.

**Entry point:** `auto_gmail_creator.py`
**Language:** Python 3.13
**No build step required** — pure Python, runs directly.

---

## Environment Setup

```bash
pip install -r requirements.txt
```

Required packages (pinned minimums):
- selenium>=4.15.0
- webdriver-manager>=4.0.0
- rich>=13.7.0
- requests>=2.31.0
- unidecode>=1.3.7
- beautifulsoup4>=4.12.0
- fp>=0.1.0

---

## Running the Tool

```bash
python auto_gmail_creator.py
```

Launches an interactive rich TUI menu (choices 1–5). No tests, no test runner.

---

## Project Structure

```
.
├── auto_gmail_creator.py     # Entire application — single file
├── requirements.txt
├── config/
│   └── config.py             # ONLY user-editable file: 5sim key + optional password
├── data/
│   └── accounts.json         # Output: saved credentials (auto-created, do NOT commit)
├── AGENTS.md
├── LICENSE
├── SECURITY.md
└── README.md
```

---

## Configuration

Only `config/config.py` needs manual editing. Everything else is automatic.

```python
# 5sim phone verification (optional — skip by leaving blank)
FIVESIM_API_KEY  = ''        # get from https://5sim.net → Profile → API Key
FIVESIM_COUNTRY  = 'usa'     # e.g. 'usa', 'uk', 'france', 'germany'
FIVESIM_OPERATOR = 'any'     # 'any' picks cheapest operator

# Password (optional — leave blank for random strong password)
YOUR_PASSWORD = ''
```

**All other values are generated automatically at runtime:**
- Name — `Faker('en_US')` library — unlimited, never repeats predictably
- User-Agent — `fake-useragent` library — real browser UA strings, updates from CDN
- Window size — matched to UA platform (prevents viewport/UA OS fingerprint mismatch)
- Birthday — random age 22–55
- Gender — random Male / Female
- Password — 14-char random (upper + lower + digit + symbol) if `YOUR_PASSWORD` is blank
---

## Key Functions Reference

| Function | Purpose |
|---|---|
| `main()` | App entry point, menu loop |
| `create_driver()` | Builds anti-detection Chrome instance via webdriver-manager |
| `create_account(driver, wait, progress, task_id, username, password, first, last)` | Full Gmail creation flow |
| `handle_verification_smart(driver, wait, progress)` | Skip phone or fall back to 5sim |
| `bypass_phone_verification(driver, wait)` | Click Skip/Not now buttons |
| `save_account(email, password)` | Appends credentials to `data/accounts.json` |
| `load_accounts()` | Reads and returns all saved accounts |
| `generate_realistic_name()` | Returns `(first, last)` via `Faker('en_US')` — unlimited pool |
| `get_random_user_agent()` | Returns `(ua_string, (width, height))` via `fake-useragent` — Chrome UA + matched window size |
| `generate_random_birthday()` | Returns `(month, day, year)` for age 22–55 |
| `generate_random_gender()` | Returns `'1'` (Male) or `'2'` (Female) |
| `human_typing(element, text)` | Mimics human keystroke delays |
| `human_click(driver, element)` | ActionChains click with pause |
| `warm_up_session(driver)` | Visits neutral sites before Google |
| `view_statistics()` | Rich table of saved accounts |
| `export_accounts_csv()` | Exports accounts to `data/accounts.csv` |
| `show_config()` | Displays current effective config |
| `safe_click(driver, element)` | Multi-strategy click fallback |
| `smart_find_element(driver, selectors)` | Tries multiple (By, value) pairs |
| `fill_field_smart(driver, element, value)` | send_keys → JS → ActionChains fallback |
| `set_birthday(driver, month, day, year)` | Fills birthday dropdowns/inputs |
| `set_gender(driver, gender)` | Fills gender dropdown |
| `get_5sim_phone_number()` | Buys virtual number from 5sim |
| `get_5sim_verification_code(order_id)` | Polls 5sim for SMS code |

---

## Code Style Guidelines

### General

- **One file** architecture — all logic lives in `auto_gmail_creator.py`. Do not split into packages.
- **Python 3.13** — use modern syntax (f-strings, `match`/`case`, `type | None`).
- Follow existing style so diffs remain minimal.

### Naming Conventions

| Entity | Convention | Example |
|---|---|---|
| Functions | `snake_case` | `create_driver()`, `human_typing()` |
| Variables | `snake_case` | `user_agent`, `max_retries` |
| Module-level constants | `SCREAMING_SNAKE_CASE` | `CONFIG_DIR`, `CONFIG` |
| Config dict key values | `lower_case strings` | `CONFIG['theme_color']` |
| Classes (if added) | `PascalCase` | `AccountManager` |

### Imports

- Standard library → third-party → local, each group separated by a blank line.
- Explicit named imports only — no wildcard `*`.
- Do not add new top-level imports not in `requirements.txt` without also updating that file.

### Formatting

- **4-space indentation** — no tabs.
- Lines ≤120 chars preferred.
- No formatter configured — match surrounding style manually.
- String quotes: **single quotes** for simple strings, **double quotes** inside f-strings.

### Docstrings

```python
def human_typing(element, text, delay_range=(0.05, 0.18)):
    """Type text into element with human-like random delays."""
```

One-liner for simple helpers; multi-line for complex flows.

### Rich UI Patterns

- All output through `console = Console()` (module-level singleton).
- Color tags from `CONFIG`:
  ```python
  console.print(f"[{CONFIG['success_color']}]✓ Done[/]")
  console.print(f"[{CONFIG['error_color']}]✗ Failed: {e}[/]")
  console.print(f"[{CONFIG['warning_color']}]⚠ Warning[/]")
  ```
- Progress bars via `rich.progress.Progress` context manager.
- Menus via `Prompt.ask()` with `choices=[...]`.
- **Never use `print()`** — always `console.print()`.

### Error Handling

- Prefer `except Exception as e:` over bare `except:`.
- Always show a user-facing `console.print(...)` before continuing silently.
- Retry pattern: `for attempt in range(3):` with `time.sleep(2)` between attempts.
- Do not raise unhandled exceptions — catch, log, return `None` or `False`.

### Selenium / Browser Patterns

- Always create driver via `create_driver()` — never call `webdriver.Chrome()` elsewhere.
- `create_driver()` calls `get_random_user_agent()` — sets both `--user-agent` and `--window-size` together. Never override just one without the other.
- Use `smart_find_element(driver, selectors)` for resilient element lookup.
- Use `fill_field_smart(driver, element, value)` for resilient input filling.
- Use `WebDriverWait(driver, timeout).until(EC.element_to_be_clickable(...))` for waits.
- Call `warm_up_session(driver)` before any Google interaction.
- Keep `--disable-blink-features=AutomationControlled` and the `navigator.webdriver` override intact.

### Data / File I/O

- Always use `save_account(email, password)` — never write `accounts.json` directly.
- Always use `load_accounts()` — never read `accounts.json` directly.
- `json.dump` with `indent=2` for any JSON files.

---

## Things to Avoid

- **Do not** add `@pytest.mark` or test files — no test infrastructure exists.
- **Do not** use `driver.find_element` without a `WebDriverWait` or `smart_find_element` wrapper.
- **Do not** hardcode API keys or passwords in source — use `config/config.py`.
- **Do not** use `print()` — use `console.print()`.
- **Do not** create new modules/packages without explicitly abandoning the single-file structure.
- **Do not** commit `data/accounts.json` — it contains sensitive credentials.
- **Do not** add static name lists (`FIRST_NAMES`, `LAST_NAMES`) — use `_faker = Faker('en_US')` instead.
- **Do not** add static user-agent lists — use `_ua = UserAgent(fallback=...)` instead.
