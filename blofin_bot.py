
import json
import hmac
import time
import uuid
import base64
import requests
import asyncio
import pandas as pd
import os

# Load from environment or replace with actual keys
API_KEY = os.getenv("BLOFIN_API_KEY", "your_api_key")
API_SECRET = os.getenv("BLOFIN_API_SECRET", "your_api_secret")
API_PASSPHRASE = os.getenv("BLOFIN_API_PASSPHRASE", "your_passphrase")
BASE_URL = "https://openapi.blofin.com"

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
TRADE_SYMBOL = "BTC-USDT"
TRADE_INTERVAL = "1h"
TRADE_SIZE = 0.003
LEVERAGE = 10

# --- RSI Calculation ---
def calculate_rsi(data: pd.Series, period: int) -> pd.Series:
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- Divergence Detection ---
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

# --- Signature Helper ---
def generate_signature(method, path, timestamp, nonce, body, secret):
    prehash = f"{path}{method}{timestamp}{nonce}{body}"
    hmac_digest = hmac.new(secret.encode(), prehash.encode(), digestmod="sha256").hexdigest()
    return base64.b64encode(hmac_digest.encode()).decode()

# --- Signed Request ---
def signed_request(method, path, body=None):
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    body_json = json.dumps(body) if body else ""
    signature = generate_signature(method, path, timestamp, nonce, body_json, API_SECRET)

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
            response = requests.post(url, headers=headers, data=body_json)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return {}

# --- Live Market Price ---
def get_live_price(symbol: str, side: str) -> float:
    try:
        response = requests.get(f"{BASE_URL}/api/v1/market/books", params={"instId": symbol, "sz": 1})
        response.raise_for_status()
        data = response.json()["data"][0]
        return float(data["asks"][0][0]) if side == "buy" else float(data["bids"][0][0])
    except Exception as e:
        print(f"⚠️ Failed to fetch live price: {e}")
        return 0.0

# --- Place Order ---
def place_order(inst_id, side, size, entry_price):
    stop_pct = 0.01
    take_pct = 0.04
    stop = round(entry_price * (1 - stop_pct), 2) if side == "buy" else round(entry_price * (1 + stop_pct), 2)
    take = round(entry_price * (1 + take_pct), 2) if side == "buy" else round(entry_price * (1 - take_pct), 2)

    order = {
        "instId": inst_id,
        "side": side,
        "ordType": "market",
        "posSide": "long" if side == "buy" else "short",
        "marginMode": "cross",
        "lever": str(LEVERAGE),
        "sz": str(size),
        "tpTriggerPrice": str(take),
        "tpOrderPrice": "-1",
        "slTriggerPrice": str(stop),
        "slOrderPrice": "-1"
    }

    print(f"📉 SL: {stop} | 🎯 TP: {take}")
    result = signed_request("POST", "/api/v1/trade/order", order)
    print("📤 Order Response:", result)

# --- Kline Fetch ---
def get_klines(symbol, interval, limit=100):
    url = f"{BASE_URL}/api/v1/market/candles?instId={symbol}&bar={interval}&limit={limit}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()["data"]
    except Exception as e:
        print(f"❌ Failed to fetch klines: {e}")
        return []

# --- Main Bot ---
async def run_bot():
    klines = get_klines(TRADE_SYMBOL, TRADE_INTERVAL)
    if not klines:
        print("⚠️ No kline data available — skipping.")
        return

    closes = pd.Series([float(k[4]) for k in klines])
    rsi = calculate_rsi(closes, RSI_PERIOD)
    last_rsi = rsi.iloc[-1]
    divergence = detect_divergence(closes, rsi)

    print(f"RSI: {last_rsi:.2f} | Divergence: {divergence}")

    if last_rsi < RSI_OVERSOLD and divergence == "bullish":
        print("🟢 BUY signal")
        price = get_live_price(TRADE_SYMBOL, "buy")
        if price > 0:
            place_order(TRADE_SYMBOL, "buy", TRADE_SIZE, price)
    elif last_rsi > RSI_OVERBOUGHT and divergence == "bearish":
        print("🔴 SELL signal")
        price = get_live_price(TRADE_SYMBOL, "sell")
        if price > 0:
            place_order(TRADE_SYMBOL, "sell", TRADE_SIZE, price)
    else:
        print("⏳ No signal")

# Run loop every 30 minutes
if __name__ == "__main__":
    print("🚀 Bot started...")
    while True:
        asyncio.run(run_bot())
        time.sleep(30 * 60)
