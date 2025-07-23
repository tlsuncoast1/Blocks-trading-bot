
def place_order(inst_id: str, side: str, size: float, entry_price: float):
    path = "/api/v1/trade/order"
    order = {
        "instId": inst_id,
        "side": side,
        "ordType": "market",
        "posSide": "long" if side == "buy" else "short",
        "marginMode": "cross",
        "tpTriggerPrice": str(take_price),
        "tpOrderPrice": "-1",
        "slTriggerPrice": str(stop_price),
        "slOrderPrice": "-1"
        "lever": str(LEVERAGE),
        "sz": str(size),
        "tgtEntry": str(entry_price)
    }
    response = signed_request("POST", path, order)

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
