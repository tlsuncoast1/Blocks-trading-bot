# blofin_bot.py
import os
import time
import hmac
import hashlib
import requests
import datetime
import logging
from typing import Dict
import uuid
import base64

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
TRADE_SYMBOL = "BTCUSDT"
TRADE_INTERVAL = "1h"
LEVERAGE = int(os.getenv("LEVERAGE", 10))
RISK_PER_TRADE = 0.10  # 10%

API_KEY = os.getenv("BLOFIN_API_KEY")
API_SECRET = os.getenv("BLOFIN_API_SECRET")
API_PASSPHRASE = "newPass1"
BASE_URL = "https://api.blofin.com"

# --- Logging ---
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Helper Functions ---
def get_klines(symbol: str, interval: str, limit=100):
    query = f"?symbol={symbol}&interval={interval}&limit={limit}"
    url = f"{BASE_URL}/v1/public/market/kline{query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        print(f"Raw kline response: {response.text}")
        return response.json()["data"]
    except Exception as e:
        logging.error(f"❌ Failed to fetch klines: {e}")
        print(f"❌ Failed to fetch klines: {e}")
        return []

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_bot():
    klines = get_klines(TRADE_SYMBOL, TRADE_INTERVAL, 100)
    if not klines:
        logging.warning("⚠️ No kline data available — skipping this cycle.")
        print("⚠️ No kline data available — skipping this cycle.")
        return

    closes = pd.Series([float(k[4]) for k in klines])
    rsi = calculate_rsi(closes, RSI_PERIOD)

    last_rsi = rsi.iloc[-1]
    logging.info(f"Latest RSI: {last_rsi:.2f}")
    print(f"Latest RSI: {last_rsi:.2f}")

if __name__ == "__main__":
    print("✅ Container started successfully.")
    while True:
        print("🟢 Bot is running... checking RSI")
        run_bot()
        time.sleep(30)  # Change to 3600 for hourly in production
