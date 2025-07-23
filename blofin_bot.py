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
BASE_URL = "https://api.blofin.com"

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

# --- Helper Functions ---
def get_klines(symbol: str, interval: str, limit=100):
    query = f"?symbol={symbol}&interval={interval}&limit={limit}"
    path = f"/v1/market/kline{query}"
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
        "Content-Type": "application/json"
    }

    url = BASE_URL + path
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        print(f"Raw kline response: {response.text}")
        return response.json()["data"]
    except Exception as e:
        logging.error(f"❌ Failed to fetch klines: {e}")
        print(f"❌ Failed to fetch klines: {e}")
        return []
