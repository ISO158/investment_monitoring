from datetime import datetime, timedelta

import yfinance as yf

import pandas as pd


def get_stock_quote(symbols):
    data = []

    for symbol in symbols:
        ticker = yf.Ticker(f"{symbol}.SA")

        info = ticker.fast_info

        data.append({
            "symbol": symbol,
            "price": info.get("last_price"),
            "open": info.get("open"),
            "high": info.get("day_high"),
            "low": info.get("day_low"),
            "previous_close": info.get("previous_close"),
            "volume": info.get("last_volume"),
        })

    return data



def get_stock_dy(symbols):
    data = []

    for symbol in symbols:
        ticker = yf.Ticker(f"{symbol}.SA")

        dividends = ticker.dividends

        end_date = dividends.index.max()
        start_date = end_date - pd.DateOffset(months=12)

        dividends_12m = dividends[
            (dividends.index > start_date) &
            (dividends.index <= end_date)
        ]

        total_dividends = dividends_12m.sum()
        price = ticker.fast_info["last_price"]

        dy = total_dividends / price

        data.append({
            "symbol": symbol,
            "dividends_12m": total_dividends,
            "price": price,
            "dividend_yield_12m": dy
        })

    return data

data = get_stock_dy(["BRAP4", "TIMS3", "ITUB4"])
print(data)