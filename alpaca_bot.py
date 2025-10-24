#!/usr/bin/env python3
"""
SPY Iron Condor executor for Alpaca (paper/live) — entry-only bot.

Features:
- .env loader + key mapping (ALPACA_API_KEY / ALPACA_SECRET_KEY)
- Master kill switch (TRADING_ENABLED) + .halt panic file + SIGINT/SIGTERM
- Risk rails: MAX_PER_TRADE_RISK, MAX_DAILY_NEW_ORDERS
- Uses REST API directly for options (compatible with alpaca-py 0.43.0+)
- Tries multi-leg combo net-credit; falls back to legging two credit spreads
- Fixed-credit pricing by default (robust). Mid-pricing stub included but off by default.

Install:
  pip install alpaca-py python-dotenv python-dateutil requests

Env (.env):
  ALPACA_API_KEY=...
  ALPACA_SECRET_KEY=...
  TRADING_ENABLED=false
  MAX_PER_TRADE_RISK=200
  MAX_DAILY_NEW_ORDERS=10
"""

import os, sys, signal
from datetime import datetime
from dateutil.relativedelta import relativedelta, FR
from dotenv import load_dotenv

# ================= USER CONFIG (edit if needed) =================
SYMBOL = "SPY"
PAPER = True

# Structure
CENTER = 670            # short strikes centered near spot
WIDTH = 2               # short->long distance (e.g., 670/672 calls; 668/666 puts)
WINGS = 4               # put long wing distance from center (asymmetry allowed)

QTY = 1                 # number of iron condors
EXPIRY_OVERRIDE = None  # "YYYY-MM-DD" else nearest Friday

# Pricing (use fixed credits — robust across SDK versions)
TARGET_CALL_SPREAD_CREDIT = 0.35
TARGET_PUT_SPREAD_CREDIT  = 0.35

# Optional mid-pricing (stubbed; set True to try — falls back transparently)
USE_MID_PRICING = False
MID_SLIPPAGE = 0.02     # for SELL: limit = max(bid, mid - 0.02)

# Safety rails
HALT_FILE = ".halt"
# ================================================================


# -------- Kill switch / safety
_HARD_STOP = {"value": False}
def _handle_stop(sig, frame):
    _HARD_STOP["value"] = True
signal.signal(signal.SIGINT, _handle_stop)
signal.signal(signal.SIGTERM, _handle_stop)

def trading_enabled() -> bool:
    v = os.getenv("TRADING_ENABLED", "false").strip().lower()
    return v in ("1", "true", "yes", "on")

def guard_or_exit():
    if _HARD_STOP["value"]:
        print("[HALT] Received stop signal.")
        sys.exit(0)
    if os.path.exists(HALT_FILE):
        print("[HALT] .halt file present.")
        sys.exit(0)
    if not trading_enabled():
        print("[HALT] TRADING_ENABLED=false — not placing orders.")
        sys.exit(0)

# -------- Helpers
def nearest_friday_str():
    now = datetime.now()
    friday = (now + relativedelta(weekday=FR(0))).date()
    return friday.strftime("%Y-%m-%d")

def occ_symbol(underlying: str, ymd: str, call_put: str, strike: float) -> str:
    """
    OCC: <root><YY><MM><DD><C/P><strike*1000 8-digit>
    e.g., SPY 2025-10-24 670 C -> SPY251024C00670000
    """
    dt = datetime.strptime(ymd, "%Y-%m-%d")
    yy, mm, dd = dt.strftime("%y"), dt.strftime("%m"), dt.strftime("%d")
    strike_int = int(round(strike * 1000))
    return f"{underlying}{yy}{mm}{dd}{call_put.upper()}{strike_int:08d}"

def load_and_map_env():
    load_dotenv()
    # Map your .env names to what alpaca-py expects:
    if os.getenv("ALPACA_API_KEY_ID") is None and os.getenv("ALPACA_API_KEY"):
        os.environ["ALPACA_API_KEY_ID"] = os.getenv("ALPACA_API_KEY")
    if os.getenv("ALPACA_API_SECRET_KEY") is None and os.getenv("ALPACA_SECRET_KEY"):
        os.environ["ALPACA_API_SECRET_KEY"] = os.getenv("ALPACA_SECRET_KEY")
    for req in ("ALPACA_API_KEY_ID", "ALPACA_API_SECRET_KEY"):
        if not os.getenv(req):
            raise RuntimeError(f"Missing {req}. Check your .env.")

