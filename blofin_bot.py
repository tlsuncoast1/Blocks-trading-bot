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
        return response.json()

    except Exception as e:
        logging.error(f"❌ API request failed: {e}")
        print(f"❌ API request failed: {e}")
        return {}