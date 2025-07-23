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
import json

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
TRADE_SYMBOL = "BTC-USDT"
TRADE_INTERVAL = "30m"
LEVERAGE = int(os.getenv("LEVERAGE", 10))
RISK_PER_TRADE = 0.10  # 10%

API_KEY = os.getenv("BLOFIN_API_KEY")
API_SECRET = os.getenv("BLOFIN_API_SECRET")
API_PASSPHRASE = "newPass1"
BASE_URL = "https://openapi.blofin.com"

# --- Logging ---
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s"
)

# --- Signature Helper ---
def generate_signature(method: str, path: str, timestamp: str, nonce: str, body: str, secret: str) -> str:
    prehash = f"{path}{method}{timestamp}{nonce}{body}"
    hmac_digest = hmac.new(secret.encode(), prehash.encode(), hashlib.sha256).hexdigest()
    signature = base64.b64encode(hmac_digest.encode()).decode()
    return signature

# --- API Request Function ---
def signed_request(method: str, path: str, body_dict=None):
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    body = "" if body_dict is None else json.dumps(body_dict)

    signature = generate_signature(method, path, timestamp, nonce, body, API_SECRET)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-NONCE": nonce,
        "ACCESS-SIGN": signature,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

    url = BASE_URL + path
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, data=body)
        else:
            raise ValueError("Unsupported method")

        response.raise_for_status()
            if response.get("code") == 0:
        stop_loss_pct = 0.01
        take_profit_pct = 0.04
        if side == "buy":
            stop_price = round(entry_price * (1 - stop_loss_pct), 2)
            take_price = round(entry_price * (1 + take_profit_pct), 2)
        else:
            stop_price = round(entry_price * (1 + stop_loss_pct), 2)
            take_price = round(entry_price * (1 - take_profit_pct), 2)
        print(f"📉 Stop Loss: {stop_price} | 🎯 Take Profit: {take_price}")
        # Future: Send stop-loss/take-profit as linked orders if supported
    return response.json()
    except Exception as e:
        logging.error(f"❌ API request failed: {e}")
        print(f"❌ API request failed: {e}")
        return {}

# --- Place Order ---
def place_order(inst_id: str, side: str, size: float, entry_price: float):
    path = "/api/v1/trade/order"
    order = {
        "instId": inst_id,
        "side": side,
        "ordType": "market",
        "posSide": "long" if side == "buy" else "short",
        "lever": str(LEVERAGE),
        "sz": str(size),
        "tgtEntry": str(entry_price)
    }
    response = signed_request("POST", path, order)
    print(f"📤 Order Response: {response}")
        if response.get("code") == 0:
        stop_loss_pct = 0.01
        take_profit_pct = 0.04
        if side == "buy":
            stop_price = round(entry_price * (1 - stop_loss_pct), 2)
            take_price = round(entry_price * (1 + take_profit_pct), 2)
        else:
            stop_price = round(entry_price * (1 + stop_loss_pct), 2)
            take_price = round(entry_price * (1 - take_profit_pct), 2)
        print(f"📉 Stop Loss: {stop_price} | 🎯 Take Profit: {take_price}")
        # Future: Send stop-loss/take-profit as linked orders if supported
    return response

# --- Get Kline Data ---
def get_klines(symbol: str, interval: str, limit=100):
    query = f"?instId={symbol}&bar={interval}&limit={limit}"
    path = f"/api/v1/market/candles{query}"
    method = "GET"
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    body = ""

    signature = generate_signature(method, path, timestamp, nonce, body, API_SECRET)

    headers = {
        "ACCESS-KEY": API_KEY,
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-NONCE": nonce,
        "ACCESS-SIGN": signature,
        "ACCESS-PASSPHRASE": API_PASSPHRASE,
        "Content-Type": "application/json"
    }

    url = BASE_URL + path
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Raw kline response: {response.text}")
            if response.get("code") == 0:
        stop_loss_pct = 0.01
        take_profit_pct = 0.04
        if side == "buy":
            stop_price = round(entry_price * (1 - stop_loss_pct), 2)
            take_price = round(entry_price * (1 + take_profit_pct), 2)
        else:
            stop_price = round(entry_price * (1 + stop_loss_pct), 2)
            take_price = round(entry_price * (1 - take_profit_pct), 2)
        print(f"📉 Stop Loss: {stop_price} | 🎯 Take Profit: {take_price}")
        # Future: Send stop-loss/take-profit as linked orders if supported
    return response.json()["data"]
    except Exception as e:
        logging.error(f"❌ Failed to fetch klines: {e}")
        print(f"❌ Failed to fetch klines: {e}")
        return []

# --- Technical Indicators ---
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def detect_divergence(closes: pd.Series, rsi: pd.Series) -> str:
    if len(closes) < 5 or len(rsi) < 5:
        return "none"
    price_highs = closes[-5:].nlargest(2)
    rsi_highs = rsi[-5:].nlargest(2)
    price_lows = closes[-5:].nsmallest(2)
    rsi_lows = rsi[-5:].nsmallest(2)
    if price_highs.iloc[0] > price_highs.iloc[1] and rsi_highs.iloc[0] < rsi_highs.iloc[1]:
        return "bearish"
    if price_lows.iloc[0] < price_lows.iloc[1] and rsi_lows.iloc[0] > rsi_lows.iloc[1]:
        return "bullish"
    return "none"

def calculate_fib_levels(closes: pd.Series) -> dict:
    high = max(closes[-20:])
    low = min(closes[-20:])
    diff = high - low
    return {
        "0.0": high,
        "0.236": high - diff * 0.236,
        "0.382": high - diff * 0.382,
        "0.5": high - diff * 0.5,
        "0.618": high - diff * 0.618,
        "0.786": high - diff * 0.786,
        "1.0": low
    }

# --- Main Bot Loop ---
def run_bot():
    klines = get_klines(TRADE_SYMBOL, TRADE_INTERVAL, 100)
    if not klines:
        logging.warning("⚠️ No kline data available — skipping this cycle.")
        print("⚠️ No kline data available — skipping this cycle.")
        return

    closes = pd.Series([float(k[4]) for k in klines])
    rsi = calculate_rsi(closes, RSI_PERIOD)
    last_rsi = rsi.iloc[-1]
    divergence = detect_divergence(closes, rsi)
    fib = calculate_fib_levels(closes)

    logging.info(f"Latest RSI: {last_rsi:.2f} | Divergence: {divergence}")
    print(f"Latest RSI: {last_rsi:.2f} | Divergence: {divergence}")
    print(f"Fibonacci levels: {fib}")

    if last_rsi < RSI_OVERSOLD and divergence == "bullish":
        print("🟢 Signal: BUY based on RSI + bullish divergence")
        place_order(TRADE_SYMBOL, "buy", 0.01)
    elif last_rsi > RSI_OVERBOUGHT and divergence == "bearish":
        print("🔴 Signal: SELL based on RSI + bearish divergence")
        place_order(TRADE_SYMBOL, "sell", 0.01)
    else:
        print("⏳ No clear signal — waiting.")

if __name__ == "__main__":
    print("✅ Container started successfully.")
    while True:
        print("🟢 Bot is running... checking RSI")
        run_bot()
        time.sleep(30)