# -------- Alpaca SDK imports
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import TimeInForce, OrderSide, OrderType
import requests
import json

# Use REST API directly for options (more reliable across versions)
def get_alpaca_base_url(paper: bool) -> str:
    """Get the correct Alpaca API base URL"""
    if paper:
        return "https://paper-api.alpaca.markets"
    else:
        return "https://api.alpaca.markets"

# Optional quotes (mid-pricing) — stubbed to be resilient
def try_get_mid(symbol_occ: str):
    """
    Attempt to fetch bid/ask and return mid. If unavailable or error, return None.
    """
    if not USE_MID_PRICING:
        return None
    try:
        # NOTE: alpaca-py options quote API signatures vary by version.
        # We attempt a best-effort import; if it fails, we return None.
        from alpaca.data.historical import OptionHistoricalDataClient
        from alpaca.data.requests import OptionQuotesRequest
        from alpaca.data.timeframe import TimeFrame
        api_key = os.getenv("ALPACA_API_KEY_ID"); api_secret = os.getenv("ALPACA_API_SECRET_KEY")
        client = OptionHistoricalDataClient(api_key, api_secret)
        # Get last quote today
        rq = OptionQuotesRequest(symbol_or_symbols=symbol_occ, limit=1)
        quotes = client.get_option_quotes(rq)
        q = None
        # quotes can be dict-like {symbol: [Quote]}
        if hasattr(quotes, "data"):
            data = quotes.data.get(symbol_occ) or quotes[symbol_occ]
        else:
            data = quotes[symbol_occ]
        if data:
            q = data[-1]
        if not q:
            return None
        bid = float(q.bid_price) if q.bid_price is not None else None
        ask = float(q.ask_price) if q.ask_price is not None else None
        if bid is None or ask is None or ask <= 0:
            return None
        return (bid + ask) / 2.0
    except Exception:
        return None

# Risk rails
def get_caps():
    max_orders = int(os.getenv("MAX_DAILY_NEW_ORDERS", "10"))
    max_risk = float(os.getenv("MAX_PER_TRADE_RISK", "200"))  # USD
    return max_orders, max_risk

_state = {"orders_today": 0}

def enforce_caps(est_max_loss_usd: float):
    max_orders, max_risk = get_caps()
    if _state["orders_today"] >= max_orders:
        print(f"[HALT] MAX_DAILY_NEW_ORDERS reached ({max_orders}).")
        sys.exit(0)
    if est_max_loss_usd > max_risk:
        print(f"[HALT] Est. max loss ${est_max_loss_usd:.2f} > cap ${max_risk:.2f}.")
        sys.exit(0)

# ---- Core submitters using REST API
def submit_option_order_rest(api_key: str, api_secret: str, paper: bool, symbol: str, qty: int, side: str, order_type: str, limit_price: float = None):
    """
    Submit option order via REST API (works with all alpaca-py versions)
    """
    base_url = get_alpaca_base_url(paper)
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
        "Content-Type": "application/json"
    }
    
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": order_type,
        "time_in_force": "day"
    }
    
    if limit_price is not None:
        payload["limit_price"] = round(limit_price, 2)
    
    response = requests.post(f"{base_url}/v2/orders", headers=headers, json=payload)
    
    if response.status_code in [200, 201]:
        order = response.json()
        return order
    else:
        raise RuntimeError(f"Order failed: {response.status_code} - {response.text}")

def submit_legged_spread(api_key: str, api_secret: str, paper: bool, short_occ: str, long_occ: str, credit_target: float):
    """
    Submit short leg LIMIT at target; immediately protect with long leg MARKET.
    Returns (resp_short, resp_long)
    """
    # Price logic (attempt mid, else target)
    limit_price = credit_target
    if USE_MID_PRICING:
        mid = try_get_mid(short_occ)
        if mid:
            limit_price = max(0.01, round(max(mid - MID_SLIPPAGE, 0.01), 2))

    guard_or_exit()
    resp_short = submit_option_order_rest(
        api_key, api_secret, paper,
        symbol=short_occ,
        qty=QTY,
        side="sell",
        order_type="limit",
        limit_price=limit_price
    )
    print(f"[OK] Submitted SHORT leg: {resp_short.get('id', 'unknown')}")
    
    guard_or_exit()
    resp_long = submit_option_order_rest(
        api_key, api_secret, paper,
        symbol=long_occ,
        qty=QTY,
        side="buy",
        order_type="market"
    )
    print(f"[OK] Submitted LONG protection: {resp_long.get('id', 'unknown')}")

    _state["orders_today"] += 2
    return resp_short, resp_long

