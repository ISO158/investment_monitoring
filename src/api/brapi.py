import os

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://brapi.dev/api/v2"
TOKEN = os.getenv("BRAPI_TOKEN")


def get_stock_quote(symbols):
    url = f"{BASE_URL}/stocks/quote"

    params = {
        "symbols": ",".join(symbols)
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    return [result["data"] for result in data["results"]]


def get_stock_dy(symbols):
    url = f"{BASE_URL}/stocks/statistics"

    params = {
        "symbols": ",".join(symbols),
        "mode": "current"
    }

    headers = {
        "Authorization": f"Bearer {TOKEN}"
    }

    response = requests.get(
        url,
        params=params,
        headers=headers
    )

    response.raise_for_status()

    data = response.json()

    return [
        {
            "symbol": result["symbol"],
            "dividendYield": result["data"].get("dividendYield")
        }
        for result in data["results"]
    ]

response = requests.get(
    "https://brapi.dev/api/v2/stocks/statistics",
    params={"symbols": "BRAP4", "mode": "current"},
    headers={"Authorization": f"Bearer {TOKEN}"}
)

print(response.status_code)
print(response.text)