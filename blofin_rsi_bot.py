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
    url = f"{BASE_URL}/v1/market/kline"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        print(f"Raw kline response: {response.text}")  # optional debug
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

def get_account_balance():
    url = f"{BASE_URL}/v1/account/balance"
    timestamp = str(int(time.time() * 1000))
    headers = {
        "X-BLOFIN-APIKEY": API_KEY,
        "Content-Type": "application/json",
        "X-BLOFIN-TIMESTAMP": timestamp,
    }
    signature = sign_request({}, API_SECRET)
    headers["X-BLOFIN-SIGNATURE"] = signature

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Raw balance response: {response.text}")  # Optional for debugging
        data = response.json()
        usdt_balance = float(data.get("balance", 10000))  # fallback to 10k
        return usdt_balance
    except Exception as e:
        logging.error(f"❌ Failed to fetch balance: {e}")
        print(f"❌ Failed to fetch balance: {e}")
        return 10000

def place_order(side: str, qty: float):
    url = f"{BASE_URL}/v1/order"
    timestamp = str(int(time.time() * 1000))
    payload = {
        "symbol": TRADE_SYMBOL,
        "side": side.upper(),
        "type": "MARKET",
        "quantity": round(qty, 4),
        "leverage": LEVERAGE
    }
    signature = sign_request(payload, API_SECRET)
    headers = {
        "X-BLOFIN-APIKEY": API_KEY,
        "Content-Type": "application/json",
        "X-BLOFIN-TIMESTAMP": timestamp,
        "X-BLOFIN-SIGNATURE": signature
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Raw order response: {response.text}")  # Optional for debugging
        logging.info(f"✅ Executed {side.upper()} order: {qty:.4f} BTC")
        print(f"✅ Executed {side.upper()} order: {qty:.4f} BTC")
    except Exception as e:
        logging.error(f"❌ Order failed: {e}")
        print(f"❌ Order failed: {e}")

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
        time.sleep(30)  # For testing; change to 3600 for hourly
