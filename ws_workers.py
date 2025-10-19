# ws_workers.py
import time, json
import numpy as np
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient
from shm_ring import ShmRing
from layouts import TRADE_DTYPE, BOOK_DTYPE

def _now_ms() -> int:
    return int(time.time() * 1000)

def exponential_backoff(base=1.0, cap=30.0):
    t = base
    while True:
        yield t
        t = min(t*2.0, cap)

# --- Binance Trade WS ---
def trade_ws_worker(cfg, shm_name_trades: str, capacity: int, shared):
    symbol = cfg["ticker"].upper()
    ring = ShmRing(shm_name_trades, TRADE_DTYPE, capacity, create=False)
    shared["tr_ws_state"] = "starting"
    backoff = exponential_backoff()

    last_msg = time.time()

    def on_message(_unused, message):
        nonlocal last_msg
        try:
            md = json.loads(message) if isinstance(message, (str, bytes)) else (message or {})
            d = md.get("data") if isinstance(md, dict) else md
            if not isinstance(d, dict):
                return
            # 필요한 키 존재?
            if not all(k in d for k in ("p","q","T","m","t")):
                return

            ts  = int(d["T"])
            px  = float(d["p"])
            qty = float(d["q"])
            sell= 1 if bool(d["m"]) else 0
            tid = int(d["t"])
            ring.push((ts, px, qty, sell, tid))

            shared["last_trade_ts"] = ts
            last_msg = time.time()
        except Exception:
            return

    while True:
        try:
            ws = SpotWebsocketStreamClient(on_message=on_message, is_combined=True)
            ws.trade(symbol=symbol.lower())
            shared["tr_ws_state"] = "connected"
            last_msg = time.time()

            while True:
                time.sleep(1.0)
                if time.time() - last_msg > 30:
                    shared["tr_ws_state"] = "idle-restart"
                    try: ws.stop()
                    except: pass
                    break

        except Exception:
            shared["tr_ws_state"] = "error"
            time.sleep(next(backoff))
            continue

# --- Binance Partial Book Depth WS ---
def book_ws_worker(cfg, shm_name_book: str, capacity: int, shared):
    symbol = cfg["ticker"].upper()
    ring = ShmRing(shm_name_book, BOOK_DTYPE, capacity, create=False)
    levels   = int(cfg.get("depth_levels", 5))
    speed_ms = int(cfg.get("depth_speed_ms", 100))
    shared["ob_ws_state"] = "starting"
    backoff = exponential_backoff()

    last_msg = time.time()

    def on_message(_unused, message):
        nonlocal last_msg
        try:
            md = json.loads(message) if isinstance(message,(str,bytes)) else (message or {})
            d = md.get("data") if isinstance(md, dict) else md
            if not isinstance(d, dict):
                return

            # keys: 'bids'/'asks' 또는 'b'/'a' 둘 다 대비
            bids = d.get("bids") or d.get("b")
            asks = d.get("asks") or d.get("a")
            if not (isinstance(bids, list) and isinstance(asks, list)):
                return
            if not bids or not asks:
                return

            b0 = bids[0]
            a0 = asks[0]
            # (가격/수량 문자열일 수 있음 → float 변환)
            bbid = float(b0[0]); bqty = float(b0[1])
            bask = float(a0[0]); aqty = float(a0[1])

            # TS 우선순위: T → E → now
            ts = _now_ms()

            # ★ 단일 튜플로 push (이전 1-엘리먼트 ndarray는 비권장)
            ring.push((ts, bbid, bqty, bask, aqty))

            shared["last_book_ts"] = ts
            last_msg = time.time()

        except Exception:
            return

    def subscribe(ws):
        try:
            ws.partial_book_depth(symbol=symbol.lower(), level=levels, speed=speed_ms)
        except Exception:
            pass

    while True:
        try:
            ws = SpotWebsocketStreamClient(on_message=on_message, is_combined=True)
            subscribe(ws)
            shared["ob_ws_state"] = "connected"
            last_msg = time.time()

            while True:
                time.sleep(1.0)
                if time.time() - last_msg > 10:
                    shared["ob_ws_state"] = "idle-restart"
                    try: ws.stop()
                    except: pass
                    break

        except Exception:
            shared["ob_ws_state"] = "error"
            time.sleep(next(backoff))
            continue