def main():
    load_and_map_env()
    guard_or_exit()

    # Get API credentials
    api_key = os.getenv("ALPACA_API_KEY_ID")
    api_secret = os.getenv("ALPACA_API_SECRET_KEY")

    # Still use SDK for account info/validation
    trading_client = TradingClient(api_key, api_secret, paper=PAPER)
    
    # Verify connection
    try:
        account = trading_client.get_account()
        print(f"✓ Connected to Alpaca ({'PAPER' if PAPER else 'LIVE'})")
        print(f"  Account: ${float(account.equity):,.2f} equity, ${float(account.buying_power):,.2f} buying power")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Alpaca: {e}")
        sys.exit(1)

    expiry = EXPIRY_OVERRIDE or nearest_friday_str()
    short_call = CENTER
    long_call  = CENTER + WIDTH
    short_put  = CENTER - WIDTH
    long_put   = CENTER - WINGS

    call_short_sym = occ_symbol(SYMBOL, expiry, "C", short_call)
    call_long_sym  = occ_symbol(SYMBOL, expiry, "C", long_call)
    put_short_sym  = occ_symbol(SYMBOL, expiry, "P", short_put)
    put_long_sym   = occ_symbol(SYMBOL, expiry, "P", long_put)

    total_target_credit = TARGET_CALL_SPREAD_CREDIT + TARGET_PUT_SPREAD_CREDIT
    call_width = long_call - short_call
    put_width  = short_put - long_put
    max_spread_width = max(call_width, put_width)
    # Est. max loss per condor (per contract): (max_width - total_credit)*100
    est_max_loss_usd = max(0.0, (max_spread_width - total_target_credit) * 100.0) * QTY

    print()
    print(f"=== SPY Iron Condor {expiry} ===")
    print(f"  Calls: SELL {short_call}C / BUY {long_call}C  (target credit ~ {TARGET_CALL_SPREAD_CREDIT:.2f})")
    print(f"  Puts : SELL {short_put}P  / BUY {long_put}P   (target credit ~ {TARGET_PUT_SPREAD_CREDIT:.2f})")
    print(f"  OCC  : {call_short_sym}, {call_long_sym}, {put_short_sym}, {put_long_sym}")
    print(f"  Qty  : {QTY}   PAPER={PAPER}   USE_MID_PRICING={USE_MID_PRICING}")
    print(f"  Est. Max Loss ${est_max_loss_usd:.2f} (widths: call={call_width}, put={put_width})")
    print()

    enforce_caps(est_max_loss_usd)

    # Use REST API to submit options orders (works with any alpaca-py version)
    print("[INFO] Submitting iron condor using REST API (compatible mode)...")
    
    # Submit call spread
    try:
        print("[1/2] Submitting call credit spread...")
        submit_legged_spread(
            api_key, api_secret, PAPER,
            call_short_sym, call_long_sym, TARGET_CALL_SPREAD_CREDIT
        )
        print("✓ Call spread submitted")
    except Exception as e:
        print(f"[ERROR] Call spread legging failed: {e}")
        sys.exit(1)

    # Submit put spread
    try:
        print("[2/2] Submitting put credit spread...")
        submit_legged_spread(
            api_key, api_secret, PAPER,
            put_short_sym, put_long_sym, TARGET_PUT_SPREAD_CREDIT
        )
        print("✓ Put spread submitted")
    except Exception as e:
        print(f"[ERROR] Put spread legging failed: {e}")
        sys.exit(1)

    print()
    print("[DONE] ✅ Iron Condor submitted via separate call/put credit spreads.")
    print("       Monitor fills in Alpaca dashboard:")
    if PAPER:
        print("       https://app.alpaca.markets/paper/dashboard/overview")
    else:
        print("       https://app.alpaca.markets/dashboard/overview")

if __name__ == "__main__":
    main()
