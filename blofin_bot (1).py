# blofin_bot.py
import os
import time
import hmac
import hashlib
import requests
import datetime
import logging
from typing import Dict

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
BASE_URL = "https://api.blofin.com"

# --- Logging ---
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Helper Functions ---
def sign_request(params: Dict[str, str], secret: str) -> str:
    query = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()

def get_klines(symbol: str, interval: str, limit=100):
    url = f"{BASE_URL}/api/v1/market/kline"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = requests.get(url, params=params)
    return response.json()["data"]

def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_account_balance():
    # Placeholder: Replace with actual API request to get account balance
    return 10000.0  # Simulated balance in USDT

def place_order(side: str, qty: float):
    # Placeholder: Replace with Blofin order execution API call
    logging.info(f"Placed {side} order for {qty:.4f} {TRADE_SYMBOL} at 10x leverage")
    print(f"Placed {side} order for {qty:.4f} {TRADE_SYMBOL} at 10x leverage")
    return True

def run_bot():
    klines = get_klines(TRADE_SYMBOL, TRADE_INTERVAL, 100)
    closes = pd.Series([float(k[4]) for k in klines])
    rsi = calculate_rsi(closes, RSI_PERIOD)

    last_rsi = rsi.iloc[-1]
    logging.info(f"Latest RSI: {last_rsi:.2f}")
    print(f"Latest RSI: {last_rsi:.2f}")

    balance = get_account_balance()
    current_price = closes.iloc[-1]
    position_size = (balance * RISK_PER_TRADE * LEVERAGE) / current_price

    if last_rsi < RSI_OVERSOLD:
        logging.info("RSI below 30 — Buying Signal")
        print("RSI below 30 — Buying Signal")
        place_order("buy", position_size)
    elif last_rsi > RSI_OVERBOUGHT:
        logging.info("RSI above 70 — Selling Signal")
        print("RSI above 70 — Selling Signal")
        place_order("sell", position_size)
    else:
        logging.info("RSI neutral — No action taken")
        print("RSI neutral — No action taken")

if __name__ == "__main__":
    while True:
        print("🟢 Bot is running... checking RSI")
        run_bot()
        time.sleep(30)  # For testing: runs every 30 seconds
