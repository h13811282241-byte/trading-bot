
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liangxi FastPlot — Binance Testnet Live Version
------------------------------------------------
- 连接 Binance Testnet (现货)，用实时 K线跑策略
- 策略逻辑和回测版一致，信号触发时自动下单
- 注意：请在 Testnet 环境使用 API_KEY/SECRET
"""

import time
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
from dataclasses import dataclass
import os
LOCAL_TZ = os.getenv("TZ", "Asia/Shanghai")
# ========== 在这里填你的 testnet API Key ==========
API_KEY = "your_testnet_api_key"
API_SECRET = "your_testnet_api_secret"

# 初始化 Binance Testnet 客户端
client = Client(API_KEY, API_SECRET, testnet=True)

# ========== 策略参数 ==========
PARAMS = {
    "symbol": "BTCUSDT",
    "interval": "1m",     # K线周期
    "qty": 0.001,         # 每次下单数量

    "ema_period": 200,
    "brk_lookback": 24,
    "brk_mult": 0.3,
    "brk_mode": "close",
    "pattern_three_filter": True,
    "min_atr": 5.0
}

# ========== 工具函数 ==========
def fetch_binance_klines(symbol="BTCUSDT", interval="1m", limit=500):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","num_trades","tbbav","tbqav","ignore"
    ])[["open_time","open","high","low","close","volume"]]
    # ✅ 关键：UTC → 本地时区
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert(LOCAL_TZ)
    df = df.astype({"open":float,"high":float,"low":float,"close":float,"volume":float})
    df = df.rename(columns={"open_time":"datetime"}).set_index("datetime")
    return df


def ema(s: pd.Series, period: int) -> pd.Series:
    return s.ewm(span=period, adjust=False).mean()

def tr(high, low, close):
    prev = close.shift(1)
    return pd.concat([(high-low).abs(), (high-prev).abs(), (low-prev).abs()], axis=1).max(axis=1)

def atr(high, low, close, p=14):
    return tr(high,low,close).ewm(alpha=1/p, adjust=False).mean()

def _is_bull(o, c): return c > o
def _is_bear(o, c): return c < o

def match_threebar_pattern(i: int, open_: pd.Series, close: pd.Series):
    if i < 2: return None
    o1, c1 = float(open_.iloc[i-2]), float(close.iloc[i-2])
    o2, c2 = float(open_.iloc[i-1]), float(close.iloc[i-1])
    o3, c3 = float(open_.iloc[i  ]), float(close.iloc[i  ])
    if _is_bull(o1,c1) and _is_bear(o2,c2) and _is_bull(o3,c3): return "long"
    if _is_bear(o1,c1) and _is_bull(o2,c2) and _is_bear(o3,c3): return "short"
    return None

def thresholds_breakout(high, low, a, lookback, mult):
    hh = high.rolling(lookback).max().shift(1)
    ll = low.rolling(lookback).min().shift(1)
    return hh + mult * a.shift(1), ll - mult * a.shift(1)

def choose_entry(i, close, high, low, open_, ema_base, a, brk_up, brk_dn, params):
    px = float(close.iloc[i])
    if params["min_atr"] > 0 and float(a.iloc[i]) < params["min_atr"]:
        return None
    raw_sig = None
    bu, bd = brk_up.iloc[i], brk_dn.iloc[i]
    hi, lo, cl = float(high.iloc[i]), float(low.iloc[i]), float(close.iloc[i])
    if params["brk_mode"] == "close":
        if cl >= bu: raw_sig = "long"
        if cl <= bd: raw_sig = "short"
    elif params["brk_mode"] == "either":
        if (hi >= bu or cl >= bu): raw_sig = "long"
        if (lo <= bd or cl <= bd): raw_sig = "short"
    else:
        if hi >= bu: raw_sig = "long"
        if lo <= bd: raw_sig = "short"

    if params["pattern_three_filter"]:
        patt = match_threebar_pattern(i, open_, close)
        if patt != raw_sig: return None
    return raw_sig

def place_order(symbol, side, qty):
    try:
        order = client.create_order(
            symbol=symbol,
            side=SIDE_BUY if side=="long" else SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=qty
        )
        print("Order executed:", order["orderId"], side, qty)
    except Exception as e:
        print("Order failed:", e)
def to_local_naive(ts, local_tz=LOCAL_TZ):
    t = pd.Timestamp(ts)
    # 若无时区，按 Binance 返回的 UTC 先本地化再转
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    return t.tz_convert(local_tz).tz_localize(None)  # 本地时间且不带 +08:00
# ========== 主循环 ==========
def run_live():
    params = PARAMS
    while True:
        df = fetch_binance_klines(params["symbol"], params["interval"], limit=300)
        close, high, low, open_ = df["close"], df["high"], df["low"], df["open"]
        ema_base = ema(close, params["ema_period"])
        A = atr(high, low, close)
        brk_up, brk_dn = thresholds_breakout(high, low, A, params["brk_lookback"], params["brk_mult"])
        sig = choose_entry(len(df) - 1, close, high, low, open_, ema_base, A, brk_up, brk_dn, params)

        now_ts = to_local_naive(df.index[-1])  # 用我们封装的函数

        if sig:
            print("Signal:", sig, "at", now_ts)
            place_order(params["symbol"], sig, params["qty"])
        else:
            print("No signal at", now_ts)
        time.sleep(60)

if __name__ == "__main__":
    run_live()
