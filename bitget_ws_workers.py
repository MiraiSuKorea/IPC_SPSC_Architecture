# bitget_ws_workers.py
import time, json, numpy as np
from websocket import WebSocketApp
from shm_ring import ShmRing
from layouts import BOOK_DTYPE
import threading

# PUB_URL = "wss://ws.bitget.com/v2/ws/public"
PUB_URL = "wss://wspap.bitget.com/v2/ws/public"

def _now_ms(): return int(time.time()*1000)

HEARTBEAT_INTERVAL = 30  # Bitget 권장
HEARTBEAT_TIMEOUT  = 70  # pong 없을 때 재연결 유도

def bitget_futures_book_ws_worker(cfg, shm_name_books: str, capacity: int, shared):
    instId = str(cfg.get("bitget_symbol"))
    ring = ShmRing(shm_name_books, BOOK_DTYPE, capacity, create=False)
    shared["bg_books_state"] = "starting"

    last_pong = {"ts": _now_ms()}  # 최근 pong 시각

    # ----- backoff generator (로컬) -----
    def _backoff_gen():
        t = 0.5
        while True:
            yield t
            t = min(t * 2, 12)

    bo = _backoff_gen()

    def reset_backoff():
        nonlocal bo
        bo = _backoff_gen()

    # ------------------------------------

    def on_open(ws):
        try:
            reset_backoff()  # 연결 성공 시 백오프 리셋
            sub = {
                "op": "subscribe",
                "args": [{"instType": "USDT-FUTURES", "channel": "books1", "instId": instId}],
            }
            ws.send(json.dumps(sub))
            shared["bg_trade_state"] = "subscribed"
            last_pong["ts"] = _now_ms()  # 오픈 시 초기화
        except Exception:
            shared["bg_trade_state"] = "open_err"

    def on_message(ws, message):
        try:
            # Bitget는 'pong'을 문자열로 주거나 {"event":"pong"} 형식으로 줄 수 있음
            if message == "pong":
                last_pong["ts"] = _now_ms()
                return

            md = json.loads(message) if isinstance(message, (str, bytes)) else (message or {})
            if isinstance(md, dict) and md.get("event") == "pong":
                last_pong["ts"] = _now_ms()
                return

            data = md.get("data")
            if not isinstance(data, list):
                return

            for d in data:
                asks = d.get("asks") or []
                bids = d.get("bids") or []

                if not asks or not bids:
                    continue
                    # 문자열로 오는 경우가 많음 -> float 캐스팅
                a0 = asks[0];
                b0 = bids[0];
                ask = float(a0[0]);
                ask_qty = float(a0[1]);
                bid = float(b0[0]);
                bid_qty = float(b0[1]);

                ts = int(d.get("ts"))

                ring.push((ts, bid, bid_qty, ask, ask_qty))
                shared["last_bg_books_ts"] = ts
                shared["last_bg_books_px"] = (ask + bid) * 0.5
        except Exception as e:
            shared["bg_trade_last_err"] = str(e)

    def on_close(ws,*a): shared["bg_books_state"]="closed"
    def on_err(ws,err):  shared["bg_books_state"]="error"

    def heartbeater(ws):
        while True:
            time.sleep(HEARTBEAT_INTERVAL)
            try:
                # Bitget 요구: 문자열 "ping" 전송
                ws.send("ping")
            except Exception:
                return  # 연결이 죽었으면 스레드 종료
            # pong 타임아웃 체크 -> 재연결 유도
            if _now_ms() - last_pong["ts"] > HEARTBEAT_TIMEOUT*1000:
                try: ws.close()  # run_forever 루프에서 재연결
                except: pass
                return

    while True:
        try:
            ws = WebSocketApp(
                PUB_URL,
                on_open=on_open,
                on_message=on_message,
                on_error=on_err,
                on_close=on_close
            )
            shared["bg_books_state"]="connecting"
            t = threading.Thread(target=heartbeater, args=(ws,), daemon=True)
            t.start()
            # run_forever의 ping_interval은 제어프레임용(프로토콜 핑). 앱 핑은 heartbeater에서 처리.
            ws.run_forever(ping_interval=0, ping_timeout=None)
        except Exception:
            shared["bg_books_state"]="crashed"
        # 실패/종료 후 지수 백오프 슬립
        try:
            time.sleep(next(bo))
        except StopIteration:
            # 이 경우는 없지만 방지용
            bo = _backoff_gen()
            time.sleep(next(bo))

