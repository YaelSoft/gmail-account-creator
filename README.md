# Gmail Account Creator

Automated Gmail account creation with anti-detection evasion, optional phone verification via 5sim, and a rich terminal UI. Everything is randomized — name, birthday, gender, password, user agent, and window size.

---

## Requirements

- Python 3.10+
- Google Chrome (latest)

---

## Installation

```bash
git clone https://github.com/vichhka-git/gmail-account-creator.git
cd gmail-account-creator
pip install -r requirements.txt
```

---

## Configuration

Open `config/config.py` — it has **two optional settings**:

```python
# 5sim phone verification (leave blank to skip)
# Get your key at https://5sim.net → Profile → API Key
FIVESIM_API_KEY  = ""
FIVESIM_COUNTRY  = "usa"   # usa, uk, france, germany, etc.
FIVESIM_OPERATOR = "any"   # 'any' picks the cheapest operator

# Password (leave blank for a random strong password)
YOUR_PASSWORD = ""
```

That's it. Nothing else needs to be changed.

---

## Usage

```bash
python auto_gmail_creator.py
```

### Menu

| Option | Action |
|--------|--------|
| `1` | Create Gmail accounts |
| `2` | View saved accounts |
| `3` | Export accounts to CSV |
| `4` | Show current config |
| `5` | Exit |

### What gets randomized automatically

| Field | Source |
|-------|--------|
| First & last name | `Faker('en_US')` — unlimited, never repeats |
| User agent | `fake-useragent` — real Chrome UA strings from live CDN |
| Window size | Matched to UA so viewport and OS never mismatch |
| Birthday | Random age 22–55 |
| Gender | Random Male / Female |
| Password | 14-char (upper + lower + digit + symbol) — unless you set `YOUR_PASSWORD` |

---

## How it works

For each account the tool:

1. Launches Chrome with anti-detection flags and a fresh random identity
2. Warms up the session by visiting neutral sites (Google, Wikipedia, BBC)
3. Fills in the signup form — name, birthday, gender, custom username
4. Attempts to skip phone verification automatically
5. Falls back to 5sim for a real SMS code if skip is unavailable (requires API key)
6. Saves credentials to `data/accounts.json`

---

## Anti-Detection

- `--disable-blink-features=AutomationControlled` + `navigator.webdriver` override
- Random Chrome user agent via `fake-useragent` (Chrome 120+, updated from CDN)
- Window size matched to UA platform — no viewport/OS fingerprint mismatch
- Human-like typing with random per-keystroke delays (50–180ms)
- Human-like mouse clicks via ActionChains with random pauses
- Session warm-up before touching any Google URL

---

## Phone Verification

The tool first tries to skip verification entirely using multiple button selectors. If Google requires a number anyway and `FIVESIM_API_KEY` is set, it automatically:

1. Buys a virtual number from 5sim
2. Enters it on the verification page
3. Polls 5sim for the SMS code (up to 2 minutes)
4. Submits the code

If no API key is configured and skip fails, the account attempt is abandoned.

---

## Project Structure

```
gmail-account-creator/
├── auto_gmail_creator.py   # Full application (single file)
├── requirements.txt
├── config/
│   └── config.py           # Only file you need to edit
├── data/
│   └── accounts.json       # Saved credentials (auto-created)
├── AGENTS.md
├── SECURITY.md
└── README.md
```

---

## Saved Accounts

Accounts are saved to `data/accounts.json`:

```json
[
  {
    "email": "johnsmith4821@gmail.com",
    "password": "Xk9#mP2$wQnL7v",
    "created_at": "2026-02-25 10:42:11",
    "status": "active"
  }
]
```

Use menu option `3` to export as CSV.

---

## Troubleshooting

**ChromeDriver error** — `webdriver-manager` handles this automatically. Make sure Chrome is installed and up to date.

**Element not found / month or gender not filled** — Google occasionally A/B tests their signup form. Try running again; the tool uses multiple selector fallbacks.

**Phone verification always required** — Configure a 5sim API key with account balance.

**`ModuleNotFoundError`** — Run `pip install -r requirements.txt` again.

---

## Legal

This tool is for educational purposes only. Creating multiple Gmail accounts may violate [Google's Terms of Service](https://policies.google.com/terms). Use responsibly and at your own risk. The authors accept no liability for misuse, account suspensions, or any consequences arising from use of this software.
