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


data = get_stock_quote(["PETR4", "VALE3", "ITUB4"])

print(data)