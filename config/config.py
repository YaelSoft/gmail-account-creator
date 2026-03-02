# ============================================================
#  Gmail Account Creator — User Configuration
# ============================================================

# --- 5sim Phone Verification (Atlama Modu) ------------------
# API anahtarını boş bırakıyoruz, böylece bot onay istemeyen 
# nadir durumları kovalayacak.
FIVESIM_API_KEY = "" 
FIVESIM_COUNTRY = "usa"
FIVESIM_OPERATOR = "any"

# --- Password Ayarı -----------------------------------------
# Boş bırakırsan rastgele oluşturur. Hatırlamak için sabit yapabilirsin.
YOUR_PASSWORD = "" 

# --- Önemli: Tarayıcı Ayarları (Codespaces İçin) ------------
# Eğer botun içinde "browser_settings" gibi bir yer varsa:
HEADLESS_MODE = True  # GitHub sanal makinesinde bu MUTLAKA True olmalı.
NO_SANDBOX = True
