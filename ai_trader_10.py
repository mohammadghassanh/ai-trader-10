"""
AI Trader 10 — paper-trading demo only.
No broker connection. No real orders. Market data may be delayed or incomplete.
"""
from __future__ import annotations

import json
import csv
from pathlib import Path
from datetime import datetime, timedelta, timezone

import yfinance as yf

STARTING_CASH = 10.00
MAX_ALLOCATION = 0.20
STOP_LOSS = 0.05
COST_RATE = 0.0015
TICKERS = ["EUNL.DE", "VUSA.DE", "EXS1.DE"]
STATE_FILE = Path("paper_state.json")
LOG_FILE = Path("trades.csv")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {
        "cash": STARTING_CASH,
        "positions": {},
        "started_at": datetime.now(timezone.utc).isoformat(),
    }


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def log_trade(action, ticker, shares, price, cash):
    new_file = not LOG_FILE.exists()
    with LOG_FILE.open("a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp_utc", "action", "ticker", "shares", "price", "cash_after"])
        writer.writerow([datetime.now(timezone.utc).isoformat(), action,
                         ticker, round(shares, 6), round(price, 4), round(cash, 2)])


def main():
    state = load_state()

    for ticker in TICKERS:
        try:
            hist = yf.Ticker(ticker).history(period="60d", interval="5m", auto_adjust=True)
            if hist.empty or len(hist) < 22:
                print(f"{ticker}: insufficient data; skipped")
                continue

            close = hist["Close"].dropna()
            price = float(close.iloc[-1])
            sma20 = float(close.tail(20).mean())
            sma50 = float(close.tail(50).mean()) if len(close) >= 50 else sma20
            position = state["positions"].get(ticker)

            if position:
                entry = float(position["entry"])
                shares = float(position["shares"])
                if price <= entry * (1 - STOP_LOSS) or price < sma20:
                    proceeds = shares * price * (1 - COST_RATE)
                    state["cash"] += proceeds
                    log_trade("SELL", ticker, shares, price, state["cash"])
                    del state["positions"][ticker]
                    print(f"{ticker}: simulated SELL at {price:.2f}")
            elif sma20 > sma50 and price > sma20 and state["cash"] > 0:
                budget = min(state["cash"], STARTING_CASH * MAX_ALLOCATION)
                shares = budget / (price * (1 + COST_RATE))
                if shares > 0:
                    cost = shares * price * (1 + COST_RATE)
                    state["cash"] -= cost
                    state["positions"][ticker] = {"shares": shares, "entry": price}
                    log_trade("BUY", ticker, shares, price, state["cash"])
                    print(f"{ticker}: simulated BUY at {price:.2f}")

        except Exception as exc:
            print(f"{ticker}: data/error, skipped ({exc})")

    save_state(state)
    holdings_value = 0.0
    for ticker, pos in state["positions"].items():
        try:
            latest = yf.Ticker(ticker).history(period="5d", interval="5m", auto_adjust=True)
            if not latest.empty:
                holdings_value += float(pos["shares"]) * float(latest["Close"].dropna().iloc[-1])
        except Exception:
            pass

    print(f"Paper portfolio value: EUR {state['cash'] + holdings_value:.2f}")
    print("Demo only — no real money or broker orders were used.")


if __name__ == "__main__":
    main()
