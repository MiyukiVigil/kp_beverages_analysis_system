import os

# File Paths
MENU_FILE = "menu.json"
SETTINGS_FILE = "settings.json"
SALES_DIR = "sales"

# Ensure directories exist
if not os.path.exists(SALES_DIR):
    os.makedirs(SALES_DIR)

# Defaults
DEFAULT_MENU = {
  "Kopi": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Kopi O": { "temperature": [ { "type": "Hot", "price": 2.00 }, { "type": "Cold", "price": 2.30 } ] },
  "Teh": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] }
}

DEFAULT_SETTINGS = {
    "big_cup_g": 20.0,
    "small_cup_g": 10.0
}

TIN_DRINKS = {"100 Plus", "Cola", "Teh Bunga"}