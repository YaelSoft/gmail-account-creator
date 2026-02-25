# ============================================================
#  Gmail Account Creator — User Configuration
#  Only these two settings require manual setup.
#  Everything else (name, birthday, gender, password) is
#  generated automatically at runtime.
# ============================================================

# --- 5sim Phone Verification (optional) ---------------------
# Leave blank to skip phone verification (not always required).
# Get your API key at: https://5sim.net/  →  Profile → API Key
FIVESIM_API_KEY = ""
FIVESIM_COUNTRY = "usa"  # e.g. 'usa', 'uk', 'france', 'germany'
FIVESIM_OPERATOR = "any"  # 'any' lets 5sim pick the cheapest operator

# --- Password (optional) ------------------------------------
# Leave blank to auto-generate a strong random password.
# If set, ALL created accounts will use this password.
YOUR_PASSWORD = ""
