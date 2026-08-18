import os

import requests
from dotenv import load_dotenv


load_dotenv()

BASE_URL = "https://api.usebolsai.com/api/v1"
TOKEN = os.getenv("BOLSAI_API_KEY")


def get_stock_quote(symbols):
    data = []

    headers = {
        "X-API-Key": TOKEN
    }

    for symbol in symbols:
        url = f"{BASE_URL}/stocks/{symbol}/quote"

        response = requests.get(
            url,
            headers=headers
        )

        response.raise_for_status()

        data.append(response.json())

    return data


def get_stock_fundamentals(symbols):
    data = []

    headers = {
        "X-API-Key": TOKEN
    }

    for symbol in symbols:
        url = f"{BASE_URL}/fundamentals/{symbol}"

        response = requests.get(
            url,
            headers=headers
        )

        response.raise_for_status()

        data.append(response.json())

    return data


def get_stock_dy(symbols):
    data = []

    headers = {
        "X-API-Key": TOKEN
    }

    for symbol in symbols:
        url = f"{BASE_URL}/dividends/{symbol}"

        response = requests.get(
            url,
            headers=headers
        )

        response.raise_for_status()

        result = response.json()

        data.append({
            "symbol": symbol,
            "dividendYield": result.get("dividend_yield_ttm")
        })

    return data


data = get_stock_quote(["PETR4", "VALE3", "ITUB4"])
print(data)

data = get_stock_dy(["PETR4", "VALE3", "ITUB4"])
print(data)